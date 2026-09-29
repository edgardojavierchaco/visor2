from copy import deepcopy
import hashlib
import logging
import re

from django.core.exceptions import ValidationError
from django.db import DatabaseError, connections, transaction
from django.db.models import Q
from django.utils import timezone

from ..models import (
    LocalizacionPof,
    POF_DB_ALIAS,
    ProyectosEspecialesPof,
    ReunidaPof,
    SnapshotPadronLocalizacionPof,
)


logger = logging.getLogger(__name__)

TIPO_IDENTIDAD_CUEANEXO = "CUEANEXO"
TIPO_IDENTIDAD_CUOF = "CUOF"
TIPOS_IDENTIDAD_ZONA = {
    TIPO_IDENTIDAD_CUEANEXO,
    TIPO_IDENTIDAD_CUOF,
}

TABLA_ZONAS_URBANAS = "reunidas_pof.zonas_educativas_urbanas"
TABLA_ZONAS_RURALES = "reunidas_pof.zonas_educativas_rurales"

_ESPACIOS_RE = re.compile(r"\s+")


def _texto(valor):
    return str(valor or "").strip()


def _normalizar_espacios(valor):
    return _ESPACIOS_RE.sub(" ", _texto(valor))


def _normalizar_tipo_zona(valor):
    tipo = _texto(valor).upper()
    tipos_validos = set(SnapshotPadronLocalizacionPof.TipoZonaEducativa.values)
    if tipo not in tipos_validos:
        raise ValidationError({
            "zona_educativa_tipo": [
                "El tipo de Zona Educativa debe ser URBANA o RURAL."
            ]
        })
    return tipo


def _normalizar_anio(valor):
    try:
        anio = int(valor)
    except (TypeError, ValueError):
        raise ValidationError({"anio": ["El año de la Zona Educativa no es válido."]})

    if anio < 1000 or anio > 9999:
        raise ValidationError({"anio": ["El año de la Zona Educativa debe tener 4 dígitos."]})
    return anio


def _normalizar_cueanexo(valor):
    cueanexo = _texto(valor)
    if not cueanexo:
        return ""
    if not cueanexo.isdigit() or len(cueanexo) != 9:
        raise ValidationError({
            "cueanexo": ["El CUEANEXO usado para Zona Educativa debe tener 9 dígitos."]
        })
    return cueanexo


def _normalizar_cuof(valor):
    # Conserva la misma semántica del Visualizador: CUOF recortado, sin
    # transformaciones de mayúsculas ni de contenido interno.
    return _texto(valor)


def construir_identidad_zona(anio, cueanexo="", cuof=""):
    """
    Construye la identidad lógica usada por Zona Educativa dentro de un ciclo.

    Regla canónica:
    - si existe CUEANEXO, la identidad es año + CUEANEXO;
    - si no existe CUEANEXO, la identidad es año + CUOF.
    """
    anio_normalizado = _normalizar_anio(anio)
    cueanexo_normalizado = _normalizar_cueanexo(cueanexo)

    if cueanexo_normalizado:
        return {
            "anio": anio_normalizado,
            "tipo_clave": TIPO_IDENTIDAD_CUEANEXO,
            "clave": cueanexo_normalizado,
        }

    cuof_normalizado = _normalizar_cuof(cuof)
    if not cuof_normalizado:
        raise ValidationError({
            "cuof": [
                "El CUOF es obligatorio para resolver Zona Educativa cuando no hay CUEANEXO."
            ]
        })

    return {
        "anio": anio_normalizado,
        "tipo_clave": TIPO_IDENTIDAD_CUOF,
        "clave": cuof_normalizado,
    }


def obtener_identidad_zona_localizacion(localizacion):
    """
    Deriva la identidad lógica desde una LocalizacionPof ya persistida.
    """
    if not localizacion or not getattr(localizacion, "pk", None):
        raise ValidationError({
            "localizacion": ["La localización POF debe existir para resolver Zona Educativa."]
        })

    if localizacion.reunida_id:
        anio = localizacion.reunida.anio
    elif localizacion.proyecto_especial_id:
        anio = localizacion.proyecto_especial.anio
    else:
        raise ValidationError({
            "localizacion": ["La localización POF no tiene una cabecera válida."]
        })

    return construir_identidad_zona(
        anio=anio,
        cueanexo=localizacion.cueanexo,
        cuof=localizacion.cuof,
    )


def _validar_identidad(identidad):
    if not isinstance(identidad, dict):
        raise ValidationError({"identidad": ["La identidad de Zona Educativa no es válida."]})

    anio = _normalizar_anio(identidad.get("anio"))
    tipo_clave = _texto(identidad.get("tipo_clave")).upper()
    clave = _texto(identidad.get("clave"))

    if tipo_clave not in TIPOS_IDENTIDAD_ZONA:
        raise ValidationError({
            "identidad": ["El tipo de identidad de Zona Educativa no es válido."]
        })

    if tipo_clave == TIPO_IDENTIDAD_CUEANEXO:
        clave = _normalizar_cueanexo(clave)
    else:
        clave = _normalizar_cuof(clave)
        if not clave:
            raise ValidationError({
                "identidad": ["La identidad por CUOF de Zona Educativa está vacía."]
            })

    return {
        "anio": anio,
        "tipo_clave": tipo_clave,
        "clave": clave,
    }


def queryset_localizaciones_identidad_zona(identidad, bloquear=False):
    """
    Devuelve todas las LocalizacionPof de la misma identidad y ciclo.

    Incluye Reunidas y Proyectos Especiales. Para CUOF sólo toma registros sin
    CUEANEXO, porque CUEANEXO tiene prioridad cuando existe.
    """
    identidad = _validar_identidad(identidad)

    reunidas_anio = ReunidaPof.objects.using(POF_DB_ALIAS).filter(
        anio=identidad["anio"]
    ).values("id")
    proyectos_anio = ProyectosEspecialesPof.objects.using(POF_DB_ALIAS).filter(
        anio=identidad["anio"]
    ).values("id")

    # Se filtra por IDs de cabecera mediante subconsultas en lugar de joins.
    # Así FOR UPDATE bloquea únicamente LocalizacionPof y evita problemas de
    # PostgreSQL con relaciones nullable y nombres calificados en la cláusula OF.
    filtro_anio = (
        Q(reunida_id__in=reunidas_anio)
        | Q(proyecto_especial_id__in=proyectos_anio)
    )
    queryset = LocalizacionPof.objects.using(POF_DB_ALIAS).filter(filtro_anio)

    if identidad["tipo_clave"] == TIPO_IDENTIDAD_CUEANEXO:
        queryset = queryset.filter(cueanexo=identidad["clave"])
    else:
        queryset = queryset.filter(
            Q(cueanexo="") | Q(cueanexo__isnull=True),
            cuof=identidad["clave"],
        )

    if bloquear:
        queryset = queryset.select_for_update()
    else:
        queryset = queryset.select_related(
            "reunida",
            "proyecto_especial",
        )

    return queryset.order_by("id")


def _clave_asignacion_snapshot(snapshot):
    tipo = _texto(snapshot.zona_educativa_tipo).upper()
    zona = _normalizar_espacios(snapshot.zona_educativa)
    puntos = snapshot.puntos_zona_educativa

    tiene_tipo = bool(tipo)
    tiene_zona = bool(zona)
    tiene_puntos = puntos is not None

    if not any((tiene_tipo, tiene_zona, tiene_puntos)):
        return None

    if not all((tiene_tipo, tiene_zona, tiene_puntos)):
        raise ValidationError({
            "zona_educativa": [
                "Existe un snapshot vigente con una asignación de Zona Educativa incompleta."
            ]
        })

    if tipo not in set(SnapshotPadronLocalizacionPof.TipoZonaEducativa.values):
        raise ValidationError({
            "zona_educativa_tipo": [
                "Existe un snapshot vigente con un tipo de Zona Educativa inválido."
            ]
        })

    try:
        puntos = int(puntos)
    except (TypeError, ValueError):
        raise ValidationError({
            "puntos_zona_educativa": [
                "Existe un snapshot vigente con puntos de Zona Educativa inválidos."
            ]
        })

    if puntos <= 0:
        raise ValidationError({
            "puntos_zona_educativa": [
                "Existe un snapshot vigente con puntos de Zona Educativa inválidos."
            ]
        })

    return {
        "tipo": tipo,
        "zona": zona,
        "puntos": puntos,
        "clave_comparable": (
            tipo,
            zona.casefold(),
            puntos,
        ),
    }


def obtener_asignacion_vigente_identidad(identidad):
    """
    Resuelve la única asignación lógica vigente para una identidad del ciclo.

    Los snapshots vacíos se consideran todavía sin asignar. Si aparecen dos
    asignaciones diferentes, se rechaza la resolución en vez de elegir una.
    """
    identidad = _validar_identidad(identidad)
    localizaciones = list(queryset_localizaciones_identidad_zona(identidad))
    localizacion_ids = [localizacion.id for localizacion in localizaciones]

    snapshots = {}
    if localizacion_ids:
        snapshots = {
            snapshot.localizacion_id: snapshot
            for snapshot in SnapshotPadronLocalizacionPof.objects.using(
                POF_DB_ALIAS
            ).filter(
                localizacion_id__in=localizacion_ids,
                vigente=True,
            ).order_by("localizacion_id", "-fecha_snapshot", "-id")
        }

    asignaciones = {}
    localizaciones_sin_zona = []
    localizaciones_sin_snapshot = []

    for localizacion in localizaciones:
        snapshot = snapshots.get(localizacion.id)
        if snapshot is None:
            localizaciones_sin_snapshot.append(localizacion.id)
            localizaciones_sin_zona.append(localizacion.id)
            continue

        asignacion = _clave_asignacion_snapshot(snapshot)
        if asignacion is None:
            localizaciones_sin_zona.append(localizacion.id)
            continue

        asignaciones.setdefault(
            asignacion["clave_comparable"],
            asignacion,
        )

    if len(asignaciones) > 1:
        raise ValidationError({
            "zona_educativa": [
                (
                    "La Zona Educativa vigente no es consistente para esta identidad "
                    "y año. Debe corregirse explícitamente antes de continuar."
                )
            ]
        })

    asignacion = next(iter(asignaciones.values()), None)
    return {
        "identidad": identidad,
        "asignada": asignacion is not None,
        "tipo": asignacion["tipo"] if asignacion else "",
        "zona": asignacion["zona"] if asignacion else "",
        "puntos": asignacion["puntos"] if asignacion else None,
        "localizaciones_total": len(localizaciones),
        "localizaciones_con_zona": (
            len(localizaciones) - len(localizaciones_sin_zona)
        ),
        "localizaciones_sin_zona": localizaciones_sin_zona,
        "localizaciones_sin_snapshot": localizaciones_sin_snapshot,
    }


def _filas_catalogo(tipo):
    tipo = _normalizar_tipo_zona(tipo)

    if tipo == SnapshotPadronLocalizacionPof.TipoZonaEducativa.URBANA:
        sql = f"""
            SELECT
                MIN(BTRIM(zona)) AS zona,
                MIN(puntos) AS puntos,
                COUNT(DISTINCT puntos) AS puntos_distintos
            FROM {TABLA_ZONAS_URBANAS}
            WHERE activo IS TRUE
              AND BTRIM(COALESCE(zona, '')) <> ''
            GROUP BY UPPER(BTRIM(zona))
            ORDER BY MIN(BTRIM(zona))
        """
    else:
        sql = f"""
            SELECT
                MIN(BTRIM(zona)) AS zona,
                MIN(puntos) AS puntos,
                COUNT(DISTINCT puntos) AS puntos_distintos,
                MIN(orden) AS orden,
                COUNT(DISTINCT orden) AS ordenes_distintos
            FROM {TABLA_ZONAS_RURALES}
            WHERE activo IS TRUE
              AND BTRIM(COALESCE(zona, '')) <> ''
            GROUP BY UPPER(BTRIM(zona))
            ORDER BY MIN(orden), MIN(BTRIM(zona))
        """

    try:
        with connections[POF_DB_ALIAS].cursor() as cursor:
            cursor.execute(sql)
            columnas = [columna[0] for columna in cursor.description]
            filas = [dict(zip(columnas, fila)) for fila in cursor.fetchall()]
    except DatabaseError as error:
        logger.exception("No se pudo consultar el catálogo de Zonas Educativas.")
        raise ValidationError({
            "zona_educativa": [
                "No fue posible consultar el catálogo de Zonas Educativas."
            ]
        }) from error

    return tipo, filas


def listar_zonas_educativas(tipo):
    """
    Lista las zonas activas del catálogo solicitado sin aplicar geografía.

    El servicio falla de forma explícita si el catálogo contiene una misma
    denominación lógica con puntos incompatibles.
    """
    tipo, filas = _filas_catalogo(tipo)
    resultados = []

    for fila in filas:
        if int(fila.get("puntos_distintos") or 0) != 1:
            raise ValidationError({
                "zona_educativa": [
                    "El catálogo de Zonas Educativas contiene una zona activa con puntajes ambiguos."
                ]
            })

        if tipo == SnapshotPadronLocalizacionPof.TipoZonaEducativa.RURAL:
            if int(fila.get("ordenes_distintos") or 0) != 1:
                raise ValidationError({
                    "zona_educativa": [
                        "El catálogo rural contiene una zona activa con orden ambiguo."
                    ]
                })

        resultados.append({
            "tipo": tipo,
            "zona": _normalizar_espacios(fila.get("zona")),
            "puntos": int(fila["puntos"]),
        })

    return resultados


def resolver_zona_educativa_catalogo(tipo, zona):
    """
    Resuelve tipo + zona contra el catálogo activo y devuelve puntos confiables.

    Los puntos nunca se reciben como dato autoritativo del cliente.
    """
    tipo = _normalizar_tipo_zona(tipo)
    zona_buscada = _normalizar_espacios(zona)
    if not zona_buscada:
        raise ValidationError({
            "zona_educativa": ["Debe seleccionar una Zona Educativa."]
        })

    if tipo == SnapshotPadronLocalizacionPof.TipoZonaEducativa.URBANA:
        tabla = TABLA_ZONAS_URBANAS
    else:
        tabla = TABLA_ZONAS_RURALES

    sql = f"""
        SELECT
            MIN(BTRIM(zona)) AS zona,
            MIN(puntos) AS puntos,
            COUNT(DISTINCT puntos) AS puntos_distintos
        FROM {tabla}
        WHERE activo IS TRUE
          AND UPPER(BTRIM(zona)) = UPPER(BTRIM(%s))
        GROUP BY UPPER(BTRIM(zona))
    """

    try:
        with connections[POF_DB_ALIAS].cursor() as cursor:
            cursor.execute(sql, [zona_buscada])
            filas = cursor.fetchall()
    except DatabaseError as error:
        logger.exception("No se pudo resolver la Zona Educativa contra el catálogo.")
        raise ValidationError({
            "zona_educativa": [
                "No fue posible consultar el catálogo de Zonas Educativas."
            ]
        }) from error

    if not filas:
        raise ValidationError({
            "zona_educativa": [
                "La Zona Educativa seleccionada no existe o no está activa en el catálogo."
            ]
        })

    if len(filas) != 1:
        raise ValidationError({
            "zona_educativa": [
                "La Zona Educativa seleccionada es ambigua en el catálogo."
            ]
        })

    zona_canonica, puntos, puntos_distintos = filas[0]
    if int(puntos_distintos or 0) != 1:
        raise ValidationError({
            "zona_educativa": [
                "La Zona Educativa seleccionada tiene puntajes ambiguos en el catálogo."
            ]
        })

    return {
        "tipo": tipo,
        "zona": _normalizar_espacios(zona_canonica),
        "puntos": int(puntos),
    }


def _id_bloqueo_identidad(identidad):
    identidad = _validar_identidad(identidad)
    texto = (
        f"reunidas_pof:zona_educativa:"
        f"{identidad['anio']}:{identidad['tipo_clave']}:{identidad['clave']}"
    )
    digest = hashlib.blake2b(
        texto.encode("utf-8"),
        digest_size=8,
        person=b"pof-zona",
    ).digest()
    return int.from_bytes(digest, byteorder="big", signed=True)


def bloquear_identidad_zona(identidad):
    """
    Toma un advisory lock transaccional de PostgreSQL para la identidad lógica.

    Debe invocarse dentro de transaction.atomic(). El lock se libera
    automáticamente al finalizar la transacción.
    """
    conexion = connections[POF_DB_ALIAS]
    if not conexion.in_atomic_block:
        raise RuntimeError(
            "El bloqueo de Zona Educativa debe ejecutarse dentro de una transacción atómica."
        )

    lock_id = _id_bloqueo_identidad(identidad)
    with conexion.cursor() as cursor:
        cursor.execute("SELECT pg_advisory_xact_lock(%s)", [lock_id])

    return lock_id


def obtener_asignacion_vigente_bloqueada(identidad):
    """
    Bloquea la identidad y relee inmediatamente su asignación vigente.

    Está pensada para flujos de escritura: el llamador abre transaction.atomic()
    y usa esta función antes de decidir si reutiliza, asigna o sincroniza Zona.
    """
    bloquear_identidad_zona(identidad)
    return obtener_asignacion_vigente_identidad(identidad)


def obtener_asignacion_snapshot(snapshot):
    """
    Devuelve la asignación Zona/Puntos congelada en un snapshot o None.
    """
    if snapshot is None:
        return None

    asignacion = _clave_asignacion_snapshot(snapshot)
    if asignacion is None:
        return None

    return {
        "tipo": asignacion["tipo"],
        "zona": asignacion["zona"],
        "puntos": asignacion["puntos"],
    }


def asignaciones_zona_equivalentes(asignacion_a, asignacion_b):
    """
    Compara dos asignaciones lógicas de Zona respetando puntos congelados.
    """
    if asignacion_a is None or asignacion_b is None:
        return asignacion_a is None and asignacion_b is None

    try:
        tipo_a = _normalizar_tipo_zona(asignacion_a.get("tipo"))
        tipo_b = _normalizar_tipo_zona(asignacion_b.get("tipo"))
        zona_a = _normalizar_espacios(asignacion_a.get("zona")).casefold()
        zona_b = _normalizar_espacios(asignacion_b.get("zona")).casefold()
        puntos_a = int(asignacion_a.get("puntos"))
        puntos_b = int(asignacion_b.get("puntos"))
    except (AttributeError, TypeError, ValueError):
        return False

    return (
        tipo_a == tipo_b
        and zona_a == zona_b
        and puntos_a == puntos_b
    )


def seleccion_zona_coincide_asignacion(tipo, zona, asignacion):
    """
    Compara sólo tipo+zona con una asignación vigente.

    Se usa en cargas normales: si ya existe una asignación en el ciclo, los
    puntos congelados vigentes prevalecen aunque el catálogo haya cambiado.
    """
    if asignacion is None:
        return False

    try:
        tipo_normalizado = _normalizar_tipo_zona(tipo)
    except ValidationError:
        return False

    return (
        tipo_normalizado == _texto(asignacion.get("tipo")).upper()
        and _normalizar_espacios(zona).casefold()
        == _normalizar_espacios(asignacion.get("zona")).casefold()
    )


def _crear_snapshot_sincronizacion_zona(snapshot_origen, asignacion, usuario=None):
    """
    Versiona sólo Zona/Puntos conservando intacto el estado Padrón del snapshot.

    Una asignación None representa una eliminación explícita de Zona Educativa:
    el nuevo snapshot queda nuevamente pendiente, con tipo/zona vacíos y puntos NULL.
    """
    if snapshot_origen is None:
        raise ValidationError({
            "zona_educativa": [
                "No existe un snapshot vigente que pueda sincronizarse."
            ]
        })

    if asignacion is None:
        tipo = ""
        zona = ""
        puntos = None
    else:
        tipo = _normalizar_tipo_zona(asignacion.get("tipo"))
        zona = _normalizar_espacios(asignacion.get("zona"))
        try:
            puntos = int(asignacion.get("puntos"))
        except (TypeError, ValueError):
            puntos = 0

        if not zona or puntos <= 0:
            raise ValidationError({
                "zona_educativa": [
                    "La asignación de Zona Educativa a sincronizar no es válida."
                ]
            })

    momento = timezone.now()
    snapshot_origen.vigente = False
    snapshot_origen.save(update_fields=["vigente"])

    return SnapshotPadronLocalizacionPof.objects.using(POF_DB_ALIAS).create(
        localizacion=snapshot_origen.localizacion,
        tipo_snapshot=SnapshotPadronLocalizacionPof.TipoSnapshot.SINCRONIZACION,
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
        zona_educativa_tipo=tipo,
        zona_educativa=zona,
        puntos_zona_educativa=puntos,
        datos_padron=deepcopy(snapshot_origen.datos_padron),
        usuario=usuario,
        fecha_snapshot=momento,
    )


def sincronizar_zona_faltante_identidad(
    identidad,
    asignacion,
    usuario=None,
    excluir_localizacion_ids=None,
):
    """
    Completa Zona en snapshots vigentes aún vacíos de la misma identidad/ciclo.

    No reemplaza una asignación diferente: ante contradicción aborta para que el
    cambio se haga mediante la operación explícita de Zona Educativa.
    """
    bloquear_identidad_zona(identidad)
    excluir_ids = {
        int(valor)
        for valor in (excluir_localizacion_ids or set())
        if str(valor).isdigit()
    }

    localizaciones = list(
        queryset_localizaciones_identidad_zona(
            identidad,
            bloquear=True,
        )
    )
    sincronizados = []

    for localizacion in localizaciones:
        if localizacion.id in excluir_ids:
            continue

        snapshot = (
            SnapshotPadronLocalizacionPof.objects.using(POF_DB_ALIAS)
            .select_for_update()
            .filter(
                localizacion_id=localizacion.id,
                vigente=True,
            )
            .order_by("-fecha_snapshot", "-id")
            .first()
        )
        if snapshot is None:
            continue

        asignacion_actual = obtener_asignacion_snapshot(snapshot)
        if asignacion_actual is None:
            nuevo_snapshot = _crear_snapshot_sincronizacion_zona(
                snapshot,
                asignacion,
                usuario=usuario,
            )
            sincronizados.append(nuevo_snapshot.id)
            continue

        if not asignaciones_zona_equivalentes(asignacion_actual, asignacion):
            raise ValidationError({
                "zona_educativa": [
                    (
                        "Existe otra Zona Educativa vigente para esta identidad "
                        "y año. Debe corregirse explícitamente antes de continuar."
                    )
                ]
            })

    return sincronizados


def _serializar_asignacion_zona(asignacion):
    if asignacion is None:
        return {
            "tipo": "",
            "zona": "",
            "puntos": None,
        }
    return {
        "tipo": _texto(asignacion.get("tipo")).upper(),
        "zona": _normalizar_espacios(asignacion.get("zona")),
        "puntos": int(asignacion.get("puntos")),
    }


def _serializar_estado_zona_vigente(resultado):
    return {
        "identidad": resultado["identidad"],
        "asignada": bool(resultado["asignada"]),
        "tipo": resultado["tipo"],
        "zona": resultado["zona"],
        "puntos": resultado["puntos"],
        "localizaciones_total": resultado["localizaciones_total"],
        "localizaciones_con_zona": resultado["localizaciones_con_zona"],
        "localizaciones_sin_zona": len(resultado["localizaciones_sin_zona"]),
        "localizaciones_sin_snapshot": len(resultado["localizaciones_sin_snapshot"]),
    }


def obtener_estado_zona_identidad(anio, cueanexo="", cuof=""):
    identidad = construir_identidad_zona(
        anio=anio,
        cueanexo=cueanexo,
        cuof=cuof,
    )
    return _serializar_estado_zona_vigente(
        obtener_asignacion_vigente_identidad(identidad)
    )


def obtener_estado_zona_localizacion(localizacion_id):
    localizacion = (
        LocalizacionPof.objects.using(POF_DB_ALIAS)
        .select_related("reunida", "proyecto_especial")
        .get(pk=localizacion_id)
    )
    identidad = obtener_identidad_zona_localizacion(localizacion)
    estado = _serializar_estado_zona_vigente(
        obtener_asignacion_vigente_identidad(identidad)
    )
    estado["localizacion"] = {
        "id": localizacion.id,
        "cueanexo": _texto(localizacion.cueanexo),
        "cuof": _texto(localizacion.cuof),
    }
    return estado


def _serializar_usuario_snapshot(usuario):
    if not usuario:
        return {
            "id": None,
            "nombre": "",
        }
    return {
        "id": getattr(usuario, "pk", None),
        "nombre": str(usuario).strip(),
    }


def _cambios_asignacion_zona(anterior, nuevo):
    anterior = _serializar_asignacion_zona(anterior)
    nuevo = _serializar_asignacion_zona(nuevo)
    cambios = []

    definiciones = (
        (
            "zona_educativa_tipo",
            "Tipo de Zona Educativa",
            anterior["tipo"],
            nuevo["tipo"],
        ),
        (
            "zona_educativa",
            "Zona Educativa",
            anterior["zona"],
            nuevo["zona"],
        ),
        (
            "puntos_zona_educativa",
            "Puntos Zona Educativa",
            anterior["puntos"],
            nuevo["puntos"],
        ),
    )
    for campo, etiqueta, valor_anterior, valor_nuevo in definiciones:
        if valor_anterior == valor_nuevo:
            continue
        cambios.append({
            "campo": campo,
            "etiqueta": etiqueta,
            "anterior": valor_anterior,
            "nuevo": valor_nuevo,
        })

    return cambios


def obtener_historial_zona_localizacion(localizacion_id):
    localizacion = (
        LocalizacionPof.objects.using(POF_DB_ALIAS)
        .select_related("reunida", "proyecto_especial")
        .get(pk=localizacion_id)
    )
    identidad = obtener_identidad_zona_localizacion(localizacion)
    snapshots = list(
        SnapshotPadronLocalizacionPof.objects.using(POF_DB_ALIAS)
        .select_related("usuario")
        .filter(localizacion_id=localizacion.id)
        .order_by("fecha_snapshot", "id")
    )

    eventos = []
    snapshot_anterior = None

    for snapshot in snapshots:
        if snapshot_anterior is None:
            snapshot_anterior = snapshot
            continue

        asignacion_anterior = obtener_asignacion_snapshot(snapshot_anterior)
        asignacion_nueva = obtener_asignacion_snapshot(snapshot)

        if asignaciones_zona_equivalentes(
            asignacion_anterior,
            asignacion_nueva,
        ):
            snapshot_anterior = snapshot
            continue

        cambios = _cambios_asignacion_zona(
            asignacion_anterior,
            asignacion_nueva,
        )
        if cambios:
            eventos.append({
                "snapshot_id": snapshot.id,
                "fecha": snapshot.fecha_snapshot,
                "tipo_snapshot": snapshot.tipo_snapshot,
                "usuario": _serializar_usuario_snapshot(snapshot.usuario),
                "anterior": _serializar_asignacion_zona(asignacion_anterior),
                "nuevo": _serializar_asignacion_zona(asignacion_nueva),
                "cambios": cambios,
            })

        snapshot_anterior = snapshot

    snapshot_vigente = next(
        (snapshot for snapshot in reversed(snapshots) if snapshot.vigente),
        None,
    )
    asignacion_vigente = obtener_asignacion_snapshot(snapshot_vigente)

    return {
        "identidad": identidad,
        "localizacion": {
            "id": localizacion.id,
            "cueanexo": _texto(localizacion.cueanexo),
            "cuof": _texto(localizacion.cuof),
        },
        "vigente": _serializar_asignacion_zona(asignacion_vigente),
        "eventos": list(reversed(eventos)),
    }


def _resolver_asignacion_cambio_zona(tipo, zona):
    """
    Interpreta la edición explícita de Zona.

    - tipo + zona vacíos: quitar la asignación y volver a estado pendiente.
    - sólo uno vacío: combinación inválida.
    - ambos informados: resolver contra el catálogo activo.
    """
    tipo_texto = _texto(tipo)
    zona_texto = _normalizar_espacios(zona)

    if not tipo_texto and not zona_texto:
        return None

    if not tipo_texto or not zona_texto:
        raise ValidationError({
            "zona_educativa": [
                "Para asignar una Zona Educativa debe indicar tipo y zona en conjunto."
            ]
        })

    return resolver_zona_educativa_catalogo(tipo_texto, zona_texto)


@transaction.atomic(using=POF_DB_ALIAS)
def cambiar_zona_educativa_localizacion(
    localizacion_id,
    tipo,
    zona,
    usuario=None,
):
    """
    Cambia explícitamente la Zona de toda la identidad lógica dentro del ciclo.

    La localización recibida sólo actúa como punto de entrada confiable. El
    alcance real se deriva en servidor por año+CUEANEXO o fallback año+CUOF.
    """
    localizacion = (
        LocalizacionPof.objects.using(POF_DB_ALIAS)
        .select_related("reunida", "proyecto_especial")
        .get(pk=localizacion_id)
    )
    identidad = obtener_identidad_zona_localizacion(localizacion)

    bloquear_identidad_zona(identidad)
    asignacion_nueva = _resolver_asignacion_cambio_zona(tipo, zona)

    localizaciones = list(
        queryset_localizaciones_identidad_zona(
            identidad,
            bloquear=True,
        )
    )
    if not localizaciones:
        raise ValidationError({
            "localizacion": [
                "No existen localizaciones para la identidad de Zona Educativa."
            ]
        })

    localizacion_ids = [item.id for item in localizaciones]
    snapshots = {
        snapshot.localizacion_id: snapshot
        for snapshot in (
            SnapshotPadronLocalizacionPof.objects.using(POF_DB_ALIAS)
            .select_for_update()
            .select_related("localizacion")
            .filter(
                localizacion_id__in=localizacion_ids,
                vigente=True,
            )
            .order_by("localizacion_id", "-fecha_snapshot", "-id")
        )
    }

    faltantes = [
        localizacion_id
        for localizacion_id in localizacion_ids
        if localizacion_id not in snapshots
    ]
    if faltantes:
        raise ValidationError({
            "zona_educativa": [
                (
                    "No se puede cambiar la Zona porque una o más localizaciones "
                    "de la misma identidad no poseen snapshot vigente."
                )
            ]
        })

    actuales = {
        localizacion_id: obtener_asignacion_snapshot(snapshot)
        for localizacion_id, snapshot in snapshots.items()
    }
    if all(
        asignaciones_zona_equivalentes(asignacion_actual, asignacion_nueva)
        for asignacion_actual in actuales.values()
    ):
        return {
            "ok": False,
            "tipo": "sin_cambios",
            "mensaje": (
                "La identidad ya se encuentra sin Zona Educativa."
                if asignacion_nueva is None
                else "La Zona Educativa seleccionada ya es la vigente."
            ),
            "errores": {},
        }

    snapshots_creados = []
    for localizacion_destino in localizaciones:
        snapshot_actual = snapshots[localizacion_destino.id]
        nuevo_snapshot = _crear_snapshot_sincronizacion_zona(
            snapshot_actual,
            asignacion_nueva,
            usuario=usuario,
        )
        snapshots_creados.append(nuevo_snapshot.id)

    return {
        "ok": True,
        "mensaje": (
            "Zona Educativa quitada correctamente."
            if asignacion_nueva is None
            else "Zona Educativa actualizada correctamente."
        ),
        "identidad": identidad,
        "zona_educativa": _serializar_asignacion_zona(asignacion_nueva),
        "localizaciones_actualizadas": localizacion_ids,
        "snapshots_creados": snapshots_creados,
    }
