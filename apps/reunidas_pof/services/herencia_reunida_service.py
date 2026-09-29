from copy import deepcopy

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Prefetch
from django.utils import timezone

from ..models import (
    CargoPof,
    LocalizacionPof,
    LoteCargaPof,
    ProyectosEspecialesPof,
    ReunidaPof,
    SnapshotPadronLocalizacionPof,
    _decimal_dos_decimales,
)
from .zona_educativa_service import (
    asignaciones_zona_equivalentes,
    bloquear_identidad_zona,
    construir_identidad_zona,
    obtener_asignacion_snapshot,
    obtener_asignacion_vigente_identidad,
)


def _resumen_herencia(reunida_base_id=None, heredada=False):
    """
    Construye la respuesta interna homogénea de una herencia de Reunida.

    - Distingue una Reunida sin base de una clonación completada.
    - Expone solo cantidades creadas para trazabilidad del flujo administrativo.
    - No se utiliza como contrato de interfaz ni modifica datos.
    """
    return {
        "heredada": heredada,
        "reunida_base_id": reunida_base_id,
        "localizaciones_creadas": 0,
        "snapshots_creados": 0,
        "lotes_creados": 0,
        "cargos_creados": 0,
    }


def _usuario_herencia(usuario):
    """
    Devuelve el usuario persistible que originó la herencia, si está disponible.

    - Conserva el usuario autenticado recibido desde la vista administrativa.
    - Evita asignar instancias anónimas a claves foráneas de usuario.
    - No consulta ni modifica los usuarios de la Reunida origen.
    """
    if usuario and getattr(usuario, "is_authenticated", False):
        return usuario
    return None


def _identificador_localizacion(localizacion):
    """
    Genera una referencia segura para informar errores de snapshot faltante.

    - Prioriza CUEANEXO y CUOF, que identifican funcionalmente la localización.
    - Incluye el ID solo como ayuda de diagnóstico técnico.
    - No expone datos ajenos a la operación de herencia.
    """
    return (
        f"CUEANEXO {localizacion.cueanexo or 'sin CUEANEXO'} / "
        f"CUOF {localizacion.cuof or 'sin CUOF'} (ID {localizacion.pk})"
    )


def _destino_tiene_datos(reunida_destino):
    """
    Detecta datos funcionales previos que impedirían una herencia inicial segura.

    - Revisa localizaciones, snapshots, lotes y cargos del destino.
    - Evita mezclar o sobrescribir información preexistente.
    - Sirve como protección contra una segunda invocación con datos creados.
    """
    return (
        LocalizacionPof.objects.filter(reunida=reunida_destino).exists()
        or LoteCargaPof.objects.filter(reunida=reunida_destino).exists()
        or SnapshotPadronLocalizacionPof.objects.filter(
            localizacion__reunida=reunida_destino
        ).exists()
        or CargoPof.objects.filter(localizacion__reunida=reunida_destino).exists()
    )


def _validar_base(reunida_destino, reunida_base):
    """
    Verifica que la relación de base cumpla las reglas temporales de Reunidas.

    - Exige el mismo nivel educativo o área.
    - Exige exactamente el año inmediatamente anterior.
    - No corrige ni reasigna la base desde el servicio de herencia.
    """
    if reunida_base.nivel != reunida_destino.nivel:
        raise ValidationError("La POF base no corresponde al mismo nivel.")

    if reunida_base.anio != reunida_destino.anio - 1:
        raise ValidationError("La POF base debe ser exactamente del año anterior.")


def _cargar_localizaciones_origen(reunida_base):
    """
    Lee el estado heredable de la Reunida base sin consultas por cargo.

    - Carga todas las localizaciones de la Reunida base.
    - Prefetch solo snapshots vigentes y todos los cargos con su lote técnico.
    - Excluye movimientos, lotes históricos y snapshots no vigentes.
    """
    return list(
        LocalizacionPof.objects.filter(reunida=reunida_base).prefetch_related(
            Prefetch(
                "snapshots_padron",
                queryset=SnapshotPadronLocalizacionPof.objects.filter(vigente=True),
                to_attr="snapshots_vigentes_herencia",
            ),
            Prefetch(
                "cargos",
                queryset=CargoPof.objects.select_related("lote_carga"),
                to_attr="cargos_herencia",
            ),
        )
    )


def _validar_origen(reunida_base, localizaciones_origen):
    """
    Comprueba toda la fuente antes de crear registros destino.

    - Exige una localización exclusiva de la Reunida y un snapshot vigente único.
    - Revisa coherencia de lote, estados, cantidades, unidad, puntos y total de cargos.
    - Evita escrituras parciales ante inconsistencias previsibles del origen.
    """
    estados_validos = set(CargoPof.EstadoPof.values)
    unidades_validas = set(CargoPof.UnidadCantidad.values)

    for localizacion in localizaciones_origen:
        if localizacion.proyecto_especial_id:
            raise ValidationError(
                "La localización origen no puede pertenecer a un Proyecto Especial."
            )

        snapshots_vigentes = localizacion.snapshots_vigentes_herencia
        if len(snapshots_vigentes) != 1:
            raise ValidationError(
                f"La localización {_identificador_localizacion(localizacion)} "
                "no posee snapshot vigente."
            )

        for cargo in localizacion.cargos_herencia:
            if cargo.lote_carga.localizacion_id != localizacion.id:
                raise ValidationError("Un cargo origen no corresponde a su localización.")
            if cargo.lote_carga.reunida_id != reunida_base.id:
                raise ValidationError("El lote de un cargo origen no corresponde a la POF base.")
            if cargo.estado_pof not in estados_validos:
                raise ValidationError("El estado de un cargo origen no es válido.")
            if cargo.unidad_cantidad not in unidades_validas:
                raise ValidationError("La unidad de cantidad de un cargo origen no es válida.")
            if cargo.cantidad < 0:
                raise ValidationError("La cantidad de un cargo origen debe ser mayor o igual a cero.")
            if cargo.puntos_asignados < 0:
                raise ValidationError("Los puntos de un cargo origen no pueden ser negativos.")
            if cargo.total != _decimal_dos_decimales(
                cargo.cantidad * cargo.puntos_asignados
            ):
                raise ValidationError("El total de un cargo origen no es consistente.")


def _preparar_asignaciones_zona_herencia(localizaciones_origen, anio_destino):
    """
    Resuelve la Zona que heredará cada localización en el nuevo ciclo.

    - Bloquea todas las identidades destino en orden estable para evitar carreras.
    - Si el destino ya tiene Zona para la identidad, esa asignación prevalece.
    - Una Zona heredada distinta a la ya vigente en destino bloquea la herencia.
    - Si el destino aún no tiene Zona, una única asignación origen se propaga a
      todas las localizaciones del mismo grupo, incluso si alguna estaba vacía.
    - Nunca consulta el catálogo: la herencia copia estado histórico congelado.
    """
    grupos = {}

    for localizacion in localizaciones_origen:
        identidad = construir_identidad_zona(
            anio=anio_destino,
            cueanexo=localizacion.cueanexo,
            cuof=localizacion.cuof,
        )
        clave_grupo = (
            identidad["anio"],
            identidad["tipo_clave"],
            identidad["clave"],
        )
        snapshot_origen = localizacion.snapshots_vigentes_herencia[0]
        grupos.setdefault(
            clave_grupo,
            {
                "identidad": identidad,
                "items": [],
            },
        )["items"].append(
            {
                "localizacion": localizacion,
                "asignacion_origen": obtener_asignacion_snapshot(snapshot_origen),
            }
        )

    grupos_ordenados = [
        grupos[clave]
        for clave in sorted(grupos)
    ]

    for grupo in grupos_ordenados:
        bloquear_identidad_zona(grupo["identidad"])

    resultado = {}

    for grupo in grupos_ordenados:
        vigente_destino = obtener_asignacion_vigente_identidad(
            grupo["identidad"]
        )
        asignacion_destino = None
        if vigente_destino["asignada"]:
            asignacion_destino = {
                "tipo": vigente_destino["tipo"],
                "zona": vigente_destino["zona"],
                "puntos": vigente_destino["puntos"],
            }

        asignaciones_origen = []
        for item in grupo["items"]:
            asignacion = item["asignacion_origen"]
            if asignacion is None:
                continue
            if not any(
                asignaciones_zona_equivalentes(asignacion, existente)
                for existente in asignaciones_origen
            ):
                asignaciones_origen.append(asignacion)

        if asignacion_destino is not None:
            for asignacion_origen in asignaciones_origen:
                if not asignaciones_zona_equivalentes(
                    asignacion_origen,
                    asignacion_destino,
                ):
                    raise ValidationError(
                        "La Zona Educativa heredada entra en conflicto con la "
                        "Zona ya vigente para esa identidad en el año destino."
                    )
            asignacion_efectiva = asignacion_destino
        else:
            if len(asignaciones_origen) > 1:
                raise ValidationError(
                    "El origen contiene Zonas Educativas contradictorias para "
                    "una misma identidad que se heredaría al nuevo ciclo."
                )
            asignacion_efectiva = (
                asignaciones_origen[0]
                if asignaciones_origen
                else None
            )

        for item in grupo["items"]:
            resultado[item["localizacion"].id] = asignacion_efectiva

    return resultado


def _crear_snapshot_destino(
    localizacion_destino,
    snapshot_origen,
    usuario,
    momento,
    asignacion_zona=None,
):
    """
    Crea el nuevo snapshot inicial desde la única foto vigente de origen.

    - Conserva los datos funcionales del padrón y copia JSON de forma independiente.
    - Copia Zona/Puntos congelados o usa la asignación ya vigente del ciclo destino.
    - Establece tipo INICIAL, vigencia y fechas propias del destino.
    - No reutiliza el usuario, fecha ni identidad del snapshot histórico.
    """
    asignacion_efectiva = (
        asignacion_zona
        if asignacion_zona is not None
        else obtener_asignacion_snapshot(snapshot_origen)
    )

    return SnapshotPadronLocalizacionPof.objects.create(
        localizacion=localizacion_destino,
        tipo_snapshot=SnapshotPadronLocalizacionPof.TipoSnapshot.INICIAL,
        origen_datos=snapshot_origen.origen_datos,
        vigente=True,
        estado_padron=snapshot_origen.estado_padron,
        estado_localizacion_padron=snapshot_origen.estado_localizacion_padron,
        estado_oferta_padron=snapshot_origen.estado_oferta_padron,
        estado_establecimiento_padron=snapshot_origen.estado_establecimiento_padron,
        oferta=snapshot_origen.oferta,
        acronimo=snapshot_origen.acronimo,
        nombre_establecimiento=snapshot_origen.nombre_establecimiento,
        numero_establecimiento=snapshot_origen.numero_establecimiento,
        region=snapshot_origen.region,
        localidad=snapshot_origen.localidad,
        departamento=snapshot_origen.departamento,
        ambito=snapshot_origen.ambito,
        categoria=snapshot_origen.categoria,
        jornada=snapshot_origen.jornada,
        ubicacion=snapshot_origen.ubicacion,
        ubicacion_localidad_departamento=snapshot_origen.ubicacion_localidad_departamento,
        zona_educativa_tipo=(
            asignacion_efectiva["tipo"]
            if asignacion_efectiva
            else ""
        ),
        zona_educativa=(
            asignacion_efectiva["zona"]
            if asignacion_efectiva
            else ""
        ),
        puntos_zona_educativa=(
            asignacion_efectiva["puntos"]
            if asignacion_efectiva
            else None
        ),
        datos_padron=deepcopy(snapshot_origen.datos_padron),
        usuario=usuario,
        fecha_snapshot=momento,
    )


def _copiar_localizaciones_destino(
    localizaciones_origen,
    resumen,
    usuario_destino,
    momento,
    *,
    reunida_destino=None,
    proyecto_destino=None,
    asignaciones_zona_por_localizacion=None,
):
    """
    Copia el estado funcional vigente de una cabecera POF a otra nueva.

    - Crea identidades, snapshot vigente y lote AFECTADO propios del destino.
    - Conserva todos los datos funcionales del cargo, incluidas sus ofertas.
    - Aplica la Zona/Puntos resuelta para el ciclo destino sin consultar catálogo.
    - No copia IDs, fechas ni historial administrativo de la cabecera base.
    """
    asignaciones_zona_por_localizacion = (
        asignaciones_zona_por_localizacion or {}
    )

    for localizacion_origen in localizaciones_origen:
        localizacion_destino = LocalizacionPof.objects.create(
            reunida=reunida_destino,
            proyecto_especial=proyecto_destino,
            cueanexo=localizacion_origen.cueanexo,
            cuof=localizacion_origen.cuof,
            cui=localizacion_origen.cui,
        )
        resumen["localizaciones_creadas"] += 1

        _crear_snapshot_destino(
            localizacion_destino,
            localizacion_origen.snapshots_vigentes_herencia[0],
            usuario_destino,
            momento,
            asignacion_zona=asignaciones_zona_por_localizacion.get(
                localizacion_origen.id
            ),
        )
        resumen["snapshots_creados"] += 1

        lote_destino = LoteCargaPof.objects.create(
            reunida=reunida_destino,
            proyecto_especial=proyecto_destino,
            localizacion=localizacion_destino,
            tipo_operacion=LoteCargaPof.TipoOperacion.AFECTADO,
            usuario=usuario_destino,
            fecha=momento,
        )
        resumen["lotes_creados"] += 1

        for cargo_origen in localizacion_origen.cargos_herencia:
            CargoPof.objects.create(
                localizacion=localizacion_destino,
                lote_carga=lote_destino,
                ceic=cargo_origen.ceic,
                cargo=cargo_origen.cargo,
                oferta=cargo_origen.oferta,
                ofertas_seleccionadas=deepcopy(
                    cargo_origen.ofertas_seleccionadas
                ),
                observacion=cargo_origen.observacion,
                cantidad=cargo_origen.cantidad,
                unidad_cantidad=cargo_origen.unidad_cantidad,
                puntos_asignados=cargo_origen.puntos_asignados,
                estado_pof=cargo_origen.estado_pof,
                snapshot_ceic=deepcopy(cargo_origen.snapshot_ceic),
            )
            resumen["cargos_creados"] += 1

    return resumen


@transaction.atomic
def heredar_estado_inicial_reunida(reunida_destino, usuario=None):
    """
    Clona de forma atómica el estado inicial de la base de una Reunida nueva.

    - Retorna sin cambios cuando no existe reunida_base_anterior.
    - Crea IDs propios para localizaciones, snapshot vigente, lote AFECTADO y todos los cargos.
    - Mantiene la fuente estrictamente en modo lectura y rechaza destinos ya poblados.
    """
    if not reunida_destino or not reunida_destino.pk:
        raise ValidationError("La POF destino debe estar persistida antes de heredar.")

    reunida_destino = ReunidaPof.objects.select_for_update().get(pk=reunida_destino.pk)
    resumen = _resumen_herencia(reunida_destino.reunida_base_anterior_id)

    if not reunida_destino.reunida_base_anterior_id:
        return resumen

    if _destino_tiene_datos(reunida_destino):
        raise ValidationError(
            "La POF destino ya contiene datos y no puede recibir una herencia inicial automática."
        )

    reunida_base = ReunidaPof.objects.get(
        pk=reunida_destino.reunida_base_anterior_id
    )
    _validar_base(reunida_destino, reunida_base)
    localizaciones_origen = _cargar_localizaciones_origen(reunida_base)
    _validar_origen(reunida_base, localizaciones_origen)

    asignaciones_zona = _preparar_asignaciones_zona_herencia(
        localizaciones_origen,
        reunida_destino.anio,
    )

    usuario_destino = _usuario_herencia(usuario)
    momento = timezone.now()
    resumen["heredada"] = True

    return _copiar_localizaciones_destino(
        localizaciones_origen,
        resumen,
        usuario_destino,
        momento,
        reunida_destino=reunida_destino,
        asignaciones_zona_por_localizacion=asignaciones_zona,
    )


def _resumen_herencia_proyecto(proyecto_base_id=None, heredada=False):
    return {
        "heredada": heredada,
        "proyecto_base_id": proyecto_base_id,
        "localizaciones_creadas": 0,
        "snapshots_creados": 0,
        "lotes_creados": 0,
        "cargos_creados": 0,
    }


def _destino_proyecto_tiene_datos(proyecto_destino):
    return (
        LocalizacionPof.objects.filter(
            proyecto_especial=proyecto_destino
        ).exists()
        or LoteCargaPof.objects.filter(
            proyecto_especial=proyecto_destino
        ).exists()
        or SnapshotPadronLocalizacionPof.objects.filter(
            localizacion__proyecto_especial=proyecto_destino
        ).exists()
        or CargoPof.objects.filter(
            localizacion__proyecto_especial=proyecto_destino
        ).exists()
    )


def _cargar_localizaciones_origen_proyecto(proyecto_base):
    return list(
        LocalizacionPof.objects.filter(
            proyecto_especial=proyecto_base
        ).prefetch_related(
            Prefetch(
                "snapshots_padron",
                queryset=SnapshotPadronLocalizacionPof.objects.filter(vigente=True),
                to_attr="snapshots_vigentes_herencia",
            ),
            Prefetch(
                "cargos",
                queryset=CargoPof.objects.select_related("lote_carga"),
                to_attr="cargos_herencia",
            ),
        )
    )


def _validar_origen_proyecto(proyecto_base, localizaciones_origen):
    estados_validos = set(CargoPof.EstadoPof.values)
    unidades_validas = set(CargoPof.UnidadCantidad.values)

    for localizacion in localizaciones_origen:
        if localizacion.reunida_id:
            raise ValidationError(
                "La localización origen no puede pertenecer a una POF."
            )
        if localizacion.proyecto_especial_id != proyecto_base.id:
            raise ValidationError(
                "La localización origen no corresponde al Proyecto Especial base."
            )

        snapshots_vigentes = localizacion.snapshots_vigentes_herencia
        if len(snapshots_vigentes) != 1:
            raise ValidationError(
                f"La localización {_identificador_localizacion(localizacion)} "
                "no posee snapshot vigente."
            )

        for cargo in localizacion.cargos_herencia:
            if cargo.lote_carga.localizacion_id != localizacion.id:
                raise ValidationError(
                    "Un cargo origen no corresponde a su localización."
                )
            if cargo.lote_carga.proyecto_especial_id != proyecto_base.id:
                raise ValidationError(
                    "El lote de un cargo origen no corresponde al Proyecto Especial base."
                )
            if cargo.estado_pof not in estados_validos:
                raise ValidationError("El estado de un cargo origen no es válido.")
            if cargo.unidad_cantidad not in unidades_validas:
                raise ValidationError("La unidad de cantidad de un cargo origen no es válida.")
            if cargo.cantidad < 0:
                raise ValidationError(
                    "La cantidad de un cargo origen debe ser mayor o igual a cero."
                )
            if cargo.puntos_asignados < 0:
                raise ValidationError(
                    "Los puntos de un cargo origen no pueden ser negativos."
                )
            if cargo.total != _decimal_dos_decimales(
                cargo.cantidad * cargo.puntos_asignados
            ):
                raise ValidationError("El total de un cargo origen no es consistente.")


@transaction.atomic
def heredar_estado_inicial_proyecto_especial(proyecto_destino, usuario=None):
    """
    Clona el estado funcional del proyecto base al crear un Proyecto Especial.

    La referencia de base puede editarse luego sin volver a copiar ni reemplazar
    los datos que ya pertenecen al proyecto destino.
    """
    if not proyecto_destino or not proyecto_destino.pk:
        raise ValidationError(
            "El Proyecto Especial destino debe estar persistido antes de heredar."
        )

    proyecto_destino = ProyectosEspecialesPof.objects.select_for_update().get(
        pk=proyecto_destino.pk
    )
    resumen = _resumen_herencia_proyecto(
        proyecto_destino.proyecto_base_anterior_id
    )

    if not proyecto_destino.proyecto_base_anterior_id:
        return resumen

    if _destino_proyecto_tiene_datos(proyecto_destino):
        raise ValidationError(
            "El Proyecto Especial destino ya contiene datos y no puede recibir una herencia inicial automática."
        )

    proyecto_base = ProyectosEspecialesPof.objects.get(
        pk=proyecto_destino.proyecto_base_anterior_id
    )
    if proyecto_base.id == proyecto_destino.id:
        raise ValidationError(
            "El Proyecto Especial base no puede ser el mismo registro."
        )
    if proyecto_base.anio >= proyecto_destino.anio:
        raise ValidationError(
            "El Proyecto Especial base debe corresponder a un año anterior."
        )

    localizaciones_origen = _cargar_localizaciones_origen_proyecto(
        proyecto_base
    )
    _validar_origen_proyecto(proyecto_base, localizaciones_origen)
    asignaciones_zona = _preparar_asignaciones_zona_herencia(
        localizaciones_origen,
        proyecto_destino.anio,
    )

    resumen["heredada"] = True
    return _copiar_localizaciones_destino(
        localizaciones_origen,
        resumen,
        _usuario_herencia(usuario),
        timezone.now(),
        proyecto_destino=proyecto_destino,
        asignaciones_zona_por_localizacion=asignaciones_zona,
    )
