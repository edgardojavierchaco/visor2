from datetime import date, datetime
from decimal import Decimal, InvalidOperation
import logging
import re

from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.db import IntegrityError, connection, transaction
from django.db.models import F, Q
from django.db.models.deletion import ProtectedError
from django.utils import timezone

from ..models import (
    CargoPof,
    LocalizacionPof,
    LoteCargaPof,
    MovimientoCargoPof,
    ProyectosEspecialesPof,
    ReunidaPof,
    SnapshotPadronLocalizacionPof,
)
from .niveles import obtener_niveles_ceic_para_reunida, oferta_es_compatible_con_reunida
from .niveles_service import normalizar_nivel
from .padron_materializadas_service import (
    armar_localizacion_payload,
    armar_snapshot_payload,
    construir_cueanexo_sin_guion,
    normalizar_anexo,
    resolver_fila_padron_oficial,
)
from .cargos_consolidacion_service import aplicar_alta_consolidada


CABECERA_REUNIDA = "REUNIDA"
CABECERA_PROYECTO_ESPECIAL = "PROYECTO_ESPECIAL"
MODO_PADRON_MANUAL_CONTROLADO = "MANUAL_CONTROLADO"
MENSAJE_INGRESO_MANUAL_SIN_CUEANEXO = (
    "El ingreso manual no debe cargar CUE, Anexo ni CUEANEXO. Use Buscar en padrón."
)
CAMPOS_IDENTIDAD_PADRON_MANUAL = (
    "cue",
    "anexo",
    "cueanexo",
    "padron_cueanexo",
    "cue_anexo",
)

logger = logging.getLogger(__name__)


def _texto(valor):
    return str(valor or "").strip()


def _digitos(valor):
    return re.sub(r"\D", "", _texto(valor))


def _ceic_codigo_texto(valor):
    """
    Convierte el CEIC recibido a texto sin corregir espacios ni símbolos.

    - Permite rechazar payloads manipulados con espacios o caracteres inválidos.
    - Mantiene enteros JSON válidos como códigos comparables.
    - No completa ni normaliza códigos antes de validarlos.
    """
    if valor is None:
        return ""
    return str(valor)


def _observacion_usuario(valor):
    texto = _texto(valor)
    if texto in {"-", "--", "---", "\u00e2\u20ac\u201d", "\u2014"}:
        return ""
    return texto


def _decimal(valor):
    return Decimal(str(valor))


def _entero_positivo(valor):
    numero = Decimal(str(valor))
    if numero != numero.to_integral_value() or numero <= 0:
        raise ValueError
    return numero


def _decimal_texto(valor):
    return str(Decimal(valor).quantize(Decimal("0.01")))


def _cantidad_texto(valor):
    numero = Decimal(valor)
    if numero == numero.to_integral_value():
        return str(int(numero))
    return _decimal_texto(numero)


def _ceic_fuera_sugerencia_explicito(valor):
    """
    Interpreta la marca enviada por el alta para aceptar un CEIC no sugerido.

    - Solo considera explícitos valores booleanos verdaderos o textos equivalentes.
    - No convierte cargo, puntos ni nivel en datos confiables del frontend.
    - Permite diferenciar una elección global consciente de un payload manipulado.
    """
    if valor is True:
        return True
    if isinstance(valor, str):
        return valor.strip().lower() in {"true", "1", "si", "sí"}
    return False


def _json_primitivo(valor):
    if valor is None or isinstance(valor, (str, int, float, bool)):
        return valor
    if isinstance(valor, Decimal):
        return str(valor)
    if isinstance(valor, (datetime, date)):
        return valor.isoformat()
    if isinstance(valor, dict):
        return {str(clave): _json_primitivo(item) for clave, item in valor.items()}
    if isinstance(valor, (list, tuple)):
        return [_json_primitivo(item) for item in valor]
    if hasattr(valor, "pk"):
        return _json_primitivo(valor.pk)
    return _texto(valor)


def _json_dict_seguro(datos):
    return _json_primitivo(datos or {})


def _snapshot_ceic_seguro(ceic_puntos):
    return _json_dict_seguro(
        {
            "ceic": ceic_puntos["ceic"],
            "cargo": ceic_puntos["cargo"],
            "puntos_asignados": _decimal_texto(ceic_puntos["puntos_asignados"]),
            "nivel": ceic_puntos.get("nivel", ""),
        }
    )


def _placeholders_sql(cantidad):
    return ", ".join(["%s"] * cantidad)


def _obtener_ceic_puntos(ceic):
    """
    Obtiene datos oficiales de un CEIC activo para modificar cargos existentes.

    - Reutiliza la misma consulta oficial usada en alta para no duplicar criterio.
    - Devuelve `None` si el CEIC no existe, está inactivo o no tiene datos válidos.
    - Expone cargo, puntos y nivel listos para regenerar `snapshot_ceic`.
    """
    try:
        ceic_normalizado = int(ceic)
    except (TypeError, ValueError):
        return None

    return _obtener_catalogo_ceic_por_ids([ceic_normalizado]).get(ceic_normalizado)


def _obtener_catalogo_ceic_por_ids(ceics, nivel_reunida=""):
    """
    Obtiene solo los CEIC necesarios para el guardado actual.

    - Filtra siempre por `estado = TRUE`.
    - En Reunidas aplica además `nivel IN (...)` según la matriz central.
    - Devuelve un diccionario por CEIC para evitar consultas repetidas dentro del lote.
    """
    ceics_unicos = sorted(
        {
            int(_ceic_codigo_texto(ceic))
            for ceic in ceics
            if re.fullmatch(r"\d{1,3}", _ceic_codigo_texto(ceic))
        }
    )
    if not ceics_unicos:
        return {}

    clausulas = [
        "estado = TRUE",
        f"ceic_id IN ({_placeholders_sql(len(ceics_unicos))})",
    ]
    parametros = list(ceics_unicos)

    nivel_normalizado = normalizar_nivel(nivel_reunida)
    if nivel_normalizado:
        niveles_permitidos = sorted(obtener_niveles_ceic_para_reunida(nivel_normalizado))
        if not niveles_permitidos:
            return {}
        clausulas.append(f"nivel IN ({_placeholders_sql(len(niveles_permitidos))})")
        parametros.extend(niveles_permitidos)

    sql = f"""
        SELECT ceic_id AS ceic, descripcion_ceic, puntos, nivel
        FROM cenpe.ceic_puntos
        WHERE {" AND ".join(clausulas)}
    """

    with connection.cursor() as cursor:
        cursor.execute(sql, parametros)
        filas = cursor.fetchall()

    catalogo = {}
    for fila in filas:
        try:
            ceic_normalizado = int(fila[0])
            cargo = _texto(fila[1])
            puntos_decimal = Decimal(str(fila[2]))
        except (IndexError, TypeError, ValueError, InvalidOperation):
            continue

        if not cargo or not puntos_decimal.is_finite():
            continue

        catalogo[ceic_normalizado] = {
            "ceic": ceic_normalizado,
            "cargo": cargo,
            "puntos_asignados": puntos_decimal,
            "nivel": _json_primitivo(fila[3] if len(fila) > 3 else ""),
            "tiene_datos": True,
        }

    return catalogo


def _errores_validation_error(error):
    if hasattr(error, "message_dict"):
        return error.message_dict
    return {"__all__": error.messages}


def _localizacion_desde_padron(padron):
    payload = armar_localizacion_payload(padron)
    cueanexo = _texto(
        padron.get("padron_cueanexo")
        or padron.get("cueanexo")
        or padron.get("cue_anexo")
    )
    if not cueanexo:
        cue = _digitos(padron.get("cue"))
        anexo = _digitos(padron.get("anexo"))
        if cue and anexo:
            cueanexo = construir_cueanexo_sin_guion(cue, anexo)
        elif not cue and not anexo:
            cueanexo = _texto(payload.get("cueanexo"))
    cuof = _texto(payload.get("cuof") or padron.get("cuof_loc") or padron.get("cuof"))
    cui = _texto(payload.get("cui") or padron.get("cui_loc") or padron.get("cui"))
    return cueanexo, cuof, cui


def _campos_identidad_padron_manual_informados(padron):
    """
    Detecta datos oficiales prohibidos en el modo manual controlado.

    - Revisa todos los aliases soportados para CUE, Anexo y CUEANEXO.
    - Trata como informados los valores no vacíos aunque luego no sean normalizables.
    - Permite rechazar el payload antes de consultar o sincronizar padrón oficial.
    """
    if not isinstance(padron, dict):
        return []
    return [
        campo
        for campo in CAMPOS_IDENTIDAD_PADRON_MANUAL
        if _texto(padron.get(campo))
    ]


def _normalizar_identidad_proyecto_desde_padron(padron):
    cueanexo = _digitos(
        padron.get("padron_cueanexo")
        or padron.get("cueanexo")
        or padron.get("cue_anexo")
    )
    cue = _digitos(padron.get("cue"))
    anexo = _digitos(padron.get("anexo"))
    _cueanexo_padron, cuof, cui = _localizacion_desde_padron(padron)

    if cueanexo:
        if len(cueanexo) != 9:
            raise ValidationError({"cueanexo": ["El CUEANEXO debe tener 9 digitos."]})
        if cue and len(cue) != 7:
            raise ValidationError({"cue": ["El CUE debe tener 7 digitos."]})
        if anexo and len(anexo) > 2:
            raise ValidationError({"anexo": ["El Anexo debe tener hasta 2 digitos."]})
        anexo_normalizado = normalizar_anexo(anexo) if anexo else cueanexo[7:]
        cue_normalizado = cue or cueanexo[:7]
        if cue and anexo and cueanexo != f"{cue_normalizado}{anexo_normalizado}":
            raise ValidationError({"cueanexo": ["El CUEANEXO debe coincidir con CUE + Anexo."]})
        return {
            "cueanexo": cueanexo,
            "cue": cue_normalizado,
            "anexo": anexo_normalizado,
            "cuof": cuof,
            "cui": cui,
        }

    if cue or anexo:
        if not cue:
            raise ValidationError({"cue": ["Para informar Anexo debe completar CUE."]})
        if not anexo:
            raise ValidationError({"anexo": ["Para informar CUE debe completar Anexo."]})
        if len(cue) != 7:
            raise ValidationError({"cue": ["El CUE debe tener 7 digitos."]})
        if len(anexo) > 2:
            raise ValidationError({"anexo": ["El Anexo debe tener hasta 2 digitos."]})
        anexo = normalizar_anexo(anexo)
        cueanexo = construir_cueanexo_sin_guion(cue, anexo)

    return {
        "cueanexo": cueanexo,
        "cue": cue if cueanexo else "",
        "anexo": anexo if cueanexo else "",
        "cuof": cuof,
        "cui": cui,
    }


def _sincronizar_padron_identidad_proyecto(padron, identidad):
    cueanexo = identidad["cueanexo"]
    padron["cueanexo"] = cueanexo
    padron["padron_cueanexo"] = cueanexo
    padron["cue_anexo"] = cueanexo
    padron["cue"] = identidad["cue"] if cueanexo else ""
    padron["anexo"] = identidad["anexo"] if cueanexo else ""
    padron["cuof"] = identidad["cuof"]
    padron["cuof_loc"] = identidad["cuof"]
    padron["cui"] = identidad["cui"]
    padron["cui_loc"] = identidad["cui"]


def _agregar_advertencia(advertencias, mensaje):
    logger.warning(mensaje)
    if advertencias is not None:
        advertencias.append(mensaje)


def _normalizar_origen_datos(valor):
    origen = _texto(valor).upper()
    opciones = {opcion for opcion, _ in SnapshotPadronLocalizacionPof.OrigenDatos.choices}
    if origen in opciones:
        return origen
    return SnapshotPadronLocalizacionPof.OrigenDatos.MANUAL


def _validar_datos_guardado_minimos(datos):
    """
    Valida solo la entrada mínima confiable del flujo de guardado.

    - Verifica cabecera, padrón y lista de cargos antes de la oficialización CEIC.
    - Acepta como datos de usuario únicamente CEIC, cantidad, unidad y observación.
    - Rechaza CUE, Anexo y CUEANEXO cuando Proyecto Especial usa ingreso manual controlado.
    - No depende de cargo, puntos, total ni snapshot enviados por frontend.
    """
    errores = {}
    if not isinstance(datos, dict):
        return {"datos": ["Los datos de guardado deben ser un diccionario."]}

    cabecera_tipo = datos.get("cabecera_tipo")
    if cabecera_tipo not in {CABECERA_REUNIDA, CABECERA_PROYECTO_ESPECIAL}:
        errores["cabecera_tipo"] = ["El tipo de cabecera no es valido."]

    modo_padron = _texto(datos.get("modo_padron")).upper()
    if cabecera_tipo == CABECERA_REUNIDA and modo_padron == MODO_PADRON_MANUAL_CONTROLADO:
        errores["modo_padron"] = ["El modo manual solo es valido para Proyecto Especial."]

    if cabecera_tipo == CABECERA_REUNIDA:
        anio = datos.get("anio")
        nivel_normalizado = normalizar_nivel(datos.get("nivel"))
        if not anio:
            errores["anio"] = ["El anio es obligatorio para Reunidas POF."]
        else:
            anio_texto = str(anio)
            if not anio_texto.isdigit() or len(anio_texto) != 4:
                errores["anio"] = ["El anio debe tener 4 digitos numericos."]
            elif int(anio) > timezone.localdate().year:
                errores["anio"] = ["El anio no puede ser posterior al anio actual."]

        if not nivel_normalizado:
            errores["nivel"] = ["El nivel ingresado no es valido."]
        elif anio and "anio" not in errores:
            if not ReunidaPof.objects.filter(anio=anio, nivel=nivel_normalizado).exists():
                errores["reunida"] = ["No existe una Reunida POF para ese anio y nivel. Primero debe crearla."]

    if cabecera_tipo == CABECERA_PROYECTO_ESPECIAL:
        proyecto_especial_id = _texto(datos.get("proyecto_especial_id"))
        if not proyecto_especial_id:
            errores["proyecto_especial_id"] = ["El proyecto especial es obligatorio."]
        elif not proyecto_especial_id.isdigit():
            errores["proyecto_especial_id"] = ["El proyecto especial no es valido."]

    tipo_operacion = datos.get("tipo_operacion") or LoteCargaPof.TipoOperacion.ALTA
    tipos_operacion = {opcion for opcion, _ in LoteCargaPof.TipoOperacion.choices}
    if tipo_operacion not in tipos_operacion:
        errores["tipo_operacion"] = ["El tipo de operacion no es valido."]

    padron = datos.get("padron")
    if not isinstance(padron, dict):
        errores["padron"] = ["El bloque padron es obligatorio."]
        padron = {}

    identidad_manual_informada = (
        cabecera_tipo == CABECERA_PROYECTO_ESPECIAL
        and modo_padron == MODO_PADRON_MANUAL_CONTROLADO
        and _campos_identidad_padron_manual_informados(padron)
    )
    if identidad_manual_informada:
        errores["padron"] = [MENSAJE_INGRESO_MANUAL_SIN_CUEANEXO]

    cueanexo, cuof, _cui = _localizacion_desde_padron(padron)

    if cabecera_tipo == CABECERA_PROYECTO_ESPECIAL and not identidad_manual_informada:
        try:
            _normalizar_identidad_proyecto_desde_padron(padron)
        except ValidationError as error:
            errores.update(_errores_validation_error(error))

    if cabecera_tipo == CABECERA_REUNIDA:
        if not cueanexo:
            errores["cueanexo"] = ["El CUEANEXO es obligatorio para Reunidas POF."]
        elif not re.fullmatch(r"\d{9}", cueanexo):
            errores["cueanexo"] = ["El CUEANEXO debe tener 9 digitos."]

    if not cuof:
        errores["cuof"] = ["El CUOF es obligatorio."]

    cargos = datos.get("cargos")
    if not isinstance(cargos, list) or not cargos:
        errores["cargos"] = ["La lista de cargos es obligatoria y no puede estar vacia."]
        return errores

    errores_cargos = {}
    unidades = {opcion for opcion, _ in CargoPof.UnidadCantidad.choices}
    for indice, cargo in enumerate(cargos):
        if not isinstance(cargo, dict):
            errores_cargos[indice] = {"cargo": ["Cada cargo debe ser un diccionario."]}
            continue

        errores_cargo = {}
        ceic_texto = _ceic_codigo_texto(cargo.get("ceic"))
        if not re.fullmatch(r"\d{1,3}", ceic_texto):
            errores_cargo["ceic"] = ["Ingresá solo números, hasta 3 dígitos."]

        try:
            _entero_positivo(cargo.get("cantidad"))
            if _decimal(cargo.get("cantidad")) <= 0:
                errores_cargo["cantidad"] = ["La cantidad debe ser mayor a 0."]
        except (InvalidOperation, TypeError, ValueError):
            errores_cargo["cantidad"] = ["La cantidad debe ser un numero valido."]

        if cargo.get("unidad_cantidad") not in unidades:
            errores_cargo["unidad_cantidad"] = ["La unidad de cantidad no es valida."]

        cargo["observacion"] = _texto(cargo.get("observacion"))

        if errores_cargo:
            errores_cargos[indice] = errores_cargo

    if errores_cargos:
        errores["cargos"] = errores_cargos

    return errores


def _obtener_cabecera(datos):
    cabecera_tipo = datos["cabecera_tipo"]
    if cabecera_tipo == CABECERA_REUNIDA:
        reunida = ReunidaPof.objects.get(
            anio=datos["anio"],
            nivel=normalizar_nivel(datos["nivel"]),
        )
        return reunida, None

    proyecto = ProyectosEspecialesPof.objects.get(id=datos["proyecto_especial_id"])
    return None, proyecto


def _validar_y_oficializar_padron_guardado(datos, reunida, proyecto):
    """
    Resuelve la localización real de padrón antes de persistir una alta.

    - Para Reunidas exige una fila real por `cueanexo + cuof` y rechaza selecciones ambiguas o inexistentes.
    - Valida compatibilidad de la oferta usando la fila oficial obtenida desde padrón, no el texto del frontend.
    - En Proyecto Especial manual rechaza identidad oficial cargada y conserva padrón manual sin resolver.
    - Si existe fila oficial resoluble, usa siempre padrón aunque el frontend envíe origen manual.
    """
    padron = datos["padron"]
    cueanexo, cuof, _cui = _localizacion_desde_padron(padron)
    id_localizacion = padron.get("id_localizacion")
    id_oferta_local = padron.get("id_oferta_local")
    puede_validar_padron = bool(cueanexo and cuof)

    if proyecto and _texto(datos.get("modo_padron")).upper() == MODO_PADRON_MANUAL_CONTROLADO:
        if _campos_identidad_padron_manual_informados(padron):
            return {
                "ok": False,
                "errores": {"padron": [MENSAJE_INGRESO_MANUAL_SIN_CUEANEXO]},
            }
        identidad_manual = _normalizar_identidad_proyecto_desde_padron(padron)
        _sincronizar_padron_identidad_proyecto(padron, identidad_manual)
        padron["origen_datos"] = SnapshotPadronLocalizacionPof.OrigenDatos.MANUAL
        padron["estado_padron"] = SnapshotPadronLocalizacionPof.EstadoPadron.NO_ENCONTRADO
        return {"ok": True, "padron": padron}

    if reunida:
        validacion_padron = resolver_fila_padron_oficial(
            cueanexo=cueanexo,
            cuof=cuof,
            id_localizacion=id_localizacion,
            id_oferta_local=id_oferta_local,
        )
        if not validacion_padron["ok"]:
            return {
                "ok": False,
                "errores": {"padron": [validacion_padron["mensaje"]]},
            }

        padron_oficial = validacion_padron["fila"]
        oferta_real = _texto(padron_oficial.get("oferta_real") or padron_oficial.get("oferta"))
        if not oferta_es_compatible_con_reunida(oferta_real, reunida.nivel):
            return {
                "ok": False,
                "errores": {
                    "padron": [
                        "La oferta real del padrón no es compatible con el nivel de la Reunida."
                    ]
                },
            }

        return {"ok": True, "padron": padron_oficial}

    if not proyecto or not puede_validar_padron:
        return {"ok": True, "padron": padron}

    validacion_padron = resolver_fila_padron_oficial(
        cueanexo=cueanexo,
        cuof=cuof,
        id_localizacion=id_localizacion,
        id_oferta_local=id_oferta_local,
    )
    if not validacion_padron["ok"]:
        return {
            "ok": False,
            "errores": {"padron": [validacion_padron["mensaje"]]},
        }

    return {"ok": True, "padron": validacion_padron["fila"]}


def _oficializar_cargos_desde_ceic(datos, reunida):
    """
    Oficializa cada cargo usando solo la fuente real de CEIC.

    - En Proyecto Especial consulta una sola vez los CEIC unicos enviados en el lote.
    - En Reunida consulta CEIC sugeridos y globales para controlar la confirmacion fuera de sugerencia.
    - Para Reunidas exige CEIC sugerido o una marca explícita de fuera de sugerencia.
    - Devuelve cargos completos listos para consolidar y persistir.
    """
    cargos = datos.get("cargos") or []
    ceics_cargos = [cargo.get("ceic") for cargo in cargos if isinstance(cargo, dict)]
    if reunida:
        catalogo_ceic = _obtener_catalogo_ceic_por_ids(
            ceics=ceics_cargos,
            nivel_reunida=reunida.nivel,
        )
        catalogo_ceic_global = _obtener_catalogo_ceic_por_ids(
            ceics=ceics_cargos,
            nivel_reunida="",
        )
    else:
        catalogo_ceic = _obtener_catalogo_ceic_por_ids(
            ceics=ceics_cargos,
            nivel_reunida="",
        )
        catalogo_ceic_global = catalogo_ceic
    errores_cargos = {}
    cargos_normalizados = []

    for indice, cargo in enumerate(cargos):
        if not isinstance(cargo, dict):
            errores_cargos[indice] = {"cargo": ["Cada cargo debe ser un diccionario."]}
            continue

        ceic_texto = _ceic_codigo_texto(cargo.get("ceic"))
        if not re.fullmatch(r"\d{1,3}", ceic_texto):
            errores_cargos[indice] = {"ceic": ["Ingresá solo números, hasta 3 dígitos."]}
            continue
        ceic = int(ceic_texto)

        ceic_real = catalogo_ceic.get(ceic)
        if reunida and not ceic_real and _ceic_fuera_sugerencia_explicito(cargo.get("ceic_fuera_sugerencia")):
            ceic_real = catalogo_ceic_global.get(ceic)
        elif reunida and not ceic_real and catalogo_ceic_global.get(ceic):
            errores_cargos[indice] = {
                "ceic": [
                    "El CEIC está fuera de sugerencia y requiere confirmación explícita."
                ]
            }
            continue

        if not ceic_real:
            mensaje = (
                "El CEIC indicado no existe, está inactivo o no es compatible con el nivel de la Reunida."
                if reunida
                else "El CEIC indicado no existe o está inactivo."
            )
            errores_cargos[indice] = {"ceic": [mensaje]}
            continue

        cantidad = _entero_positivo(cargo.get("cantidad"))
        puntos_asignados = ceic_real["puntos_asignados"]
        cargos_normalizados.append(
            {
                "ceic": ceic_real["ceic"],
                "cargo": ceic_real["cargo"],
                "cantidad": cantidad,
                "unidad_cantidad": cargo.get("unidad_cantidad"),
                "puntos_asignados": puntos_asignados,
                "total": cantidad * puntos_asignados,
                "observacion": _texto(cargo.get("observacion")),
                "snapshot_ceic": _snapshot_ceic_seguro(ceic_real),
            }
        )

    return {"ok": not errores_cargos, "errores": errores_cargos, "cargos": cargos_normalizados}


def _existe_conflicto_cuof(localizacion, cuof):
    if not cuof:
        return False

    if localizacion.reunida_id:
        return LocalizacionPof.objects.filter(
            reunida_id=localizacion.reunida_id,
            proyecto_especial=None,
            cueanexo=localizacion.cueanexo,
            cuof=cuof,
        ).exclude(pk=localizacion.pk).exists()

    return LocalizacionPof.objects.filter(
        reunida=None,
        proyecto_especial_id=localizacion.proyecto_especial_id,
        cuof=cuof,
    ).exclude(pk=localizacion.pk).exists()


def _actualizar_localizacion_identificadores(localizacion, *, cueanexo=None, cuof="", cui="", advertencias=None):
    update_fields = []

    if cueanexo is not None and localizacion.cueanexo != cueanexo:
        localizacion.cueanexo = cueanexo
        update_fields.append("cueanexo")

    if cui and localizacion.cui != cui:
        localizacion.cui = cui
        update_fields.append("cui")

    if cuof and localizacion.cuof != cuof:
        if _existe_conflicto_cuof(localizacion, cuof):
            _agregar_advertencia(
                advertencias,
                (
                    "No se actualizo el CUOF de la localizacion "
                    f"{localizacion.id} porque ya existe otra localizacion historica con ese CUOF."
                ),
            )
        else:
            localizacion.cuof = cuof
            update_fields.append("cuof")

    if update_fields:
        localizacion.save(update_fields=update_fields)


def _obtener_localizacion_reunida(reunida, cueanexo, cuof, cui, advertencias):
    candidatas = list(
        LocalizacionPof.objects.select_for_update()
        .filter(
            reunida=reunida,
            proyecto_especial=None,
            cueanexo=cueanexo,
        )
        .order_by("id")[:2]
    )

    if candidatas:
        if len(candidatas) > 1:
            _agregar_advertencia(
                advertencias,
                (
                    "Existen localizaciones historicas duplicadas para la misma Reunida "
                    f"y CUEANEXO {cueanexo}; se uso la de menor id."
                ),
            )
        localizacion = candidatas[0]
        _actualizar_localizacion_identificadores(
            localizacion,
            cuof=cuof,
            cui=cui,
            advertencias=advertencias,
        )
        return localizacion

    return LocalizacionPof.objects.create(
        reunida=reunida,
        proyecto_especial=None,
        cueanexo=cueanexo,
        cuof=cuof,
        cui=cui,
    )


def _obtener_localizacion_proyecto(proyecto, identidad, advertencias):
    """
    Obtiene o crea la localización de Proyecto Especial según su identidad.

    - En flujo con CUEANEXO reutiliza la localización oficial coincidente.
    - En flujo manual por CUOF evita asociar datos a una localización con CUEANEXO.
    - Mantiene advertencias para duplicados históricos sin fusionar identidades incompatibles.
    """
    cueanexo = identidad["cueanexo"]
    cuof = identidad["cuof"]
    cui = identidad["cui"]

    if cueanexo:
        candidatas = list(
            LocalizacionPof.objects.select_for_update()
            .filter(
                reunida=None,
                proyecto_especial=proyecto,
                cueanexo=cueanexo,
            )
            .order_by("id")[:2]
        )
        if candidatas:
            if len(candidatas) > 1:
                _agregar_advertencia(
                    advertencias,
                    (
                        "Existen localizaciones historicas duplicadas para el mismo Proyecto Especial "
                        f"y CUEANEXO {cueanexo}; se uso la de menor id."
                    ),
                )
            localizacion = candidatas[0]
            _actualizar_localizacion_identificadores(
                localizacion,
                cuof=cuof,
                cui=cui,
                advertencias=advertencias,
            )
            return localizacion

        localizacion_por_cuof = None
        if cuof:
            localizacion_por_cuof = (
                LocalizacionPof.objects.select_for_update()
                .filter(
                    reunida=None,
                    proyecto_especial=proyecto,
                    cuof=cuof,
                )
                .order_by("id")
                .first()
            )

        if localizacion_por_cuof:
            if _texto(localizacion_por_cuof.cueanexo):
                raise ValidationError({
                    "cuof": [
                        (
                            "El CUOF indicado ya está asociado a otro CUEANEXO en este Proyecto Especial. "
                            "No se fusionaron datos; revise la localización antes de guardar."
                        )
                    ]
                })
            _actualizar_localizacion_identificadores(
                localizacion_por_cuof,
                cueanexo=cueanexo,
                cuof=cuof,
                cui=cui,
                advertencias=advertencias,
            )
            return localizacion_por_cuof

        return LocalizacionPof.objects.create(
            reunida=None,
            proyecto_especial=proyecto,
            cueanexo=cueanexo,
            cuof=cuof,
            cui=cui,
        )

    if not cuof:
        raise ValidationError({"cuof": ["El CUOF es obligatorio."]})

    candidatas = list(
        LocalizacionPof.objects.select_for_update()
        .filter(
            reunida=None,
            proyecto_especial=proyecto,
            cuof=cuof,
        )
        .order_by("id")[:2]
    )
    if candidatas:
        if len(candidatas) > 1:
            _agregar_advertencia(
                advertencias,
                (
                    "Existen localizaciones historicas duplicadas para el mismo Proyecto Especial "
                    f"y CUOF {cuof}; se uso la de menor id."
                ),
            )
        localizacion = candidatas[0]
        if _texto(localizacion.cueanexo):
            raise ValidationError({
                "cuof": [
                    "El CUOF indicado ya está asociado a una localización del padrón. Use Buscar en padrón."
                ]
            })
        _actualizar_localizacion_identificadores(
            localizacion,
            cui=cui,
            advertencias=advertencias,
        )
        return localizacion

    return LocalizacionPof.objects.create(
        reunida=None,
        proyecto_especial=proyecto,
        cueanexo="",
        cuof=cuof,
        cui=cui,
    )


def _obtener_localizacion(datos, reunida, proyecto, advertencias=None):
    padron = datos["padron"]

    if reunida:
        cueanexo, cuof, cui = _localizacion_desde_padron(padron)
        return _obtener_localizacion_reunida(reunida, cueanexo, cuof, cui, advertencias)

    identidad = _normalizar_identidad_proyecto_desde_padron(padron)
    _sincronizar_padron_identidad_proyecto(padron, identidad)
    return _obtener_localizacion_proyecto(proyecto, identidad, advertencias)


def _obtener_snapshot(localizacion, padron, usuario):
    snapshot_payload = armar_snapshot_payload(padron)
    origen_datos = _normalizar_origen_datos(
        padron.get("origen_datos") or snapshot_payload.get("origen_datos")
    )
    estado_padron = _texto(padron.get("estado_padron"))
    if not estado_padron:
        if origen_datos == SnapshotPadronLocalizacionPof.OrigenDatos.PADRON:
            estado_padron = SnapshotPadronLocalizacionPof.EstadoPadron.VIGENTE
        else:
            estado_padron = SnapshotPadronLocalizacionPof.EstadoPadron.SIN_VERIFICAR

    datos_snapshot = {
        "tipo_snapshot": SnapshotPadronLocalizacionPof.TipoSnapshot.INICIAL,
        "origen_datos": origen_datos,
        "vigente": True,
        "estado_padron": estado_padron,
        "estado_localizacion_padron": snapshot_payload.get("estado_localizacion_padron", ""),
        "estado_oferta_padron": snapshot_payload.get("estado_oferta_padron", ""),
        "estado_establecimiento_padron": snapshot_payload.get("estado_establecimiento_padron", ""),
        "oferta": snapshot_payload.get("oferta", ""),
        "acronimo": snapshot_payload.get("acronimo", ""),
        "nombre_establecimiento": snapshot_payload.get("nombre_establecimiento", ""),
        "numero_establecimiento": snapshot_payload.get("numero_establecimiento", ""),
        "region": snapshot_payload.get("region", ""),
        "localidad": snapshot_payload.get("localidad", ""),
        "departamento": snapshot_payload.get("departamento", ""),
        "ambito": snapshot_payload.get("ambito", ""),
        "categoria": snapshot_payload.get("categoria", ""),
        "jornada": snapshot_payload.get("jornada", ""),
        "ubicacion": snapshot_payload.get("ubicacion", ""),
        "ubicacion_localidad_departamento": snapshot_payload.get("ubicacion_localidad_departamento", ""),
        "datos_padron": snapshot_payload.get("datos_padron", {}),
        "usuario": usuario,
        "fecha_snapshot": timezone.now(),
    }

    snapshot = SnapshotPadronLocalizacionPof.objects.filter(
        localizacion=localizacion,
        vigente=True,
    ).first()
    if snapshot:
        for campo, valor in datos_snapshot.items():
            setattr(snapshot, campo, valor)
        snapshot.save(update_fields=list(datos_snapshot.keys()))
        return snapshot

    return SnapshotPadronLocalizacionPof.objects.create(
        localizacion=localizacion,
        **datos_snapshot,
    )


def _valores_nuevos_cargo(cargo):
    return _json_dict_seguro(
        {
            "ceic": cargo.ceic,
            "cargo": cargo.cargo,
            "cantidad": _cantidad_texto(cargo.cantidad),
            "unidad_cantidad": cargo.unidad_cantidad,
            "puntos_asignados": _decimal_texto(cargo.puntos_asignados),
            "total": _decimal_texto(cargo.total),
            "estado_pof": cargo.estado_pof,
            "observacion": cargo.observacion,
        }
    )


def _observacion_movimiento_desde_carga(cargo_data, datos=None):
    """
    Obtiene una observación propia del movimiento solo cuando el usuario la escribió.

    - Prioriza la observación específica del cargo dentro de la carga.
    - Reutiliza la observación general solo si existe texto real y no placeholder.
    - Nunca inventa mensajes automáticos para cubrir cambios que ya quedan en el diff.
    """
    return (
        _observacion_usuario((cargo_data or {}).get("observacion"))
        or _observacion_usuario((datos or {}).get("observacion"))
    )


def _obtener_snapshot_vigente(localizacion):
    return SnapshotPadronLocalizacionPof.objects.filter(
        localizacion=localizacion,
        vigente=True,
    ).order_by("-fecha_snapshot").first()


def _crear_lote_administrativo(cargo, tipo_operacion, usuario):
    localizacion = cargo.localizacion
    return LoteCargaPof.objects.create(
        reunida=localizacion.reunida,
        proyecto_especial=localizacion.proyecto_especial,
        localizacion=localizacion,
        tipo_operacion=tipo_operacion,
        usuario=usuario,
    )


def _serializar_cargo_detalle(cargo):
    localizacion = cargo.localizacion
    reunida = localizacion.reunida
    proyecto = localizacion.proyecto_especial
    snapshot = _obtener_snapshot_vigente(localizacion)

    if reunida:
        cabecera = f"Reunida {reunida.anio} - {reunida.get_nivel_display()}"
    elif proyecto:
        cabecera = f"Proyecto Especial {proyecto.anio} - {proyecto.nombre}"
    else:
        cabecera = ""

    return _json_dict_seguro({
        "id": cargo.id,
        "ceic": cargo.ceic,
        "cargo": cargo.cargo,
        "cantidad": _cantidad_texto(cargo.cantidad),
        "unidad_cantidad": cargo.unidad_cantidad,
        "unidad_cantidad_display": cargo.get_unidad_cantidad_display(),
        "puntos_asignados": _decimal_texto(cargo.puntos_asignados),
        "total": _decimal_texto(cargo.total),
        "estado_pof": cargo.estado_pof,
        "estado_pof_display": cargo.get_estado_pof_display(),
        "observacion": cargo.observacion,
        "actualizado_en": cargo.actualizado_en.isoformat() if cargo.actualizado_en else "",
        "localizacion": {
            "cueanexo": localizacion.cueanexo,
            "cuof": localizacion.cuof,
            "establecimiento": (
                snapshot.nombre_establecimiento
                or snapshot.numero_establecimiento
                if snapshot
                else ""
            ),
        },
        "cabecera": cabecera,
    })


def obtener_detalle_cargo_pof(cargo_id):
    cargo = CargoPof.objects.select_related(
        "localizacion",
        "localizacion__reunida",
        "localizacion__proyecto_especial",
    ).get(pk=cargo_id)
    return _serializar_cargo_detalle(cargo)


def _validar_payload_modificacion(datos):
    """
    Valida solo los campos realmente editables en administración de cargos.

    - Mantiene CEIC como dato de control para impedir cambios de identidad.
    - Permite editar únicamente cantidad, unidad, estado y observación.
    - Ignora cargo, puntos y snapshot enviados por frontend porque se oficializan desde backend.
    """
    errores = {}

    cantidad_texto = _texto(datos.get("cantidad"))
    if not re.fullmatch(r"[1-9]\d*", cantidad_texto):
        cantidad = None
        errores["cantidad"] = ["La cantidad debe ser un número entero."]
    else:
        cantidad = Decimal(cantidad_texto)

    unidades = {opcion for opcion, _ in CargoPof.UnidadCantidad.choices}
    unidad_cantidad = _texto(datos.get("unidad_cantidad")).upper()
    if unidad_cantidad not in unidades:
        errores["unidad_cantidad"] = ["La unidad de cantidad no es válida."]

    estados_editables = {
        CargoPof.EstadoPof.AFECTADO,
        CargoPof.EstadoPof.DESAFECTADO,
    }
    estado_pof = _texto(datos.get("estado_pof")).upper()
    if estado_pof not in estados_editables:
        errores["estado_pof"] = ["El estado indicado no es válido."]

    return {
        "ok": not errores,
        "errores": errores,
        "datos": {
            "cantidad": cantidad,
            "unidad_cantidad": unidad_cantidad,
            "estado_pof": estado_pof,
            "observacion": _observacion_usuario(datos.get("observacion")),
        },
    }


def modificar_cargo_pof(cargo_id, datos, usuario=None):
    """
    Modifica un cargo POF y registra solo la auditoría propia de la acción.

    - Detecta cambios comparando el snapshot completo del cargo antes y después del guardado.
    - Deja la observación persistente del cargo dentro del diff, no como nota duplicada del movimiento.
    - Conserva movimientos separados para datos y estado cuando ambos cambian en la misma acción.
    """
    if not isinstance(datos, dict):
        return {
            "ok": False,
            "tipo": "validacion",
            "mensaje": "El cuerpo de la solicitud debe ser un objeto JSON.",
            "errores": {"payload": ["JSON inválido."]},
        }

    etapa = "validacion_payload"
    usuario_id = getattr(usuario, "id", None)
    validacion = _validar_payload_modificacion(datos)
    if not validacion["ok"]:
        return {
            "ok": False,
            "tipo": "validacion",
            "mensaje": "Hay errores de validación.",
            "errores": validacion["errores"],
        }

    try:
        with transaction.atomic():
            etapa = "obtencion_cargo"
            cargo = CargoPof.objects.select_for_update().get(pk=cargo_id)

            etapa = "snapshot_anterior"
            valores_anteriores = _valores_nuevos_cargo(cargo)
            datos_limpios = validacion["datos"]
            etapa = "consulta_ceic_oficial"
            ceic_puntos = _obtener_ceic_puntos(cargo.ceic)
            if not ceic_puntos:
                return {
                    "ok": False,
                    "tipo": "validacion",
                    "mensaje": "Hay errores de validación.",
                    "errores": {
                        "ceic": [
                            "El CEIC actual del cargo no existe, está inactivo o no tiene datos oficiales."
                        ]
                    },
                }

            puntos_ceic = ceic_puntos["puntos_asignados"]
            etapa = "comparacion_cambios"
            valores_enviados = dict(valores_anteriores) # type: ignore
            valores_enviados.update(
                {
                    "ceic": cargo.ceic,
                    "cantidad": _cantidad_texto(datos_limpios["cantidad"]),
                    "unidad_cantidad": datos_limpios["unidad_cantidad"],
                    "puntos_asignados": _decimal_texto(puntos_ceic),
                    "estado_pof": datos_limpios["estado_pof"],
                    "cargo": ceic_puntos["cargo"],
                    "observacion": datos_limpios["observacion"],
                }
            )
            valores_enviados["total"] = _decimal_texto(
                datos_limpios["cantidad"] * puntos_ceic
            )
            valores_enviados_sin_estado = dict(valores_enviados)
            valores_enviados_sin_estado["estado_pof"] = valores_anteriores["estado_pof"]
            hay_cambios_datos = valores_anteriores != valores_enviados_sin_estado
            hay_cambio_estado = (
                valores_anteriores["estado_pof"] != valores_enviados["estado_pof"]
            )

            if not hay_cambios_datos and not hay_cambio_estado:
                return {
                    "ok": False,
                    "tipo": "sin_cambios",
                    "mensaje": "No hay cambios para guardar.",
                    "errores": {"__all__": ["Los datos enviados son iguales a los actuales."]},
                }

            etapa = "crear_lote_administrativo"
            lote_modificacion = (
                _crear_lote_administrativo(
                    cargo,
                    LoteCargaPof.TipoOperacion.MODIFICACION,
                    usuario,
                )
                if hay_cambios_datos
                else None
            )
            es_afectacion = datos_limpios["estado_pof"] == CargoPof.EstadoPof.AFECTADO
            lote_estado = (
                _crear_lote_administrativo(
                    cargo,
                    (
                        LoteCargaPof.TipoOperacion.AFECTACION
                        if es_afectacion
                        else LoteCargaPof.TipoOperacion.DESAFECTACION
                    ),
                    usuario,
                )
                if hay_cambio_estado
                else None
            )
            lote_final = lote_estado or lote_modificacion

            etapa = "asignacion_campos"
            cargo.lote_carga = lote_final
            cargo.cantidad = datos_limpios["cantidad"]
            cargo.unidad_cantidad = datos_limpios["unidad_cantidad"]
            cargo.estado_pof = datos_limpios["estado_pof"]
            cargo.cargo = ceic_puntos["cargo"]
            cargo.puntos_asignados = puntos_ceic
            cargo.snapshot_ceic = _snapshot_ceic_seguro(ceic_puntos)
            cargo.observacion = datos_limpios["observacion"]

            etapa = "guardar_cargo"
            cargo.save()
            etapa = "snapshot_nuevo"
            valores_nuevos = _valores_nuevos_cargo(cargo)
            valores_nuevos_sin_estado = dict(valores_nuevos)
            valores_nuevos_sin_estado["estado_pof"] = valores_anteriores["estado_pof"]
            snapshot_vigente = _obtener_snapshot_vigente(cargo.localizacion)

            etapa = "crear_movimiento"
            if hay_cambios_datos:
                MovimientoCargoPof.objects.create(
                    cargo=cargo,
                    lote_carga=lote_modificacion,
                    snapshot_padron=snapshot_vigente,
                    tipo_movimiento=MovimientoCargoPof.TipoMovimiento.MODIFICACION,
                    estado_anterior=valores_anteriores["estado_pof"],
                    estado_nuevo=valores_anteriores["estado_pof"],
                    valores_anteriores=valores_anteriores,
                    valores_nuevos=valores_nuevos_sin_estado,
                    observacion="",
                    usuario=usuario,
                )

            if hay_cambio_estado:
                tipo_movimiento_estado = (
                    MovimientoCargoPof.TipoMovimiento.AFECTACION
                    if es_afectacion
                    else MovimientoCargoPof.TipoMovimiento.DESAFECTACION
                )
                MovimientoCargoPof.objects.create(
                    cargo=cargo,
                    lote_carga=lote_estado,
                    snapshot_padron=snapshot_vigente,
                    tipo_movimiento=tipo_movimiento_estado,
                    estado_anterior=valores_anteriores["estado_pof"],
                    estado_nuevo=valores_nuevos["estado_pof"],
                    valores_anteriores=(
                        valores_nuevos_sin_estado
                        if hay_cambios_datos
                        else valores_anteriores
                    ),
                    valores_nuevos=valores_nuevos,
                    observacion="",
                    usuario=usuario,
                )

            etapa = "serializar_respuesta"
            cargo_serializado = _serializar_cargo_detalle(cargo)
            return {
                "ok": True,
                "mensaje": "Cargo modificado correctamente.",
                "cargo": cargo_serializado,
                "lote_carga_id": lote_final.id,
            }
    except CargoPof.DoesNotExist:
        return {
            "ok": False,
            "tipo": "no_encontrado",
            "mensaje": "No se encontró el cargo solicitado.",
            "errores": {"cargo_id": ["No se encontró el cargo solicitado."]},
        }
    except ValidationError as error:
        logger.warning(
            "Validacion al modificar cargo POF cargo_id=%s usuario_id=%s etapa=%s tipo=%s detalle=%s",
            cargo_id,
            usuario_id,
            etapa,
            error.__class__.__name__,
            error,
        )
        return {
            "ok": False,
            "tipo": "validacion",
            "mensaje": "No se pudo modificar el cargo.",
            "errores": _errores_validation_error(error),
        }
    except IntegrityError as error:
        logger.warning(
            "Integridad al modificar cargo POF cargo_id=%s usuario_id=%s etapa=%s tipo=%s detalle=%s",
            cargo_id,
            usuario_id,
            etapa,
            error.__class__.__name__,
            error,
        )
        return {
            "ok": False,
            "tipo": "validacion",
            "mensaje": "No se pudo modificar el cargo.",
            "errores": {"__all__": ["Los datos enviados no cumplen las reglas de integridad."]},
        }
    except Exception as error:
        logger.exception(
            "Error inesperado al modificar cargo POF cargo_id=%s usuario_id=%s etapa=%s tipo=%s detalle=%s",
            cargo_id,
            usuario_id,
            etapa,
            error.__class__.__name__,
            error,
        )
        return {
            "ok": False,
            "tipo": "interno",
            "mensaje": "Ocurrió un error interno al guardar. Informe al administrador.",
            "errores": {},
        }


def cambiar_estado_cargo_pof(cargo_id, estado_nuevo, usuario=None):
    estados_validos = {
        CargoPof.EstadoPof.AFECTADO,
        CargoPof.EstadoPof.DESAFECTADO,
    }
    estado_nuevo = _texto(estado_nuevo).upper()
    if estado_nuevo not in estados_validos:
        return {
            "ok": False,
            "tipo": "validacion",
            "mensaje": "Hay errores de validación.",
            "errores": {"estado_pof": ["El estado indicado no es válido."]},
        }

    try:
        with transaction.atomic():
            cargo = CargoPof.objects.select_for_update().get(pk=cargo_id)

            estado_anterior = cargo.estado_pof
            if estado_anterior == estado_nuevo:
                return {
                    "ok": False,
                    "tipo": "sin_cambios",
                    "mensaje": "No hay cambios para guardar.",
                    "errores": {"estado_pof": ["El cargo ya tiene el estado solicitado."]},
                }

            valores_anteriores = _valores_nuevos_cargo(cargo)
            cargo.estado_pof = estado_nuevo
            cargo.save()
            valores_nuevos = _valores_nuevos_cargo(cargo)

            es_afectacion = estado_nuevo == CargoPof.EstadoPof.AFECTADO
            tipo_operacion = (
                LoteCargaPof.TipoOperacion.AFECTACION
                if es_afectacion
                else LoteCargaPof.TipoOperacion.DESAFECTACION
            )
            tipo_movimiento = (
                MovimientoCargoPof.TipoMovimiento.AFECTACION
                if es_afectacion
                else MovimientoCargoPof.TipoMovimiento.DESAFECTACION
            )

            lote = _crear_lote_administrativo(cargo, tipo_operacion, usuario)
            MovimientoCargoPof.objects.create(
                cargo=cargo,
                lote_carga=lote,
                snapshot_padron=_obtener_snapshot_vigente(cargo.localizacion),
                tipo_movimiento=tipo_movimiento,
                estado_anterior=estado_anterior,
                estado_nuevo=estado_nuevo,
                valores_anteriores=valores_anteriores,
                valores_nuevos=valores_nuevos,
                observacion="",
                usuario=usuario,
            )

            return {
                "ok": True,
                "mensaje": "Estado del cargo actualizado correctamente.",
                "cargo": _serializar_cargo_detalle(cargo),
                "lote_carga_id": lote.id,
            }
    except CargoPof.DoesNotExist:
        return {
            "ok": False,
            "tipo": "no_encontrado",
            "mensaje": "No se encontró el cargo solicitado.",
            "errores": {"cargo_id": ["No se encontró el cargo solicitado."]},
        }
    except (ValidationError, IntegrityError) as error:
        errores = _errores_validation_error(error) if isinstance(error, ValidationError) else {"__all__": [str(error)]}
        return {
            "ok": False,
            "tipo": "validacion",
            "mensaje": "No se pudo cambiar el estado del cargo.",
            "errores": errores,
        }


def eliminar_cargo_pof(cargo_id, usuario=None):
    try:
        with transaction.atomic():
            cargo = CargoPof.objects.select_for_update().get(pk=cargo_id)

            cargo_id_eliminado = cargo.id
            MovimientoCargoPof.objects.filter(cargo=cargo).delete()
            cargo.delete()

            return {
                "ok": True,
                "mensaje": "Cargo eliminado correctamente.",
                "cargo_id": cargo_id_eliminado,
            }
    except CargoPof.DoesNotExist:
        return {
            "ok": False,
            "tipo": "no_encontrado",
            "mensaje": "No se encontró el cargo solicitado.",
            "errores": {"cargo_id": ["No se encontró el cargo solicitado."]},
        }
    except (ValidationError, IntegrityError) as error:
        errores = _errores_validation_error(error) if isinstance(error, ValidationError) else {"__all__": [str(error)]}
        return {
            "ok": False,
            "tipo": "validacion",
            "mensaje": "No se pudo eliminar el cargo.",
            "errores": errores,
        }


def _resultado_eliminacion_bloqueada(mensaje, campo):
    """
    Construye una respuesta segura cuando una cabecera POF no se puede eliminar.

    - Mantiene un mensaje claro para la vista sin exponer detalles internos.
    - Reutiliza la misma forma de error para Reunidas y Proyectos Especiales.
    - No realiza escrituras ni decide permisos de usuario.
    """
    return {"ok": False, "mensaje": mensaje, "errores": {campo: [mensaje]}}


def _dependencias_cabecera_bloqueadas(cabecera, campo_cabecera):
    """
    Bloquea y resume solo las dependencias exactas y coherentes de una cabecera.

    - Exige que lote, cargo y localizacion coincidan simultaneamente con la cabecera.
    - Detecta cruces de cabecera o localizacion y corta la operacion sin borrar.
    - Devuelve IDs bloqueados solo cuando el conjunto es seguro para validar y eliminar.
    """
    campo_otro = (
        "proyecto_especial" if campo_cabecera == "reunida" else "reunida"
    )
    filtro_cabecera = {f"{campo_cabecera}_id": cabecera.pk}
    filtro_cabecera_exacta = {
        **filtro_cabecera,
        f"{campo_otro}__isnull": True,
    }
    localizacion_ids = list(
        LocalizacionPof.objects.select_for_update()
        .filter(**filtro_cabecera_exacta)
        .values_list("pk", flat=True)
    )
    localizacion_inconsistente = (
        LocalizacionPof.objects.select_for_update()
        .filter(**filtro_cabecera)
        .exclude(**{f"{campo_otro}__isnull": True})
        .exists()
    )
    if localizacion_inconsistente:
        return {"ok": False, "dependencias": {}}

    lotes_cabecera = LoteCargaPof.objects.select_for_update().filter(
        **filtro_cabecera
    )
    lotes_localizaciones = LoteCargaPof.objects.select_for_update().filter(
        localizacion_id__in=localizacion_ids
    )
    lote_inconsistente = (
        lotes_cabecera.exclude(**{f"{campo_otro}__isnull": True}).exists()
        or lotes_cabecera.exclude(localizacion_id__in=localizacion_ids).exists()
        or lotes_localizaciones.exclude(
            Q(**filtro_cabecera) & Q(**{f"{campo_otro}__isnull": True})
        ).exists()
    )
    if lote_inconsistente:
        return {"ok": False, "dependencias": {}}

    lote_ids = list(
        lotes_cabecera.filter(
            localizacion_id__in=localizacion_ids,
            **{f"{campo_otro}__isnull": True},
        )
        .values_list("pk", flat=True)
    )
    snapshot_ids = list(
        SnapshotPadronLocalizacionPof.objects.select_for_update()
        .filter(localizacion_id__in=localizacion_ids)
        .values_list("pk", flat=True)
    )
    cargos_localizaciones = CargoPof.objects.select_for_update().filter(
        localizacion_id__in=localizacion_ids
    )
    cargos_lotes = CargoPof.objects.select_for_update().filter(
        lote_carga_id__in=lote_ids
    )
    cargo_inconsistente = (
        cargos_localizaciones.exclude(lote_carga_id__in=lote_ids).exists()
        or cargos_lotes.exclude(localizacion_id__in=localizacion_ids).exists()
        or cargos_localizaciones.filter(lote_carga_id__in=lote_ids)
        .exclude(lote_carga__localizacion_id=F("localizacion_id"))
        .exists()
    )
    if cargo_inconsistente:
        return {"ok": False, "dependencias": {}}

    cargo_ids = list(
        cargos_localizaciones.filter(lote_carga_id__in=lote_ids)
        .filter(lote_carga__localizacion_id=F("localizacion_id"))
        .values_list("pk", flat=True)
    )
    return {
        "ok": True,
        "dependencias": {
            "localizacion_ids": localizacion_ids,
            "lote_ids": lote_ids,
            "snapshot_ids": snapshot_ids,
            "cargo_ids": cargo_ids,
        },
    }


def _existen_movimientos_cabecera(dependencias):
    """
    Indica si una cabecera tiene al menos un movimiento de cargo asociado.

    - Consulta solo existencia y no carga ni cuenta movimientos completos.
    - Usa los IDs de dependencias ya acotados y bloqueados por la cabecera objetivo.
    - Mantiene a MovimientoCargoPof como unica señal de actividad administrativa.
    """
    return MovimientoCargoPof.objects.filter(
        Q(cargo_id__in=dependencias["cargo_ids"])
        | Q(lote_carga_id__in=dependencias["lote_ids"])
        | Q(snapshot_padron_id__in=dependencias["snapshot_ids"])
    ).exists()


def _eliminar_dependencias_cabecera(dependencias):
    """
    Borra dependencias de una cabecera que no tiene movimientos asociados.

    - Respeta el orden de las relaciones protegidas: cargos, lotes, snapshots y localizaciones.
    - Usa exclusivamente IDs obtenidos desde la cabecera objetivo bloqueada.
    - Debe ejecutarse dentro de la transaccion de validacion y borrado.
    """
    CargoPof.objects.filter(pk__in=dependencias["cargo_ids"]).delete()
    LoteCargaPof.objects.filter(pk__in=dependencias["lote_ids"]).delete()
    SnapshotPadronLocalizacionPof.objects.filter(
        pk__in=dependencias["snapshot_ids"]
    ).delete()
    LocalizacionPof.objects.filter(pk__in=dependencias["localizacion_ids"]).delete()


def eliminar_reunida_pof(reunida_id):
    """
    Elimina una Reunida que no registra movimientos administrativos.

    - Bloquea cabecera y dependencias dentro de una unica transaccion atomica.
    - Rechaza Reunidas usadas como base y cualquier MovimientoCargoPof asociado.
    - Nunca modifica la Reunida base anterior ni datos de otras cabeceras.
    """
    try:
        with transaction.atomic():
            reunida = ReunidaPof.objects.select_for_update().get(pk=reunida_id)
            if reunida.reunidas_derivadas.exists():
                return _resultado_eliminacion_bloqueada(
                    "No se puede eliminar esta Reunida porque es utilizada como base por otra Reunida.",
                    "reunida",
                )

            resultado_dependencias = _dependencias_cabecera_bloqueadas(
                reunida, "reunida"
            )
            if not resultado_dependencias["ok"]:
                return _resultado_eliminacion_bloqueada(
                    "No se puede eliminar esta Reunida porque existen inconsistencias de integridad en sus dependencias.",
                    "reunida",
                )

            dependencias = resultado_dependencias["dependencias"]
            if _existen_movimientos_cabecera(dependencias):
                return _resultado_eliminacion_bloqueada(
                    "No se puede eliminar esta Reunida porque registra actividad administrativa posterior.",
                    "reunida",
                )

            _eliminar_dependencias_cabecera(dependencias)
            reunida.delete()
            return {"ok": True, "mensaje": "Reunida POF eliminada correctamente."}
    except ReunidaPof.DoesNotExist:
        return _resultado_eliminacion_bloqueada(
            "La Reunida indicada no existe.", "reunida_id"
        )
    except ProtectedError:
        return _resultado_eliminacion_bloqueada(
            "No se puede eliminar esta Reunida porque conserva referencias protegidas.",
            "reunida",
        )
    except (ValidationError, IntegrityError) as error:
        errores = (
            _errores_validation_error(error)
            if isinstance(error, ValidationError)
            else {"__all__": [str(error)]}
        )
        return {"ok": False, "mensaje": "No se pudo eliminar la Reunida.", "errores": errores}


def eliminar_proyecto_especial_pof(proyecto_id):
    """
    Elimina un Proyecto Especial que no registra movimientos administrativos.

    - Reutiliza la transacción y los bloqueos de la eliminación de Reunidas.
    - Rechaza proyectos base de otros y cualquier MovimientoCargoPof asociado.
    - Elimina sus dependencias solo después de confirmar que no hay movimientos.
    """
    try:
        with transaction.atomic():
            proyecto = ProyectosEspecialesPof.objects.select_for_update().get(pk=proyecto_id)

            if proyecto.proyectos_derivados.exists():
                return _resultado_eliminacion_bloqueada(
                    "No se puede eliminar este Proyecto Especial porque es utilizado como base por otro proyecto.",
                    "proyecto",
                )

            resultado_dependencias = _dependencias_cabecera_bloqueadas(
                proyecto, "proyecto_especial"
            )
            if not resultado_dependencias["ok"]:
                return _resultado_eliminacion_bloqueada(
                    "No se puede eliminar este Proyecto Especial porque existen inconsistencias de integridad en sus dependencias.",
                    "proyecto",
                )

            dependencias = resultado_dependencias["dependencias"]
            if _existen_movimientos_cabecera(dependencias):
                return _resultado_eliminacion_bloqueada(
                    "No se puede eliminar este Proyecto Especial porque registra actividad administrativa.",
                    "proyecto",
                )

            _eliminar_dependencias_cabecera(dependencias)
            proyecto.delete()

            return {
                "ok": True,
                "mensaje": "Proyecto Especial POF eliminado correctamente.",
            }
    except ProyectosEspecialesPof.DoesNotExist:
        return {
            "ok": False,
            "mensaje": "El Proyecto Especial indicado no existe.",
            "errores": {"proyecto_id": ["No se encontró el Proyecto Especial."]},
        }
    except ProtectedError:
        return {
            "ok": False,
            "mensaje": "No se pudo eliminar el Proyecto Especial porque conserva referencias protegidas.",
            "errores": {"proyecto": ["Hay registros relacionados que impiden la eliminación."]},
        }
    except (ValidationError, IntegrityError) as error:
        errores = _errores_validation_error(error) if isinstance(error, ValidationError) else {"__all__": [str(error)]}
        return {
            "ok": False,
            "mensaje": "No se pudo eliminar el Proyecto Especial.",
            "errores": errores,
        }


def guardar_carga_pof(datos, usuario=None):
    """
    Guarda una carga POF tomando al CEIC como fuente real de cargo y puntos.

    - Valida primero la entrada mínima editable del usuario.
    - Oficializa luego cada cargo desde `cenpe.ceic_puntos` antes de consolidar.
    - Persiste descripción, puntos, total y snapshot usando solo datos reales del CEIC.
    """
    errores = _validar_datos_guardado_minimos(datos)
    if errores:
        return {
            "ok": False,
            "mensaje": "Hay errores de validación.",
            "errores": errores,
        }

    try:
        with transaction.atomic():
            advertencias_guardado = []
            reunida, proyecto = _obtener_cabecera(datos)
            validacion_padron = _validar_y_oficializar_padron_guardado(datos, reunida, proyecto)
            if not validacion_padron["ok"]:
                return {
                    "ok": False,
                    "mensaje": "Hay errores de validacion.",
                    "errores": validacion_padron["errores"],
                }
            padron_oficial = validacion_padron["padron"]
            datos["padron"] = padron_oficial
            oficializacion_ceic = _oficializar_cargos_desde_ceic(datos, reunida)
            if not oficializacion_ceic["ok"]:
                return {
                    "ok": False,
                    "mensaje": "Hay errores de validacion.",
                    "errores": {"cargos": oficializacion_ceic["errores"]},
                }
            localizacion = _obtener_localizacion(
                datos,
                reunida,
                proyecto,
                advertencias=advertencias_guardado,
            )
            snapshot = _obtener_snapshot(localizacion, datos["padron"], usuario)
            lote = LoteCargaPof.objects.create(
                reunida=reunida,
                proyecto_especial=proyecto,
                localizacion=localizacion,
                tipo_operacion=datos.get("tipo_operacion") or LoteCargaPof.TipoOperacion.ALTA,
                usuario=usuario,
            )

            resultado_consolidado = aplicar_alta_consolidada(
                localizacion,
                lote,
                oficializacion_ceic["cargos"],
                usuario=usuario,
            )

            cargos_creados = []
            for item_creado in resultado_consolidado["creados"]:
                cargo = item_creado["cargo"]
                cargo_data = item_creado["cargo_data"]
                observacion_movimiento = _observacion_movimiento_desde_carga(
                    cargo_data,
                    datos,
                )
                MovimientoCargoPof.objects.create(
                    cargo=cargo,
                    lote_carga=lote,
                    snapshot_padron=snapshot,
                    tipo_movimiento=MovimientoCargoPof.TipoMovimiento.ALTA,
                    estado_anterior="",
                    estado_nuevo=CargoPof.EstadoPof.AFECTADO,
                    valores_anteriores={},
                    valores_nuevos=_valores_nuevos_cargo(cargo),
                    observacion=observacion_movimiento,
                    usuario=usuario,
                )
                cargos_creados.append(
                    {
                        "id": cargo.id,
                        "ceic": cargo.ceic,
                        "cargo": cargo.cargo,
                        "cantidad": str(cargo.cantidad),
                        "unidad_cantidad": cargo.unidad_cantidad,
                        "puntos_asignados": str(cargo.puntos_asignados),
                        "total": str(cargo.total),
                        "observacion": cargo.observacion,
                    }
                )

            cargos_incrementados = []
            for item_incrementado in resultado_consolidado["incrementados"]:
                cargo = item_incrementado["cargo"]
                cargo_data = item_incrementado["cargo_data"]
                valores_anteriores = item_incrementado["valores_anteriores"]
                valores_nuevos = _valores_nuevos_cargo(cargo)
                MovimientoCargoPof.objects.create(
                    cargo=cargo,
                    lote_carga=lote,
                    snapshot_padron=snapshot,
                    tipo_movimiento=MovimientoCargoPof.TipoMovimiento.MODIFICACION,
                    estado_anterior=CargoPof.EstadoPof.AFECTADO,
                    estado_nuevo=CargoPof.EstadoPof.AFECTADO,
                    valores_anteriores=valores_anteriores,
                    valores_nuevos={
                        "cantidad": valores_nuevos["cantidad"],
                        "total": valores_nuevos["total"],
                    },
                    observacion=_observacion_movimiento_desde_carga(
                        cargo_data,
                        datos,
                    ),
                    usuario=usuario,
                )
                cargos_incrementados.append(
                    {
                        "id": cargo.id,
                        "ceic": cargo.ceic,
                        "cargo": cargo.cargo,
                        "cantidad": str(cargo.cantidad),
                        "unidad_cantidad": cargo.unidad_cantidad,
                        "puntos_asignados": str(cargo.puntos_asignados),
                        "total": str(cargo.total),
                        "observacion": cargo.observacion,
                    }
                )

            cantidad_incrementados = len(cargos_incrementados)
            mensaje = "Carga guardada correctamente."
            if cantidad_incrementados:
                sufijo = "s" if cantidad_incrementados != 1 else ""
                mensaje = f"Carga guardada. Se incremento {cantidad_incrementados} cargo{sufijo} existente{sufijo}."

            return {
                "ok": True,
                "mensaje": mensaje,
                "reunida_id": reunida.id if reunida else None,
                "proyecto_especial_id": proyecto.id if proyecto else None,
                "localizacion_id": localizacion.id,
                "snapshot_padron_id": snapshot.id,
                "lote_carga_id": lote.id,
                "cargos_creados": cargos_creados,
                "cargos_incrementados": cargos_incrementados,
                "creados": len(cargos_creados),
                "incrementados": cantidad_incrementados,
                "consolidados_payload": resultado_consolidado["total_cargos_consolidados"],
                "total_cargos_procesados": resultado_consolidado["total_cargos_procesados"],
                "advertencias": advertencias_guardado + resultado_consolidado["advertencias"],
            }
    except ProyectosEspecialesPof.DoesNotExist:
        return {
            "ok": False,
            "mensaje": "No se pudo guardar la carga.",
            "errores": {"proyecto_especial_id": ["El proyecto especial indicado no existe."]},
        }
    except (ValidationError, IntegrityError) as error:
        errores = _errores_validation_error(error) if isinstance(error, ValidationError) else {"__all__": [str(error)]}
        return {
            "ok": False,
            "mensaje": "No se pudo guardar la carga.",
            "errores": errores,
        }
    except ObjectDoesNotExist as error:
        return {
            "ok": False,
            "mensaje": "No se pudo guardar la carga.",
            "errores": {"__all__": [str(error)]},
        }
