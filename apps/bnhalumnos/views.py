"""Vistas y endpoints AJAX para la carga integral de BNH Alumnos.

La pantalla trabaja como una aplicacion de una sola carga: renderiza catalogos,
arma colecciones temporales en JavaScript y envia un unico JSON para guardar
alumno, obras sociales, discapacidades, planes sociales y tutores.
"""

import json
import re

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import connections, transaction
from django.http import JsonResponse
from django.shortcuts import render
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_GET, require_POST

# Catálogos externos reutilizados por la pantalla. Se consultan desde
# bnhpersonas para no duplicar datos maestros dentro del módulo alumnos.
from apps.bnhpersonas.models import (
    DocumentoTipo,
    Provincias,
    Localidades,
    Nacionalidad,
    Pais,
    Sexo,
    EstadosCiviles,
    RelacionParentesco,
    TipoPlanesSociales,
    NivelFormacion,
    TipoComunidadOriginaria,
    TipoLenguaOriginaria,
    TipoDiscapacidad,
    CodAreasTelefonos,
)

from .models import (
    Alumno,
    Tutor,
    CatalogoObraSocial,
    CatalogoSinoTipo,
    TipoObraSocial,
    normalizar_documento_bnh,
    normalizar_cuil_opcional,
    validar_cuil_con_documento,
)
from .forms import (
    AlumnoForm,
    TutorForm,
    ObraSocialForm,
    DiscapacidadForm,
    PlanesSocialesForm,
    ParentalForm,
    form_errors_to_json,
    payload_tiene_datos,
    validar_texto_persona,
    validar_y_guardar,
)
from .permisos import bnh_alumnos_required


def _solo_digitos(valor):
    """Devuelve solo los dígitos de un valor recibido desde formulario o querystring."""

    return re.sub(r"\D", "", str(valor or ""))


def _validar_cuil_para_ui(valor, nombre="CUIL", requerido=False):
    """Normaliza CUIL para la interfaz sin volverlo requisito de existencia."""

    cuil = normalizar_cuil_opcional(valor, nombre)
    if requerido and not cuil:
        raise ValidationError(f"{nombre} es obligatorio.")
    return cuil


def _catalogo(modelo):
    """Obtiene opciones de catálogo sin bloquear la pantalla si falla una consulta."""

    try:
        return list(modelo.objects.all())
    except Exception:
        return []


def _fecha_iso(valor):
    """Convierte fechas de modelo al formato ISO que espera el frontend."""

    if not valor:
        return ""
    return valor.isoformat()


def _es_menor_de_18(fecha_nacimiento):
    """Determina mayoría de edad por fecha exacta, incluyendo el día de cumpleaños."""

    if not fecha_nacimiento:
        return False
    hoy = timezone.localdate()
    edad = hoy.year - fecha_nacimiento.year
    if (hoy.month, hoy.day) < (fecha_nacimiento.month, fecha_nacimiento.day):
        edad -= 1
    return edad < 18


def _decimal_text(valor):
    """Serializa decimales como texto para no perder formato en JSON."""

    if valor is None:
        return ""
    return str(valor)


def _fk_id(objeto, campo):
    """Extrae el id crudo de un ForeignKey para seleccionar opciones en HTML."""

    return getattr(objeto, f"{campo}_id", "") or ""


def _telefono_label(objeto):
    """Arma una etiqueta legible con codigo de area y numero local."""

    if not getattr(objeto, "telefono", None) or not getattr(objeto, "codigo_area_id", None):
        return ""
    return f"({objeto.codigo_area.codigo}) {objeto.telefono}"


def _error_json(exc):
    """Unifica errores Django para devolverlos en JsonResponse."""

    if hasattr(exc, "message_dict"):
        return exc.message_dict
    if hasattr(exc, "messages"):
        return exc.messages
    return str(exc)


def _alumno_payload(alumno):
    """Arma el JSON de alumno usado para autocompletar el formulario."""

    return {
        "id": alumno.id,
        "id_persona_sge": alumno.id_persona_sge,
        "id_persona_jurisdiccional": alumno.id_persona_jurisdiccional or "",
        "apellidos": alumno.apellidos,
        "nombres": alumno.nombres,
        "tipo_doc": _fk_id(alumno, "tipo_doc"),
        "tipo_doc_label": str(alumno.tipo_doc) if alumno.tipo_doc_id else "",
        "nro_doc": alumno.nro_doc,
        "cuil": alumno.cuil or "",
        "fecha_nacimiento": _fecha_iso(alumno.fecha_nacimiento),
        "sexo": _fk_id(alumno, "sexo"),
        "nacionalidad": _fk_id(alumno, "nacionalidad"),
        "prov_nacimiento": _fk_id(alumno, "prov_nacimiento"),
        "lugar_nacimiento": alumno.lugar_nacimiento or "",
        "loc_nacimiento": _fk_id(alumno, "loc_nacimiento"),
        "pais_nacimiento": _fk_id(alumno, "pais_nacimiento"),
        "prov_residencia": _fk_id(alumno, "prov_residencia"),
        "pais_residencia": _fk_id(alumno, "pais_residencia"),
        "loc_residencia": _fk_id(alumno, "loc_residencia"),
        "est_civil": _fk_id(alumno, "est_civil"),
        "pertenece_pueblo_indigena": _fk_id(alumno, "pertenece_pueblo_indigena"),
        "comunidad_originaria": _fk_id(alumno, "comunidad_originaria"),
        "lengua_originaria": _fk_id(alumno, "lengua_originaria"),
        "tiene_discapacidad": _fk_id(alumno, "tiene_discapacidad"),
        "tiene_ppi": _fk_id(alumno, "tiene_ppi"),
        "codigo_area": _fk_id(alumno, "codigo_area"),
        "codigo_area_codigo": alumno.codigo_area.codigo if alumno.codigo_area_id else "",
        "telefono": alumno.telefono or "",
        "telefono_normalizado": alumno.telefono_normalizado or "",
        "telefono_label": _telefono_label(alumno),
        "es_celular": alumno.es_celular,
        "whatsapp": alumno.whatsapp,
        "email": alumno.email,
        "talla": _decimal_text(alumno.talla),
        "peso": _decimal_text(alumno.peso),
        "observaciones": alumno.observaciones,
    }


def _tutor_payload(tutor):
    """Arma el JSON de tutor usado por la búsqueda y por relaciones parentales."""

    return {
        "id": tutor.id,
        "cuil_tutor": tutor.cuil_tutor,
        "apellidos": tutor.apellidos,
        "nombres": tutor.nombres,
        "tipo_doc": _fk_id(tutor, "tipo_doc"),
        "tipo_doc_label": str(tutor.tipo_doc) if tutor.tipo_doc_id else "",
        "nro_doc": tutor.nro_doc,
        "fecha_nac": _fecha_iso(tutor.fecha_nac),
        "nacionalidad": _fk_id(tutor, "nacionalidad"),
        "pais_nac": _fk_id(tutor, "pais_nac"),
        "nivel_formacion": _fk_id(tutor, "nivel_formacion"),
        "ocupacion": tutor.ocupacion,
        "prov_resid": _fk_id(tutor, "prov_resid"),
        "loc_resid": _fk_id(tutor, "loc_resid"),
        "cod_postal": tutor.cod_postal,
        "calle": tutor.calle,
        "nro": tutor.nro,
        "piso": tutor.piso,
        "dpto": tutor.dpto,
        "mail": tutor.mail,
        "codigo_area": _fk_id(tutor, "codigo_area"),
        "codigo_area_codigo": tutor.codigo_area.codigo if tutor.codigo_area_id else "",
        "telefono": tutor.telefono or "",
        "telefono_normalizado": tutor.telefono_normalizado or "",
        "telefono_label": _telefono_label(tutor),
        "es_celular": tutor.es_celular,
        "whatsapp": tutor.whatsapp,
    }


def _relaciones_payload(alumno):
    """Serializa relaciones hijas sin bloquear el autocompletado principal."""

    obras = []
    try:
        for item in alumno.obras_sociales.select_related("tipo_obra", "nombre_obra").all():
            obras.append({
                "tipo_obra": _fk_id(item, "tipo_obra"),
                "tipo_obra_label": str(item.tipo_obra),
                "nombre_obra": _fk_id(item, "nombre_obra"),
                "nombre_obra_label": str(item.nombre_obra),
                "fecha_inicio": _fecha_iso(item.fecha_inicio),
                "fecha_fin": _fecha_iso(item.fecha_fin),
                "descripcion": item.descripcion,
                "estado": item.estado,
            })
    except Exception:
        obras = []

    discapacidades = []
    try:
        for item in alumno.discapacidades.select_related("id_discapacidad").all():
            discapacidades.append({
                "id_discapacidad": _fk_id(item, "id_discapacidad"),
                "id_discapacidad_label": str(item.id_discapacidad),
                "fecha_inicio": _fecha_iso(item.fecha_inicio),
                "fecha_fin": _fecha_iso(item.fecha_fin),
                "porcentaje": _decimal_text(item.porcentaje),
                "certificado_cud": item.certificado_cud,
                "observaciones": item.observaciones,
            })
    except Exception:
        discapacidades = []

    planes = []
    try:
        for item in alumno.planes_sociales.select_related("id_beneficio").all():
            planes.append({
                "id_beneficio": _fk_id(item, "id_beneficio"),
                "id_beneficio_label": str(item.id_beneficio),
                "descripcion": item.descripcion,
                "fecha_desde": _fecha_iso(item.fecha_desde),
                "fecha_hasta": _fecha_iso(item.fecha_hasta),
                "monto": _decimal_text(item.monto),
                "estado": item.estado,
                "observaciones": item.observaciones,
            })
    except Exception:
        planes = []

    tutores = []
    try:
        for item in alumno.parentales.select_related("id_tutor", "parentesco").all():
            tutor_data = _tutor_payload(item.id_tutor)
            tutor_data.update({
                "parentesco": _fk_id(item, "parentesco"),
                "parentesco_label": str(item.parentesco),
                "parental_observaciones": item.observaciones,
            })
            tutores.append(tutor_data)
    except Exception:
        tutores = []

    return {
        "obras_sociales": obras,
        "discapacidades": discapacidades,
        "planes_sociales": planes,
        "tutores": tutores,
    }


def _tipo_documento_busqueda(tipo_doc_id):
    """Resuelve un tipo documental real antes de normalizar una búsqueda."""

    if tipo_doc_id in (None, ""):
        return None
    try:
        tipo_doc_id = int(tipo_doc_id)
    except (TypeError, ValueError):
        raise ValidationError("El tipo de documento seleccionado no es válido.")
    tipo_doc = DocumentoTipo.objects.filter(pk=tipo_doc_id).first()
    if not tipo_doc:
        raise ValidationError("El tipo de documento seleccionado no existe.")
    return tipo_doc


class SGEConsultaNoDisponible(Exception):
    """Indica que no fue posible consultar la fuente consolidada de personas SGE."""


SGE_PERSONAS_MATERIALIZADA = "public.personas_alumnos_sge"
SGE_TIPOS_DOCUMENTO_EXTRANJERO = (8, 9, 10)
SGE_TIPO_DOCUMENTO_A_BNH = {
    1: 1,
    2: 2,
    3: 3,
    4: 4,
    5: 5,
    8: 13,
    9: 13,
    10: 13,
    11: 11,
    12: 12,
}
SGE_ESTADO_CIVIL_A_BNH = {
    1: 1,  # Soltero
    2: 2,  # Casado
    3: 4,  # Viudo
    4: 3,  # Divorciado
}
# Equivalencias semánticas comprobadas entre los catálogos usados en SGE y BNH.
# Un código positivo no listado sigue permitiendo afirmar pertenencia, pero deja
# la comunidad para selección manual.
SGE_COMUNIDAD_A_BNH = {
    1: 2,   # Atacama
    2: 3,   # Ava Guaraní
    3: 4,   # Aymara
    12: 13, # Guaraní
    18: 19, # Mbyá
    19: 20, # Moqoit / Mocoví
    22: 23, # Qom
    23: 24, # Quechua
    34: 35, # Wichí
    35: 37, # Otro/s
    36: 36, # Quilmes
}
SGE_TIPOS_TELEFONO_CONOCIDOS = {1, 2, 3, 4, 5}
SGE_TIPO_TELEFONO_CELULAR = 3


def _entero_sge(valor):
    """Convierte códigos SGE a entero sin forzar valores inválidos."""

    if valor in (None, ""):
        return None
    try:
        return int(valor)
    except (TypeError, ValueError):
        return None


def _catalogo_pk_si_existe(modelo, valor, *, excluidos=()):
    """Devuelve el PK sólo cuando el código existe realmente en el catálogo BNH."""

    codigo = _entero_sge(valor)
    if codigo is None or codigo in excluidos:
        return None
    try:
        return codigo if modelo.objects.filter(pk=codigo).exists() else None
    except Exception:
        return None


def _texto_persona_sge_seguro(valor):
    """Conserva nombre/apellido sólo si supera la misma validación usada por BNH."""

    try:
        texto = validar_texto_persona(valor)
    except ValidationError:
        return None
    return texto or None


def _email_sge_seguro(valor):
    """Devuelve el email SGE únicamente si el formato es válido para BNH."""

    email = str(valor or "").strip()
    if not email:
        return None
    try:
        validate_email(email)
    except ValidationError:
        return None
    return email


def _lugar_nacimiento_sge_seguro(valor):
    """Aplica las restricciones del campo libre de nacimiento antes de precargarlo."""

    texto = str(valor or "").strip().upper()
    if not texto or len(texto) > 100 or re.search(r"\d", texto):
        return None
    return texto


def _codigo_area_bnh_desde_sge(valor):
    """Resuelve un código de área SGE contra el catálogo BNH sin elegir ambiguos."""

    codigo = _solo_digitos(valor)
    if not codigo:
        return None
    try:
        candidatos = list(
            CodAreasTelefonos.objects.filter(codigo=codigo)
            .values_list("pk", flat=True)[:2]
        )
    except Exception:
        return None
    return candidatos[0] if len(candidatos) == 1 else None


def _telefono_sge_a_payload(codigo_area, numero, tipo_telefono):
    """Precarga contacto sólo si código, número y tipo son inequívocos y válidos."""

    codigo_area_bnh = _codigo_area_bnh_desde_sge(codigo_area)
    numero_bnh = _solo_digitos(numero)
    tipo_sge = _entero_sge(tipo_telefono)

    if (
        not codigo_area_bnh
        or not re.fullmatch(r"\d{6,8}", numero_bnh or "")
        or tipo_sge not in SGE_TIPOS_TELEFONO_CONOCIDOS
    ):
        return {}

    return {
        "codigo_area": codigo_area_bnh,
        "telefono": numero_bnh,
        "es_celular": tipo_sge == SGE_TIPO_TELEFONO_CELULAR,
    }


def _aliases_sge_personas():
    """Prioriza la BD consolidada SGE-NACION y permite un alias explícito."""

    aliases = []
    alias_configurado = str(
        getattr(settings, "BNHALUMNOS_SGE_DB_ALIAS", "") or ""
    ).strip()
    if alias_configurado:
        aliases.append(alias_configurado)
    if "sge_nacion" not in aliases:
        aliases.append("sge_nacion")
    return aliases


def _alias_sge_con_persona():
    """Obtiene una conexión Django que exponga la materializada consolidada."""

    hubo_alias_configurado = False
    for alias in _aliases_sge_personas():
        if alias not in connections.databases:
            continue
        hubo_alias_configurado = True
        try:
            with connections[alias].cursor() as cursor:
                cursor.execute("SELECT to_regclass(%s)", [SGE_PERSONAS_MATERIALIZADA])
                if cursor.fetchone()[0]:
                    return alias
        except Exception:
            continue

    if hubo_alias_configurado:
        raise SGEConsultaNoDisponible(
            "La conexión SGE disponible no expone la materializada de personas necesaria para verificar la identidad."
        )
    raise SGEConsultaNoDisponible(
        "No hay una conexión SGE-NACION configurada para verificar la identidad del alumno."
    )


def _tipos_documento_sge_para_bnh(tipo_doc):
    """Traduce el tipo BNH a los códigos documentales que deben buscarse en SGE."""

    if not tipo_doc:
        return ()
    tipo_bnh = int(tipo_doc.pk)
    if tipo_bnh == 13:
        # BNH agrupa los tres subtipos extranjeros de SGE bajo Documento extranjero.
        return SGE_TIPOS_DOCUMENTO_EXTRANJERO
    if tipo_bnh in {1, 2, 3, 4, 5, 11, 12}:
        return (tipo_bnh,)
    return ()


def _persona_sge_a_payload(fila):
    """Convierte la fila consolidada SGE sólo a valores seguros para Carga Alumno."""

    (
        id_persona,
        apellido,
        nombre,
        tipo_sge,
        nro_documento,
        cuil,
        fecha_nacimiento,
        sexo,
        c_nacionalidad,
        c_pais_nacimiento,
        c_provincia_nacimiento,
        c_localidad_nacimiento,
        lugar_nacimiento,
        c_indigena,
        c_lengua_indigena,
        c_estado_civil_actual,
        c_pais_residencia,
        c_provincia_residencia,
        c_localidad_residencia,
        email,
        codigo_area_telefono,
        nro_telefono,
        c_tipo_telefono,
    ) = fila

    tipo_sge = _entero_sge(tipo_sge)
    tipo_bnh = SGE_TIPO_DOCUMENTO_A_BNH.get(tipo_sge)
    if tipo_bnh and not _catalogo_pk_si_existe(DocumentoTipo, tipo_bnh):
        tipo_bnh = None

    documento_bnh = None
    if tipo_bnh:
        try:
            documento_normalizado = normalizar_documento_bnh(
                tipo_bnh,
                nro_documento,
            )
            if documento_normalizado is None and tipo_bnh in {11, 12}:
                documento_bnh = ""
            else:
                documento_bnh = documento_normalizado
        except ValidationError:
            documento_bnh = None

    cuil_bnh = None
    if tipo_bnh == 1:
        try:
            cuil_normalizado = normalizar_cuil_opcional(cuil, "CUIL del alumno")
            validar_cuil_con_documento(
                cuil_normalizado,
                tipo_bnh,
                documento_bnh,
                "CUIL del alumno",
            )
            cuil_bnh = cuil_normalizado
        except ValidationError:
            cuil_bnh = None
    elif tipo_bnh is not None:
        # BNH sólo admite CUIL cuando el documento es DNI.
        cuil_bnh = ""

    sexo_bnh = _catalogo_pk_si_existe(Sexo, sexo)
    if sexo_bnh not in {1, 2, 3}:
        sexo_bnh = None

    nacionalidad_bnh = _catalogo_pk_si_existe(Nacionalidad, c_nacionalidad)
    pais_nacimiento_bnh = _catalogo_pk_si_existe(
        Pais,
        c_pais_nacimiento,
        excluidos={-2},
    )
    provincia_nacimiento_bnh = None
    if pais_nacimiento_bnh == 14:
        provincia_nacimiento_bnh = _catalogo_pk_si_existe(
            Provincias,
            c_provincia_nacimiento,
            excluidos={99},
        )

    # La materializada conserva sólo el código de localidad SGE. Como todavía
    # no hay una equivalencia de localidad validada contra el catálogo BNH,
    # ambos campos quedan deliberadamente para selección manual.
    _ = c_localidad_nacimiento
    _ = c_localidad_residencia

    lugar_nacimiento_bnh = None
    if pais_nacimiento_bnh and pais_nacimiento_bnh != 14:
        lugar_nacimiento_bnh = _lugar_nacimiento_sge_seguro(lugar_nacimiento)

    indigena_sge = _entero_sge(c_indigena)
    pertenece_bnh = None
    comunidad_bnh = None
    if indigena_sge == 0:
        pertenece_bnh = CatalogoSinoTipo.NO
    elif indigena_sge is not None and indigena_sge > 0:
        pertenece_bnh = CatalogoSinoTipo.SI
        comunidad_bnh = _catalogo_pk_si_existe(
            TipoComunidadOriginaria,
            SGE_COMUNIDAD_A_BNH.get(indigena_sge),
        )

    lengua_sge = _entero_sge(c_lengua_indigena)
    lengua_bnh = None
    if lengua_sge is not None and 1 <= lengua_sge <= 15:
        lengua_bnh = _catalogo_pk_si_existe(TipoLenguaOriginaria, lengua_sge)

    estado_sge = _entero_sge(c_estado_civil_actual)
    estado_bnh = _catalogo_pk_si_existe(
        EstadosCiviles,
        SGE_ESTADO_CIVIL_A_BNH.get(estado_sge),
    )

    pais_residencia_bnh = _catalogo_pk_si_existe(
        Pais,
        c_pais_residencia,
        excluidos={-2},
    )
    provincia_residencia_bnh = None
    if pais_residencia_bnh == 14:
        provincia_residencia_bnh = _catalogo_pk_si_existe(
            Provincias,
            c_provincia_residencia,
            excluidos={99},
        )

    payload = {
        "id_persona_sge": id_persona,
        "apellidos": _texto_persona_sge_seguro(apellido),
        "nombres": _texto_persona_sge_seguro(nombre),
        "tipo_doc": tipo_bnh,
        "nro_doc": documento_bnh,
        "cuil": cuil_bnh,
        "fecha_nacimiento": _fecha_iso(fecha_nacimiento) if fecha_nacimiento else None,
        "sexo": sexo_bnh,
        "nacionalidad": nacionalidad_bnh,
        "pais_nacimiento": pais_nacimiento_bnh,
        "prov_nacimiento": provincia_nacimiento_bnh,
        "loc_nacimiento": None,
        "lugar_nacimiento": lugar_nacimiento_bnh,
        "pais_residencia": pais_residencia_bnh,
        "prov_residencia": provincia_residencia_bnh,
        "loc_residencia": None,
        "est_civil": estado_bnh,
        "pertenece_pueblo_indigena": pertenece_bnh,
        "comunidad_originaria": comunidad_bnh,
        "lengua_originaria": lengua_bnh,
        "email": _email_sge_seguro(email),
    }
    payload.update(
        _telefono_sge_a_payload(
            codigo_area_telefono,
            nro_telefono,
            c_tipo_telefono,
        )
    )
    return payload


def _buscar_personas_sge(*, cuil=None, tipo_doc=None, nro_doc=None):
    """Busca por identidad fuerte sobre la materializada de personas SGE-NACION."""

    condiciones = []
    params = []

    if cuil:
        condiciones.append(
            "REGEXP_REPLACE(COALESCE(p.cuil::text, ''), '[^0-9]', '', 'g') = %s"
        )
        params.append(cuil)

    documento_crudo = str(nro_doc or "").strip()
    if tipo_doc and documento_crudo:
        documento = normalizar_documento_bnh(tipo_doc, documento_crudo)
        tipos_sge = _tipos_documento_sge_para_bnh(tipo_doc)
        if tipos_sge and documento:
            placeholders = ", ".join(["%s"] * len(tipos_sge))
            clase_bnh = int(tipo_doc.pk)
            if clase_bnh == 1:
                comparacion_documento = (
                    "LPAD(REGEXP_REPLACE(COALESCE(p.nro_documento::text, ''), '[^0-9]', '', 'g'), 8, '0') = %s"
                )
            elif clase_bnh in {2, 3, 4, 5}:
                comparacion_documento = (
                    "REGEXP_REPLACE(COALESCE(p.nro_documento::text, ''), '[^0-9]', '', 'g') = %s"
                )
            else:
                comparacion_documento = (
                    "UPPER(BTRIM(COALESCE(p.nro_documento::text, ''))) = %s"
                )
            condiciones.append(
                f"(p.c_tipo_documento IN ({placeholders}) AND {comparacion_documento})"
            )
            params.extend(tipos_sge)
            params.append(documento)

    if not condiciones:
        return []

    alias = _alias_sge_con_persona()
    sql = f"""
        SELECT
            p.id_persona,
            p.apellido,
            p.nombre,
            p.c_tipo_documento,
            p.nro_documento,
            p.cuil,
            p.fecha_nacimiento,
            p.c_sexo,
            p.c_nacionalidad,
            p.c_pais_nacimiento,
            p.c_provincia_nacimiento,
            p.c_localidad_nacimiento,
            p.lugar_nacimiento,
            p.c_indigena,
            p.c_lengua_indigena,
            p.c_estado_civil_actual,
            p.c_pais_residencia,
            p.c_provincia_residencia,
            p.c_localidad_residencia,
            p.email,
            p.codigo_area_telefono,
            p.nro_telefono,
            p.c_tipo_telefono
        FROM {SGE_PERSONAS_MATERIALIZADA} p
        WHERE {" OR ".join(condiciones)}
        ORDER BY p.id_persona
        LIMIT 3
    """
    try:
        with connections[alias].cursor() as cursor:
            cursor.execute(sql, params)
            return cursor.fetchall()
    except Exception as exc:
        raise SGEConsultaNoDisponible(
            "No se pudo consultar la materializada de personas SGE en este momento. "
            "No se asumió que la persona esté ausente."
        ) from exc


def _resolver_persona_sge(*, cuil=None, tipo_doc=None, nro_doc=None):
    """Resuelve una única persona SGE o bloquea cualquier ambigüedad."""

    filas = _buscar_personas_sge(cuil=cuil, tipo_doc=tipo_doc, nro_doc=nro_doc)
    personas = {}
    for fila in filas:
        personas.setdefault(fila[0], fila)

    if len(personas) > 1:
        raise ValidationError(
            "Los identificadores ingresados coinciden con más de una persona en SGE. Revise CUIL y documento antes de continuar."
        )
    if not personas:
        return None
    return _persona_sge_a_payload(next(iter(personas.values())))


def _alumnos_por_identidad(*, cuil=None, tipo_doc=None, nro_doc=None):
    """Reúne coincidencias fuertes sin dar prioridad silenciosa a una clave."""

    candidatos_ids = set()

    if cuil:
        candidatos_ids.update(
            Alumno.objects.filter(cuil=cuil).values_list("pk", flat=True)
        )

    documento_crudo = str(nro_doc or "").strip()
    if tipo_doc and documento_crudo:
        documento = normalizar_documento_bnh(tipo_doc, documento_crudo)
        if documento:
            candidatos_ids.update(
                Alumno.objects.filter(
                    tipo_doc_id=tipo_doc.pk,
                    nro_doc__iexact=documento,
                ).values_list("pk", flat=True)
            )

    if not candidatos_ids:
        return []

    return list(
        Alumno.objects.filter(pk__in=candidatos_ids)
        .select_related("tipo_doc")
        .order_by("pk")
    )


def _tutores_por_identidad(*, cuil=None, tipo_doc=None, nro_doc=None):
    """Reúne coincidencias fuertes del tutor sin priorizar una clave sobre otra."""

    candidatos_ids = set()

    if cuil:
        candidatos_ids.update(
            Tutor.objects.filter(cuil_tutor=cuil).values_list("pk", flat=True)
        )

    documento_crudo = str(nro_doc or "").strip()
    if tipo_doc and documento_crudo:
        documento = normalizar_documento_bnh(
            tipo_doc,
            documento_crudo,
            "Número de documento del tutor",
        )
        if documento:
            candidatos_ids.update(
                Tutor.objects.filter(
                    tipo_doc_id=tipo_doc.pk,
                    nro_doc__iexact=documento,
                ).values_list("pk", flat=True)
            )

    if not candidatos_ids:
        return []

    return list(
        Tutor.objects.filter(pk__in=candidatos_ids)
        .select_related("tipo_doc")
        .order_by("pk")
    )


def _tutores_por_identidad_debil(*, apellidos="", nombres="", fecha_nac=None):
    """Detecta candidatos nominales de tutor sin fusionarlos automáticamente."""

    apellidos = str(apellidos or "").strip()
    nombres = str(nombres or "").strip()
    if not (apellidos and nombres and fecha_nac):
        return []

    return list(
        Tutor.objects.filter(
            apellidos__iexact=apellidos,
            nombres__iexact=nombres,
            fecha_nac=fecha_nac,
        )
        .select_related("tipo_doc")
        .order_by("pk")
    )


def _respuesta_alumno_encontrado(alumno):
    data = {"exists": True, "alumno": _alumno_payload(alumno)}
    data.update(_relaciones_payload(alumno))
    return data


@bnh_alumnos_required
def carga_alumno_view(request):
    """Renderiza la pantalla de carga con todos los catálogos necesarios."""

    raw_next_url = (request.GET.get("next") or "").strip()
    next_url = ""
    if raw_next_url and url_has_allowed_host_and_scheme(
        raw_next_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        next_url = raw_next_url

    # El template recibe catálogos completos porque la pantalla filtra y arma
    # varias relaciones en el navegador antes de enviar el POST final.
    nacionalidades = _catalogo(Nacionalidad)
    prioridad_nacionalidad = {-2: 0, 300: 1}
    nacionalidades.sort(
        key=lambda item: prioridad_nacionalidad.get(item.pk, 2)
    )

    alumno_id_inicial = ""
    raw_alumno_id = (request.GET.get("alumno_id") or "").strip()
    if raw_alumno_id:
        try:
            alumno_id = int(raw_alumno_id)
        except (TypeError, ValueError):
            alumno_id = None
        if alumno_id and Alumno.objects.filter(pk=alumno_id).exists():
            alumno_id_inicial = str(alumno_id)

    context = {
        "alumno_id_inicial": alumno_id_inicial,
        "tipo_doc_inicial": (request.GET.get("tipo_doc") or "").strip(),
        "nro_doc_inicial": (request.GET.get("nro_doc") or "").strip().upper(),
        "cuil_inicial": _solo_digitos(request.GET.get("cuil")),
        "apellidos_inicial": (request.GET.get("apellidos") or "").strip(),
        "nombres_inicial": (request.GET.get("nombres") or "").strip(),
        "fecha_nacimiento_inicial": (request.GET.get("fecha_nacimiento") or "").strip(),
        "sexo_inicial": (request.GET.get("sexo") or "").strip(),
        "next_url": next_url,
        "return_label": request.GET.get("return_label") or "Volver",
        "tipos_documento": _catalogo(DocumentoTipo),
        "provincias": _catalogo(Provincias),
        "localidades": _catalogo(Localidades),
        "nacionalidades": nacionalidades,
        "paises": _catalogo(Pais),
        "sexos": _catalogo(Sexo),
        "parentescos": _catalogo(RelacionParentesco),
        "beneficios": _catalogo(TipoPlanesSociales),
        "niveles_formacion": _catalogo(NivelFormacion),
        "tipos_obra_social": _catalogo(TipoObraSocial),
        "catalogo_obras_sociales": _catalogo(CatalogoObraSocial),
        "catalogo_sino_tipo": _catalogo(CatalogoSinoTipo),
        "estados_civiles": _catalogo(EstadosCiviles),
        "comunidades_originarias": _catalogo(TipoComunidadOriginaria),
        "lenguas_originarias": _catalogo(TipoLenguaOriginaria),
        "tipos_discapacidad": _catalogo(TipoDiscapacidad),
        "codigos_area": _catalogo(CodAreasTelefonos),
    }
    return render(request, "bnhalumnos/carga_alumno.html", context)


@bnh_alumnos_required
@require_GET
def buscar_alumno_por_cuil(request):
    """Busca alumnos únicamente por identificadores fuertes.

    Para resolver identidad se acepta CUIL y/o tipo + número de documento.
    Los datos nominales nunca se usan para localizar, seleccionar o fusionar
    automáticamente una persona.
    """

    try:
        alumno_id_raw = (request.GET.get("alumno_id") or "").strip()
        if alumno_id_raw:
            try:
                alumno_id = int(alumno_id_raw)
            except (TypeError, ValueError):
                return JsonResponse(
                    {"exists": False, "valid": False, "error": "El alumno seleccionado no es válido."},
                    status=400,
                )
            alumno = (
                Alumno.objects.filter(pk=alumno_id)
                .select_related("tipo_doc")
                .first()
            )
            if not alumno:
                return JsonResponse(
                    {"exists": False, "valid": False, "error": "El alumno seleccionado ya no existe."},
                    status=404,
                )
            return JsonResponse(_respuesta_alumno_encontrado(alumno))

        cuil = _validar_cuil_para_ui(
            request.GET.get("cuil"),
            "CUIL del alumno",
            requerido=False,
        )
        tipo_doc = _tipo_documento_busqueda(request.GET.get("tipo_doc"))
        nro_doc = request.GET.get("nro_doc")
        documento_informado = bool(tipo_doc and str(nro_doc or "").strip())

        if cuil and tipo_doc:
            documento_normalizado = (
                normalizar_documento_bnh(tipo_doc, nro_doc)
                if documento_informado
                else None
            )
            validar_cuil_con_documento(
                cuil,
                tipo_doc,
                documento_normalizado,
                "CUIL del alumno",
            )

        # Sin CUIL ni tipo+documento no existe una clave segura de identidad.
        # En particular, No posee / En trámite sin número no se buscan por
        # nombre, apellido, fecha de nacimiento ni sexo.
        if not cuil and not documento_informado:
            return JsonResponse(
                {
                    "exists": False,
                    "valid": True,
                    "search_skipped": True,
                    "cuil": "",
                    "message": (
                        "No se realizó una búsqueda de identidad porque no hay "
                        "CUIL ni tipo y número de documento informados."
                    ),
                }
            )

        candidatos = _alumnos_por_identidad(
            cuil=cuil,
            tipo_doc=tipo_doc if documento_informado else None,
            nro_doc=nro_doc if documento_informado else None,
        )

        if not candidatos:
            persona_sge = _resolver_persona_sge(
                cuil=cuil,
                tipo_doc=tipo_doc if documento_informado else None,
                nro_doc=nro_doc if documento_informado else None,
            )
            if persona_sge:
                # Si SGE reconoce la persona por identificadores actuales pero BNH
                # conserva un documento/CUIL anterior, el vínculo técnico estable
                # permite reencontrar el mismo Alumno y evita proponer un alta nueva.
                id_persona_sge = int(persona_sge["id_persona_sge"])
                alumno_vinculado = (
                    Alumno.objects.filter(id_persona_sge=id_persona_sge)
                    .select_related("tipo_doc")
                    .first()
                )
                if alumno_vinculado:
                    data = _respuesta_alumno_encontrado(alumno_vinculado)
                    data["weak_match"] = False
                    data["matched_by_sge_link"] = True
                    # El frontend necesita únicamente la identidad SGE ya validada
                    # para evitar mezclar documento/CUIL nuevos con valores locales
                    # anteriores al reencontrar la misma persona por id_persona_sge.
                    data["alumno_sge"] = persona_sge
                    return JsonResponse(data)

                return JsonResponse({
                    "exists": False,
                    "valid": True,
                    "sge_found": True,
                    "cuil": cuil or "",
                    "alumno_sge": persona_sge,
                })
            return JsonResponse({
                "exists": False,
                "valid": True,
                "sge_found": False,
                "cuil": cuil or "",
            })

        if len(candidatos) > 1:
            return JsonResponse(
                {
                    "exists": False,
                    "valid": False,
                    "ambiguous": True,
                    "weak_match": False,
                    "error": (
                        "El CUIL y el tipo + número de documento apuntan a "
                        "personas distintas. Revise los datos antes de continuar."
                    ),
                },
                status=409,
            )

        data = _respuesta_alumno_encontrado(candidatos[0])
        data["weak_match"] = False
        return JsonResponse(data)
    except SGEConsultaNoDisponible as exc:
        return JsonResponse(
            {"exists": False, "valid": False, "sge_unavailable": True, "error": str(exc)},
            status=503,
        )
    except ValidationError as exc:
        return JsonResponse(
            {"exists": False, "valid": False, "error": _error_json(exc)},
            status=400,
        )
    except Exception as exc:
        return JsonResponse(
            {"exists": False, "valid": False, "error": str(exc)},
            status=500,
        )


@bnh_alumnos_required
@require_GET
def buscar_tutor_por_cuil(request):
    """Busca tutor por CUIL o tipo+documento sin asumir que el CUIL existe."""

    try:
        cuil = _validar_cuil_para_ui(
            request.GET.get("cuil"),
            "CUIL del tutor",
            requerido=False,
        )
        tipo_doc = _tipo_documento_busqueda(request.GET.get("tipo_doc"))
        nro_doc = request.GET.get("nro_doc")
        apellidos = request.GET.get("apellidos")
        nombres = request.GET.get("nombres")
        fecha_nac = request.GET.get("fecha_nac") or None

        if cuil and tipo_doc:
            documento_normalizado = (
                normalizar_documento_bnh(
                    tipo_doc,
                    nro_doc,
                    "Número de documento del tutor",
                )
                if str(nro_doc or "").strip()
                else None
            )
            validar_cuil_con_documento(
                cuil,
                tipo_doc,
                documento_normalizado,
                "CUIL del tutor",
            )

        if not cuil and not tipo_doc:
            raise ValidationError(
                "Ingrese un CUIL o seleccione tipo de documento para buscar al tutor."
            )

        candidatos = _tutores_por_identidad(
            cuil=cuil,
            tipo_doc=tipo_doc,
            nro_doc=nro_doc,
        )
        coincidencia_debil = False

        if not candidatos:
            candidatos = _tutores_por_identidad_debil(
                apellidos=apellidos,
                nombres=nombres,
                fecha_nac=fecha_nac,
            )
            coincidencia_debil = bool(candidatos)

        if not candidatos:
            return JsonResponse({"exists": False, "valid": True, "cuil": cuil or ""})
        if len(candidatos) > 1:
            return JsonResponse(
                {
                    "exists": False,
                    "valid": False,
                    "ambiguous": True,
                    "weak_match": coincidencia_debil,
                    "error": (
                        "Se encontraron varios tutores posibles con esos datos. "
                        "No se seleccionó ninguno automáticamente."
                    ),
                    "candidates": [_tutor_payload(item) for item in candidatos],
                },
                status=409,
            )
        return JsonResponse({
            "exists": True,
            "weak_match": coincidencia_debil,
            "tutor": _tutor_payload(candidatos[0]),
        })
    except ValidationError as exc:
        return JsonResponse(
            {"exists": False, "valid": False, "error": _error_json(exc)},
            status=400,
        )
    except Exception as exc:
        return JsonResponse(
            {"exists": False, "valid": False, "error": str(exc)},
            status=500,
        )


def _guardar_form(form, prefijo=None):
    """Valida y guarda un ModelForm, con prefijo para errores de listas."""

    if form.is_valid():
        # form.save() no esta definido en este archivo: lo aporta Django ModelForm.
        # Como cada Form tiene Meta.model, Django sabe que tabla/modelo guardar.
        return form.save()

    errores = form_errors_to_json(form)
    if prefijo:
        errores = {f"{prefijo}.{campo}": mensajes for campo, mensajes in errores.items()}
    raise ValidationError(errores)


def _guardar_alumno_form(alumno, data, usuario=None):
    """Guarda el alumno delegando limpieza y validacion en AlumnoForm."""

    data = dict(data)
    data.pop("id", None)
    if data.get("pueblo_indigena") and not data.get("comunidad_originaria"):
        data["comunidad_originaria"] = data.get("pueblo_indigena")
    data.pop("pueblo_indigena", None)
    data.pop("discapacidad", None)

    if str(data.get("pertenece_pueblo_indigena") or "") != str(CatalogoSinoTipo.SI):
        data["comunidad_originaria"] = ""
    if not data.get("telefono") or not data.get("codigo_area"):
        data["whatsapp"] = False
        data["es_celular"] = False
    elif not data.get("es_celular"):
        data["whatsapp"] = False

    if usuario and getattr(usuario, "is_authenticated", False):
        alumno.usuario_modificacion = usuario
        alumno.cuil_usuario_modificacion = _solo_digitos(getattr(usuario, "username", ""))

    # instance=alumno decide si el form actualiza un Alumno existente o crea uno nuevo.
    # validar_y_guardar() termina llamando a form.save(), que usa models.Alumno y el ORM de Django.
    return validar_y_guardar(AlumnoForm(data, instance=alumno))


def _guardar_tutor_form(tutor, data, prefijo=None):
    """Guarda el tutor delegando limpieza y validacion en TutorForm."""

    data = dict(data)
    data.pop("id", None)
    if not data.get("es_celular"):
        data["whatsapp"] = False

    # Igual que AlumnoForm: TutorForm es un ModelForm conectado a models.Tutor.
    return _guardar_form(TutorForm(data, instance=tutor), prefijo)


def _guardar_obras_sociales(alumno, items):
    """Reemplaza obras sociales del alumno por la lista vigente del payload."""

    # Las relaciones se reemplazan completas: el frontend envia la lista vigente.
    # Al asignar id_alumno=alumno.pk, cada registro queda asociado al alumno guardado.
    alumno.obras_sociales.all().delete()
    campos = ["tipo_obra", "nombre_obra", "fecha_inicio", "fecha_fin", "descripcion"]
    for indice, item in enumerate(items):
        if not payload_tiene_datos(item, campos):
            continue
        data = dict(item)
        data["id_alumno"] = alumno.pk
        _guardar_form(ObraSocialForm(data), f"obras_sociales[{indice}]")


def _guardar_discapacidades(alumno, items):
    """Reemplaza detalles de discapacidad respetando el indicador principal."""

    # Misma mecanica: borrar relaciones previas y guardar las actuales con ModelForm.
    alumno.discapacidades.all().delete()
    if alumno.tiene_discapacidad_id != CatalogoSinoTipo.SI:
        return

    campos = ["id_discapacidad", "fecha_inicio", "fecha_fin", "porcentaje", "certificado_cud", "observaciones"]
    for indice, item in enumerate(items):
        if not payload_tiene_datos(item, campos):
            continue
        data = dict(item)
        data["id_alumno"] = alumno.pk
        _guardar_form(DiscapacidadForm(data), f"discapacidades[{indice}]")


def _guardar_planes_sociales(alumno, items):
    """Reemplaza planes sociales del alumno por los enviados desde el frontend."""

    # PlanesSocialesForm tiene Meta.model = PlanesSociales; _guardar_form() valida y hace save().
    alumno.planes_sociales.all().delete()
    campos = ["id_beneficio", "descripcion", "fecha_desde", "fecha_hasta", "monto", "observaciones"]
    for indice, item in enumerate(items):
        if not payload_tiene_datos(item, campos):
            continue
        data = dict(item)
        data["id_alumno"] = alumno.pk
        _guardar_form(PlanesSocialesForm(data), f"planes_sociales[{indice}]")


def _guardar_tutores_parentales(alumno, items):
    """Guarda tutores y recrea las relaciones Parental del alumno."""

    # Guarda dos cosas por cada tutor recibido:
    # 1) Tutor: persona adulta, buscada por CUIL/DNI o creada si no existe.
    # 2) Parental: relacion entre ese tutor y el alumno.
    alumno.parentales.all().delete()
    campos = [
        "cuil_tutor",
        "apellidos",
        "nombres",
        "tipo_doc",
        "nro_doc",
        "parentesco",
    ]
    for indice, item in enumerate(items):
        if not payload_tiene_datos(item, campos):
            continue

        tutor_id = item.get("id")
        tutor = None
        if tutor_id:
            try:
                tutor_id = int(tutor_id)
            except (TypeError, ValueError):
                raise ValidationError({
                    f"tutores[{indice}].id": ["El tutor seleccionado no es válido."]
                })
            tutor = Tutor.objects.filter(pk=tutor_id).first()
            if not tutor:
                raise ValidationError({
                    f"tutores[{indice}].id": ["El tutor seleccionado ya no existe."]
                })
        else:
            cuil_tutor = _validar_cuil_para_ui(
                item.get("cuil_tutor"),
                "CUIL del tutor",
                requerido=False,
            )
            tipo_doc = _tipo_documento_busqueda(item.get("tipo_doc"))
            candidatos_ids = set()

            if cuil_tutor:
                candidatos_ids.update(
                    Tutor.objects.filter(cuil_tutor=cuil_tutor).values_list("pk", flat=True)
                )

            if tipo_doc:
                try:
                    nro_doc = normalizar_documento_bnh(
                        tipo_doc,
                        item.get("nro_doc"),
                        "Número de documento del tutor",
                    )
                except ValidationError as exc:
                    raise ValidationError({
                        f"tutores[{indice}].nro_doc": exc.messages
                    })
                if nro_doc:
                    candidatos_ids.update(
                        Tutor.objects.filter(
                            tipo_doc_id=tipo_doc.pk,
                            nro_doc__iexact=nro_doc,
                        ).values_list("pk", flat=True)
                    )
                # Sin CUIL ni número de documento no se fusiona un tutor por
                # nombre/fecha: podría tratarse de otra persona homónima.

            if len(candidatos_ids) > 1:
                raise ValidationError({
                    f"tutores[{indice}].nro_doc": [
                        "Los datos coinciden con más de un tutor. No se actualizó ninguno automáticamente."
                    ]
                })
            if candidatos_ids:
                tutor = Tutor.objects.filter(pk=next(iter(candidatos_ids))).first()
            if tutor is None:
                tutor = Tutor()

        tutor = _guardar_tutor_form(tutor, item, f"tutores[{indice}]")
        parental_data = dict(item)
        parental_data.pop("id", None)
        parental_data["id_alumno"] = alumno.pk
        parental_data["id_tutor"] = tutor.pk
        parental_data["observaciones"] = item.get("parental_observaciones", "")
        # ParentalForm guarda la fila intermedia que une alumno + tutor + parentesco.
        _guardar_form(ParentalForm(parental_data), f"tutores[{indice}].parental")


@bnh_alumnos_required
@require_POST
def guardar_carga_alumno(request):
    """Guarda alumno y relaciones en una operación atómica desde el formulario."""

    try:
        # El frontend no manda un form HTML tradicional: manda JSON con fetch().
        # request.body trae ese JSON crudo y json.loads() lo convierte en diccionario Python.
        payload = json.loads(request.body.decode("utf-8"))
        alumno_data = dict(payload.get("alumno") or {})
        alumno_id = alumno_data.get("id")
        es_alta_nueva = not bool(alumno_id)

        # Toda la carga se confirma o se revierte junta para evitar alumnos
        # guardados sin sus relaciones o relaciones sin alumno. Si cualquier
        # ModelForm o save() lanza ValidationError, transaction.atomic() revierte
        # las escrituras realizadas dentro del bloque.
        with transaction.atomic():
            alumno = None

            if alumno_id:
                try:
                    alumno_id = int(alumno_id)
                except (TypeError, ValueError):
                    raise ValidationError({"id": "El alumno seleccionado no es válido."})
                alumno = (
                    Alumno.objects.select_for_update()
                    .filter(pk=alumno_id)
                    .first()
                )
                if not alumno:
                    raise ValidationError({
                        "id": "El alumno seleccionado ya no existe. Vuelva a buscarlo."
                    })
            else:
                # Una alta nueva no reutiliza personas silenciosamente. Se
                # detectan coincidencias fuertes y, si existen, se exige abrir
                # el registro existente para evitar fusiones incorrectas.
                cuil_alumno = _validar_cuil_para_ui(
                    alumno_data.get("cuil"),
                    "CUIL del alumno",
                    requerido=False,
                )
                tipo_doc = _tipo_documento_busqueda(alumno_data.get("tipo_doc"))
                candidatos_ids = set()

                if cuil_alumno:
                    candidatos_ids.update(
                        Alumno.objects.filter(cuil=cuil_alumno).values_list("pk", flat=True)
                    )

                nro_doc = None
                if tipo_doc:
                    try:
                        nro_doc = normalizar_documento_bnh(
                            tipo_doc,
                            alumno_data.get("nro_doc"),
                        )
                    except ValidationError as exc:
                        raise ValidationError({"nro_doc": exc.messages})

                    if nro_doc:
                        candidatos_ids.update(
                            Alumno.objects.filter(
                                tipo_doc_id=tipo_doc.pk,
                                nro_doc__iexact=nro_doc,
                            ).values_list("pk", flat=True)
                        )
                    # Sin CUIL ni número de documento no hay una clave fuerte.
                    # Los datos nominales no se usan para resolver identidad ni
                    # para fusionar registros automáticamente.

                if len(candidatos_ids) > 1:
                    raise ValidationError({
                        "__all__": (
                            "Los datos ingresados coinciden con más de un alumno. "
                            "No se modificó ninguno automáticamente; revise los duplicados."
                        )
                    })
                if candidatos_ids:
                    raise ValidationError({
                        "__all__": (
                            "Ya existe un alumno con esta identidad. "
                            "Búsquelo y abra ese registro antes de guardar para evitar duplicados."
                        )
                    })

                alumno = Alumno()

            # El vínculo SGE se resuelve siempre por identificadores fuertes y
            # queda separado del identificador jurisdiccional BNH. Si SGE no
            # puede consultarse, no se interpreta el fallo como "persona ausente".
            cuil_sge = _validar_cuil_para_ui(
                alumno_data.get("cuil"),
                "CUIL del alumno",
                requerido=False,
            )
            tipo_doc_sge = _tipo_documento_busqueda(alumno_data.get("tipo_doc"))
            nro_doc_sge = alumno_data.get("nro_doc")
            documento_sge_informado = bool(
                tipo_doc_sge and str(nro_doc_sge or "").strip()
            )
            if cuil_sge or documento_sge_informado:
                try:
                    persona_sge = _resolver_persona_sge(
                        cuil=cuil_sge,
                        tipo_doc=tipo_doc_sge if documento_sge_informado else None,
                        nro_doc=nro_doc_sge if documento_sge_informado else None,
                    )
                except SGEConsultaNoDisponible as exc:
                    if es_alta_nueva:
                        raise ValidationError({"__all__": str(exc)})
                    persona_sge = None

                if persona_sge:
                    id_persona_sge = int(persona_sge["id_persona_sge"])
                    if (
                        alumno.id_persona_sge is not None
                        and alumno.id_persona_sge != id_persona_sge
                    ):
                        raise ValidationError({
                            "__all__": (
                                "La identidad ingresada corresponde a otra persona en SGE. "
                                "No se cambió el vínculo existente."
                            )
                        })

                    # Segunda defensa: si la misma persona SGE ya está vinculada a
                    # otro Alumno BNH, nunca se crea ni fusiona un registro nuevo.
                    alumno_vinculado = (
                        Alumno.objects.select_for_update()
                        .filter(id_persona_sge=id_persona_sge)
                        .exclude(pk=alumno.pk)
                        .first()
                    )
                    if alumno_vinculado:
                        raise ValidationError({
                            "__all__": (
                                "Esta persona de SGE ya está vinculada a un alumno BNH existente. "
                                "Búsquelo y abra ese registro antes de guardar."
                            )
                        })

                    alumno.id_persona_sge = id_persona_sge

            # Punto exacto donde se guarda/actualiza el alumno:
            # _guardar_alumno_form -> AlumnoForm -> validar_y_guardar -> form.save() -> models.Alumno -> BD.
            alumno = _guardar_alumno_form(alumno, alumno_data, request.user)

            # El frontend envia la coleccion completa vigente: se reemplazan
            # relaciones hijas dentro de la misma transaccion atomica. En la BD
            # se persiste el JSON ya desarmado en tablas relacionales.
            _guardar_obras_sociales(alumno, payload.get("obras_sociales") or [])
            _guardar_discapacidades(alumno, payload.get("discapacidades") or [])
            _guardar_planes_sociales(alumno, payload.get("planes_sociales") or [])
            _guardar_tutores_parentales(alumno, payload.get("tutores") or [])

            # Los menores de 18 años deben quedar vinculados al menos a un tutor
            # o responsable. Desde los 18 años cumplidos la relación es opcional.
            if _es_menor_de_18(alumno.fecha_nacimiento) and not alumno.parentales.exists():
                raise ValidationError({
                    "tutores": (
                        "El alumno es menor de 18 años. Debe cargar al menos un tutor o responsable."
                    )
                })

        respuesta = {
            "ok": True,
            "alumno_id": alumno.id,
            "alumno": _alumno_payload(alumno),
            "message": "Carga guardada correctamente.",
        }
        respuesta.update(_relaciones_payload(alumno))
        return JsonResponse(respuesta)
    except ValidationError as exc:
        return JsonResponse({"ok": False, "error": _error_json(exc)}, status=400)
    except Exception as exc:
        return JsonResponse({"ok": False, "error": str(exc)}, status=500)
