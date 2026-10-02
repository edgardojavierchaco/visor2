from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation

from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db.models import Max, Q
from django.utils import timezone

from ..models import (
    CargoPof,
    HistorialAsociacionAnexoPof,
    LocalizacionPof,
    MovimientoCargoPof,
    SnapshotPadronLocalizacionPof,
)
from .exportacion_rows import obtener_clave_consolidacion_cargo
from .zona_educativa_service import obtener_historial_zona_localizacion
from .filtros_pof_service import (
    TIPOS_MOVIMIENTO_LABELS,
    MENSAJE_FILTROS_INVALIDOS,
    NIVEL_TODOS,
    TIPO_MOVIMIENTO_TODOS,
    VISTA_30_DIAS,
    VISTA_7_DIAS,
    VISTA_RECIENTES,
    VISTAS_RAPIDAS,
    construir_chips_filtros_historial,
    filtros_historial_suficientes,
    obtener_mensaje_filtros_insuficientes_historial,
    obtener_filtros_historial_pof,
    obtener_filtros_historial_pof_con_errores,
    querystring_limpio_historial,
)
from .niveles_service import NIVELES_VALIDOS, limpiar_texto, normalizar_nivel


def obtener_filtros_historial(request):
    return obtener_filtros_historial_pof(request)


MAX_CARGOS_HISTORIAL = 100
TIPOS_MOVIMIENTO_ESTADO = (
    MovimientoCargoPof.TipoMovimiento.AFECTADO,
    MovimientoCargoPof.TipoMovimiento.DESAFECTADO,
)
FLECHA_CAMBIO = "\u2192"
GUION_VACIO = "\u2014"
MOJIBAKE_GUION_VACIO = "\u00e2\u20ac\u201d"
OBSERVACION_PLACEHOLDERS = {"-", "--", "---", MOJIBAKE_GUION_VACIO, GUION_VACIO}

TIPO_EVENTO_ZONA_EDUCATIVA = "ZONA_EDUCATIVA"
TIPO_EVENTO_ANEXO_POF = "ANEXO_POF"
TIPOS_EVENTO_CARGO = set(MovimientoCargoPof.TipoMovimiento.values)

NOMBRES_CAMPOS_DIFF = {
    "ceic": "CEIC",
    "cargo": "Cargo",
    "oferta": "Ofertas",
    "cantidad": "Cantidad",
    "unidad_cantidad": "Unidad",
    "puntos_asignados": "Puntos asignados",
    "total": "Total",
    "estado_pof": "Estado POF",
    "observacion": "Observación",
}

CAMPOS_JSON_AUDITORIA = {"ofertas_seleccionadas", "snapshot_ceic"}
CAMPOS_EXCLUIDOS_DIFF = {"observacion"} | CAMPOS_JSON_AUDITORIA
CAMPOS_ENTEROS_DIFF = {"id", "ceic", "cantidad"}
CAMPOS_DECIMALES_DIFF = {"puntos_asignados", "puntos", "total"}
ORDEN_CAMPOS_DIFF = (
    "ceic",
    "cargo",
    "oferta",
    "cantidad",
    "unidad_cantidad",
    "puntos_asignados",
    "total",
    "estado_pof",
)
ESTADOS_POF_DISPLAY = {
    "AFECTADO": "Afectado",
    "DESAFECTADO": "Desafectado",
}
NOMBRES_CAMPOS_RESUMEN = {
    "puntos_asignados": "Puntos",
    "estado_pof": "Estado",
}


def _obtener_tipo_movimiento_display(movimiento):
    return TIPOS_MOVIMIENTO_LABELS.get(
        movimiento.tipo_movimiento,
        movimiento.get_tipo_movimiento_display(),
    )


def _formatear_entero(valor):
    if valor in (None, ""):
        return GUION_VACIO
    try:
        return str(int(Decimal(str(valor))))
    except (ArithmeticError, ValueError):
        return str(valor)


def _formatear_decimal(valor):
    if valor in (None, ""):
        return GUION_VACIO
    try:
        return f"{Decimal(str(valor)):.2f}"
    except (ArithmeticError, ValueError):
        return str(valor)


def _formatear_valor_campo(clave, valor):
    if valor in (None, ""):
        return GUION_VACIO
    clave = str(clave or "").lower()
    if clave == "estado_pof":
        return _formatear_estado_pof(valor)
    if clave in {"id", "ceic", "cantidad"} or clave.endswith("_id"):
        return _formatear_entero(valor)
    if clave in {"puntos_asignados", "puntos", "total"}:
        return _formatear_decimal(valor)
    return _valor_serializable(valor)


def _valor_serializable(valor):
    if valor in (None, ""):
        return GUION_VACIO
    if isinstance(valor, Decimal):
        return f"{valor:.2f}"
    if isinstance(valor, datetime):
        if timezone.is_aware(valor):
            valor = timezone.localtime(valor)
        return valor.strftime("%d/%m/%Y %H:%M")
    if isinstance(valor, date):
        return valor.strftime("%d/%m/%Y")
    if isinstance(valor, bool):
        return "Sí" if valor else "No"
    return str(valor)


def _valor_crudo_comparable(valor):
    if valor in (None, ""):
        return GUION_VACIO
    return _valor_serializable(valor)


def _formatear_estado_pof(valor):
    """
    Traduce el estado técnico POF al texto visible del historial.

    - Expone `AFECTADO` como `Activo`.
    - Expone `DESAFECTADO` como `Baja`.
    - Conserva el valor original solo si no coincide con estados conocidos.
    """
    texto = str(valor or "").strip()
    if not texto:
        return GUION_VACIO
    return ESTADOS_POF_DISPLAY.get(texto.upper(), texto)


def _normalizar_observacion_comparable(valor):
    """
    Normaliza observaciones para comparar cambios auditables reales.

    - Trata `None`, vacío, guiones, em dash y espacios como ausencia de observación.
    - Colapsa espacios internos para evitar falsos cambios de formato.
    - Devuelve siempre texto plano comparable.
    """
    texto = str(valor or "").strip()
    if not texto or texto in OBSERVACION_PLACEHOLDERS:
        return ""
    return " ".join(texto.split())


def _normalizar_texto_comparable(valor):
    return " ".join(str(valor or "").strip().split())


def _normalizar_decimal_comparable(valor):
    try:
        return Decimal(str(valor).strip())
    except (InvalidOperation, ValueError, TypeError):
        return None


def _valor_comparable(clave, valor):
    if valor in (None, ""):
        return ""
    clave = str(clave or "").lower()
    if clave == "observacion":
        return _normalizar_observacion_comparable(valor)
    if clave in CAMPOS_ENTEROS_DIFF or clave.endswith("_id"):
        numero = _normalizar_decimal_comparable(valor)
        if numero is not None:
            return int(numero)
    if clave in CAMPOS_DECIMALES_DIFF:
        numero = _normalizar_decimal_comparable(valor)
        if numero is not None:
            return numero
    if clave == "estado_pof":
        return _normalizar_texto_comparable(valor).upper()
    return _normalizar_texto_comparable(valor)


def _valores_equivalentes(clave, anterior, nuevo):
    anterior_comparable = _valor_comparable(clave, anterior)
    nuevo_comparable = _valor_comparable(clave, nuevo)
    if anterior_comparable == nuevo_comparable:
        return True

    clave = str(clave or "").lower()
    if clave in CAMPOS_ENTEROS_DIFF or clave in CAMPOS_DECIMALES_DIFF or clave.endswith("_id"):
        return False

    anterior_decimal = _normalizar_decimal_comparable(anterior)
    nuevo_decimal = _normalizar_decimal_comparable(nuevo)
    return (
        anterior_decimal is not None
        and nuevo_decimal is not None
        and anterior_decimal == nuevo_decimal
    )


def _cantidades_comparables_movimiento(movimiento):
    if movimiento.tipo_movimiento != MovimientoCargoPof.TipoMovimiento.MODIFICACION:
        return None

    anteriores = movimiento.valores_anteriores
    nuevos = movimiento.valores_nuevos
    if not isinstance(anteriores, dict) or not isinstance(nuevos, dict):
        return None
    if "cantidad" not in anteriores or "cantidad" not in nuevos:
        return None

    cantidad_anterior = _normalizar_decimal_comparable(anteriores.get("cantidad"))
    cantidad_nueva = _normalizar_decimal_comparable(nuevos.get("cantidad"))
    if cantidad_anterior is None or cantidad_nueva is None:
        return None
    return cantidad_anterior, cantidad_nueva


def es_cambio_real_cantidad_movimiento(movimiento):
    cantidades = _cantidades_comparables_movimiento(movimiento)
    return bool(cantidades and cantidades[0] != cantidades[1])


def _observaciones_comparables_movimiento(movimiento):
    if movimiento.tipo_movimiento != MovimientoCargoPof.TipoMovimiento.MODIFICACION:
        return None

    anteriores = movimiento.valores_anteriores
    nuevos = movimiento.valores_nuevos
    if not isinstance(anteriores, dict) or not isinstance(nuevos, dict):
        return None
    if "observacion" not in anteriores or "observacion" not in nuevos:
        return None

    return (
        _normalizar_observacion_comparable(anteriores.get("observacion")),
        _normalizar_observacion_comparable(nuevos.get("observacion")),
    )


def es_cambio_real_observacion_movimiento(movimiento):
    observaciones = _observaciones_comparables_movimiento(movimiento)
    return bool(observaciones and observaciones[0] != observaciones[1])


def es_cambio_real_estado_movimiento(movimiento):
    """
    Detecta un cambio real de Estado POF auditable.

    - Acepta solo movimientos Afectado o Desafectado.
    - Compara estado anterior y nuevo con la normalización existente.
    - Ignora movimientos sin cambio efectivo de estado.
    """
    if movimiento.tipo_movimiento not in TIPOS_MOVIMIENTO_ESTADO:
        return False

    estado_anterior = _valor_comparable(
        "estado_pof",
        movimiento.estado_anterior,
    )
    estado_nuevo = _valor_comparable(
        "estado_pof",
        movimiento.estado_nuevo,
    )

    return bool(
        estado_anterior
        and estado_nuevo
        and estado_anterior != estado_nuevo
    )


def enriquecer_filas_con_historial_cantidad(filas):
    cargo_ids = sorted({
        cargo_id
        for fila in filas
        for cargo_id in fila.get("cargo_ids", [])
        if isinstance(cargo_id, int) and cargo_id > 0
    })
    modificados = set()

    if cargo_ids:
        movimientos = MovimientoCargoPof.objects.filter(
            cargo_id__in=cargo_ids,
            tipo_movimiento=MovimientoCargoPof.TipoMovimiento.MODIFICACION,
        ).only(
            "cargo_id",
            "tipo_movimiento",
            "valores_anteriores",
            "valores_nuevos",
        )
        for movimiento in movimientos:
            if movimiento.cargo_id not in modificados and es_cambio_real_cantidad_movimiento(movimiento):
                modificados.add(movimiento.cargo_id)

    for fila in filas:
        ids_fila = sorted({
            cargo_id
            for cargo_id in fila.get("cargo_ids", [])
            if isinstance(cargo_id, int) and cargo_id > 0
        })
        fila["cargo_ids"] = ids_fila
        fila["tiene_modificacion_cantidad"] = any(
            cargo_id in modificados for cargo_id in ids_fila
        )

    return filas


def enriquecer_filas_con_historial_observacion(filas):
    """Marca en lote las filas con cambios reales de observación."""
    cargo_ids = sorted({
        cargo_id
        for fila in filas
        for cargo_id in fila.get("cargo_ids", [])
        if isinstance(cargo_id, int) and cargo_id > 0
    })
    modificados = set()

    if cargo_ids:
        movimientos = MovimientoCargoPof.objects.filter(
            cargo_id__in=cargo_ids,
            tipo_movimiento=MovimientoCargoPof.TipoMovimiento.MODIFICACION,
        ).only(
            "cargo_id",
            "tipo_movimiento",
            "valores_anteriores",
            "valores_nuevos",
        )
        for movimiento in movimientos:
            if (
                movimiento.cargo_id not in modificados
                and es_cambio_real_observacion_movimiento(movimiento)
            ):
                modificados.add(movimiento.cargo_id)

    for fila in filas:
        ids_fila = sorted({
            cargo_id
            for cargo_id in fila.get("cargo_ids", [])
            if isinstance(cargo_id, int) and cargo_id > 0
        })
        fila["cargo_ids"] = ids_fila
        fila["tiene_modificacion_observacion"] = any(
            cargo_id in modificados for cargo_id in ids_fila
        )

    return filas


def enriquecer_filas_con_historial_zona(filas):
    """
    Marca en lote las filas cuyo historial de Zona Educativa contiene al menos
    un cambio explícito en el ciclo actual o en algún ancestro enlazado por
    cargo_origen.

    Además expone un cargo_id representativo para abrir el historial interanual
    de Zona desde la fila visible sin tener que resolver la cadena en frontend.
    """
    cargo_ids = sorted({
        cargo_id
        for fila in filas
        for cargo_id in fila.get("cargo_ids", [])
        if isinstance(cargo_id, int) and cargo_id > 0
    })

    cargos_por_id = {}
    pendientes = set(cargo_ids)

    while pendientes:
        registros = list(
            CargoPof.objects.filter(pk__in=pendientes).values(
                "id",
                "cargo_origen_id",
                "localizacion_id",
            )
        )
        nuevos = set()
        for registro in registros:
            cargo_id = registro["id"]
            cargos_por_id[cargo_id] = registro
            origen_id = registro.get("cargo_origen_id")
            if origen_id and origen_id not in cargos_por_id:
                nuevos.add(origen_id)
        pendientes = nuevos

    localizacion_ids = {
        registro["localizacion_id"]
        for registro in cargos_por_id.values()
        if registro.get("localizacion_id")
    }
    localizaciones_con_evento = set()

    if localizacion_ids:
        localizaciones_con_evento = set(
            SnapshotPadronLocalizacionPof.objects.filter(
                localizacion_id__in=localizacion_ids,
                zona_educativa_evento=True,
            ).values_list("localizacion_id", flat=True).distinct()
        )

    cache_tiene_historial = {}

    def cargo_tiene_historial_zona(cargo_id):
        if cargo_id in cache_tiene_historial:
            return cache_tiene_historial[cargo_id]

        visitados = set()
        actual_id = cargo_id
        tiene_historial = False

        while actual_id and actual_id not in visitados:
            visitados.add(actual_id)
            registro = cargos_por_id.get(actual_id)
            if not registro:
                break
            if registro.get("localizacion_id") in localizaciones_con_evento:
                tiene_historial = True
                break
            actual_id = registro.get("cargo_origen_id")

        for visitado in visitados:
            cache_tiene_historial[visitado] = tiene_historial
        return tiene_historial

    for fila in filas:
        ids_fila = sorted({
            cargo_id
            for cargo_id in fila.get("cargo_ids", [])
            if isinstance(cargo_id, int) and cargo_id > 0
        })
        fila["cargo_ids"] = ids_fila

        localizacion_fila = fila.get("localizacion_id")
        ids_misma_localizacion = [
            cargo_id
            for cargo_id in ids_fila
            if (
                not localizacion_fila
                or str(
                    cargos_por_id.get(cargo_id, {}).get("localizacion_id") or ""
                )
                == str(localizacion_fila)
            )
        ]
        ids_contexto = ids_misma_localizacion or ids_fila

        cargo_id_historial = next(
            (
                cargo_id
                for cargo_id in ids_contexto
                if cargo_tiene_historial_zona(cargo_id)
            ),
            ids_contexto[0] if ids_contexto else None,
        )
        fila["cargo_id_historial_zona"] = cargo_id_historial
        fila["tiene_modificacion_zona"] = any(
            cargo_tiene_historial_zona(cargo_id)
            for cargo_id in ids_contexto
        )

    return filas


def enriquecer_filas_con_ultima_actividad(filas):
    """
    Anota en lote la fecha del último movimiento de los cargos de cada fila.

    - Agrupa en BD por cargo y obtiene MAX(fecha).
    - Consolida luego por los cargo_ids que representa cada fila.
    - Evita consultas N+1 y no altera los historiales existentes.
    """
    cargo_ids = sorted({
        cargo_id
        for fila in filas
        for cargo_id in fila.get("cargo_ids", [])
        if isinstance(cargo_id, int) and cargo_id > 0
    })
    ultima_por_cargo = {}

    if cargo_ids:
        movimientos = (
            MovimientoCargoPof.objects.filter(cargo_id__in=cargo_ids)
            .values("cargo_id")
            .annotate(ultima_actividad=Max("fecha"))
        )
        ultima_por_cargo = {
            item["cargo_id"]: item["ultima_actividad"]
            for item in movimientos
            if item.get("ultima_actividad") is not None
        }

    for fila in filas:
        ids_fila = sorted({
            cargo_id
            for cargo_id in fila.get("cargo_ids", [])
            if isinstance(cargo_id, int) and cargo_id > 0
        })
        fechas = [
            ultima_por_cargo[cargo_id]
            for cargo_id in ids_fila
            if cargo_id in ultima_por_cargo
        ]
        fila["ultima_actividad"] = max(fechas) if fechas else None

    return filas


def enriquecer_filas_con_historial_estado(filas):
    """
    Marca en lote las filas que poseen cambios reales de Estado POF.

    - Obtiene todos los cargo_ids de las filas recibidas.
    - Ejecuta una única consulta para movimientos Afectado y Desafectado.
    - Evita consultas N+1 independientemente de la cantidad de filas.
    - Expone `tiene_modificacion_estado` para el preview HTML.
    """
    cargo_ids = sorted({
        cargo_id
        for fila in filas
        for cargo_id in fila.get("cargo_ids", [])
        if isinstance(cargo_id, int) and cargo_id > 0
    })
    modificados = set()

    if cargo_ids:
        movimientos = MovimientoCargoPof.objects.filter(
            cargo_id__in=cargo_ids,
            tipo_movimiento__in=TIPOS_MOVIMIENTO_ESTADO,
        ).only(
            "cargo_id",
            "tipo_movimiento",
            "estado_anterior",
            "estado_nuevo",
        )

        for movimiento in movimientos:
            if (
                movimiento.cargo_id not in modificados
                and es_cambio_real_estado_movimiento(movimiento)
            ):
                modificados.add(movimiento.cargo_id)

    for fila in filas:
        ids_fila = sorted({
            cargo_id
            for cargo_id in fila.get("cargo_ids", [])
            if isinstance(cargo_id, int) and cargo_id > 0
        })

        fila["cargo_ids"] = ids_fila
        fila["tiene_modificacion_estado"] = any(
            cargo_id in modificados
            for cargo_id in ids_fila
        )

    return filas


def _serializar_mapa(valores):
    if not isinstance(valores, dict):
        return {}
    return {
        str(clave): _formatear_valor_campo(clave, valor)
        for clave, valor in valores.items()
        if str(clave) not in CAMPOS_JSON_AUDITORIA
    }


def _nombre_campo_diff(clave):
    return NOMBRES_CAMPOS_DIFF.get(
        clave,
        str(clave).replace("_", " ").capitalize(),
    )


def _ordenar_claves_diff(claves):
    orden = {clave: indice for indice, clave in enumerate(ORDEN_CAMPOS_DIFF)}
    return sorted(
        claves,
        key=lambda clave: (orden.get(str(clave), len(orden)), str(clave)),
    )


def _es_movimiento_afectado_inicial(movimiento):
    return bool(
        movimiento.tipo_movimiento
        == MovimientoCargoPof.TipoMovimiento.AFECTADO
        and not _valor_comparable("estado_pof", movimiento.estado_anterior)
    )


def _es_movimiento_desafectado_inicial(movimiento):
    return bool(
        movimiento.tipo_movimiento
        == MovimientoCargoPof.TipoMovimiento.DESAFECTADO
        and not _valor_comparable("estado_pof", movimiento.estado_anterior)
    )


def _construir_diff_movimiento(movimiento):
    """
    Genera el diff visible del movimiento a partir de sus snapshots JSON.

    - Compara cada campo con normalización por tipo para evitar falsos positivos.
    - Incluye observación cuando cambió de forma real entre antes y después.
    - Fuerza la presencia del cambio en movimientos de estado.
    """
    anteriores = movimiento.valores_anteriores if isinstance(movimiento.valores_anteriores, dict) else {}
    nuevos = movimiento.valores_nuevos if isinstance(movimiento.valores_nuevos, dict) else {}
    claves = _ordenar_claves_diff(
        clave for clave in set(anteriores.keys()) | set(nuevos.keys())
        if str(clave) not in (CAMPOS_EXCLUIDOS_DIFF - {"observacion"})
    )
    diff = []
    es_afectado_inicial = _es_movimiento_afectado_inicial(movimiento)

    for clave in claves:
        anterior_crudo = anteriores.get(clave)
        nuevo_crudo = nuevos.get(clave)
        anterior = _formatear_valor_campo(clave, anterior_crudo)
        nuevo = _formatear_valor_campo(clave, nuevo_crudo)

        if _valores_equivalentes(clave, anterior_crudo, nuevo_crudo) and not (es_afectado_inicial and clave in nuevos and not anteriores):
            continue

        if es_afectado_inicial and clave in nuevos and not anteriores:
            tipo = "agregado"
        elif clave not in nuevos:
            tipo = "eliminado"
        elif clave not in anteriores:
            tipo = "agregado"
        else:
            tipo = "modificado"

        diff.append({
            "clave": str(clave),
            "campo": _nombre_campo_diff(str(clave)),
            "anterior": anterior,
            "nuevo": nuevo,
            "tipo": tipo,
        })

    if movimiento.tipo_movimiento in TIPOS_MOVIMIENTO_ESTADO:
        estado_anterior = _formatear_estado_pof(movimiento.estado_anterior)
        estado_nuevo = _formatear_estado_pof(movimiento.estado_nuevo)
        if (
            _valor_comparable("estado_pof", movimiento.estado_anterior)
            != _valor_comparable("estado_pof", movimiento.estado_nuevo)
            and not any(item["clave"] == "estado_pof" for item in diff)
        ):
            diff.insert(0, {
                "clave": "estado_pof",
                "campo": "Estado POF",
                "anterior": estado_anterior,
                "nuevo": estado_nuevo,
                "tipo": "modificado",
            })

    return diff


def _obtener_movimientos_queryset():
    return MovimientoCargoPof.objects.select_related(
        "cargo",
        "cargo__localizacion",
        "cargo__localizacion__reunida",
        "cargo__localizacion__proyecto_especial",
        "lote_carga",
        "lote_carga__localizacion",
        "lote_carga__reunida",
        "lote_carga__proyecto_especial",
        "usuario",
        "snapshot_padron",
        "snapshot_padron__localizacion",
    ).order_by("-fecha", "-id")


def _aplicar_filtros_historial(queryset, filtros):
    vista_rapida = filtros.get("vista_rapida")
    if vista_rapida == VISTA_7_DIAS:
        queryset = queryset.filter(fecha__gte=timezone.now() - timedelta(days=7))
    elif vista_rapida == VISTA_30_DIAS:
        queryset = queryset.filter(fecha__gte=timezone.now() - timedelta(days=30))

    if filtros["anio"]:
        queryset = queryset.filter(
            Q(cargo__localizacion__reunida__anio=filtros["anio"])
            | Q(cargo__localizacion__proyecto_especial__anio=filtros["anio"])
        )

    if filtros["nivel"] and filtros["nivel"] != NIVEL_TODOS:
        queryset = queryset.filter(
            cargo__localizacion__reunida__nivel=filtros["nivel"]
        )

    if filtros["cueanexo"]:
        queryset = queryset.filter(
            cargo__localizacion__cueanexo=filtros["cueanexo"]
        )

    if filtros["cuof"]:
        queryset = queryset.filter(
            cargo__localizacion__cuof__iexact=filtros["cuof"]
        )

    if filtros["ceic"]:
        ceic_texto = filtros["ceic"]
        queryset = queryset.filter(
            Q(valores_nuevos__ceic=int(ceic_texto))
            | Q(valores_nuevos__ceic=ceic_texto)
        )

    if filtros.get("cuil"):
        queryset = queryset.filter(usuario__username__contains=filtros["cuil"])

    if filtros["tipo"] and filtros["tipo"] != TIPO_MOVIMIENTO_TODOS:
        queryset = queryset.filter(tipo_movimiento=filtros["tipo"])

    return queryset


def _formatear_valores(valores):
    if not valores:
        return GUION_VACIO

    if not isinstance(valores, dict):
        return str(valores)

    partes = []
    for clave, valor in valores.items():
        if str(clave) in CAMPOS_JSON_AUDITORIA:
            continue
        if isinstance(valor, (dict, list)):
            valor_legible = "datos adicionales"
        elif valor in (None, ""):
            valor_legible = GUION_VACIO
        else:
            valor_legible = str(valor)
        partes.append(f"{str(clave).replace('_', ' ')}: {valor_legible}")

    return "; ".join(partes) if partes else GUION_VACIO


def _obtener_localizacion_movimiento(movimiento):
    cargo = getattr(movimiento, "cargo", None)
    if cargo and getattr(cargo, "localizacion", None):
        return cargo.localizacion
    lote = getattr(movimiento, "lote_carga", None)
    if lote and getattr(lote, "localizacion", None):
        return lote.localizacion
    snapshot = getattr(movimiento, "snapshot_padron", None)
    if snapshot and getattr(snapshot, "localizacion", None):
        return snapshot.localizacion
    return None


def _obtener_cabecera_movimiento(movimiento):
    localizacion = _obtener_localizacion_movimiento(movimiento)
    lote = movimiento.lote_carga
    return (
        (localizacion.reunida if localizacion else None) or (lote.reunida if lote else None),
        (localizacion.proyecto_especial if localizacion else None) or (lote.proyecto_especial if lote else None),
    )


def _resumir_cabecera(reunida, proyecto):
    if reunida:
        return f"POF · {reunida.get_nivel_display()} {reunida.anio}"
    if proyecto:
        return f"Proyecto · {proyecto.nombre}"
    return GUION_VACIO


def _serializar_localizacion_listado(movimiento):
    localizacion = _obtener_localizacion_movimiento(movimiento)
    return {
        "cueanexo": _valor_serializable(getattr(localizacion, "cueanexo", "")),
        "cuof": _valor_serializable(getattr(localizacion, "cuof", "")),
    }


def _serializar_usuario_movimiento(usuario):
    if not usuario:
        return {
            "nombre": GUION_VACIO,
            "cuil": GUION_VACIO,
        }

    nombre = str(usuario).strip()
    identificador = str(
        getattr(usuario, "cuil", "")
        or getattr(usuario, "cuit", "")
        or getattr(usuario, "username", "")
        or ""
    ).strip()
    if identificador and nombre.startswith(identificador):
        nombre_sin_identificador = nombre[len(identificador):].lstrip(" -–—")
        if nombre_sin_identificador:
            nombre = nombre_sin_identificador

    cuil = "".join(caracter for caracter in identificador if caracter.isdigit())

    return {
        "nombre": nombre or GUION_VACIO,
        "cuil": cuil if len(cuil) == 11 else GUION_VACIO,
    }


def _normalizar_observacion_real(valor):
    """
    Limpia la observación textual que se muestra aparte del diff.

    - Oculta placeholders o vacíos que no aportan valor de auditoría.
    - Oculta observaciones técnicas automáticas de cambio de estado.
    - Conserva solo texto final entendible para el usuario.
    """
    texto = str(valor or "").strip()
    if not texto or texto in OBSERVACION_PLACEHOLDERS:
        return ""
    if texto.lower().startswith("cambio de estado:"):
        return ""
    return texto


def _nombre_campo_resumen(clave):
    return NOMBRES_CAMPOS_RESUMEN.get(str(clave), _nombre_campo_diff(str(clave)))


def _referencia_cargo_movimiento(movimiento):
    cargo = getattr(movimiento, "cargo", None)
    anteriores = movimiento.valores_anteriores if isinstance(movimiento.valores_anteriores, dict) else {}
    nuevos = movimiento.valores_nuevos if isinstance(movimiento.valores_nuevos, dict) else {}
    valores = nuevos or anteriores
    ceic = _formatear_valor_campo("ceic", valores.get("ceic") or getattr(cargo, "ceic", ""))
    nombre_cargo = _normalizar_texto_comparable(valores.get("cargo") or getattr(cargo, "cargo", ""))
    if len(nombre_cargo) > 70:
        nombre_cargo = f"{nombre_cargo[:67].rstrip()}..."
    if ceic != GUION_VACIO and nombre_cargo:
        return f"CEIC {ceic} - {nombre_cargo}"
    if ceic != GUION_VACIO:
        return f"CEIC {ceic}"
    if nombre_cargo:
        return nombre_cargo
    return "cargo"


def _partes_diff_resumen(diff, modo):
    partes = []
    for cambio in diff:
        clave = cambio["clave"]
        if modo == "alta" and clave in {"ceic", "cargo", "estado_pof"}:
            continue
        nombre = _nombre_campo_resumen(clave)
        if cambio["tipo"] == "eliminado":
            partes.append(f"{nombre} eliminado: {cambio['anterior']}")
        elif modo == "alta":
            partes.append(f"{nombre}: {cambio['nuevo']}")
        elif clave == "cargo":
            partes.append("Cargo actualizado")
        elif clave == "observacion":
            partes.append(f"{nombre} {cambio['anterior']} {FLECHA_CAMBIO} {cambio['nuevo']}")
        else:
            partes.append(f"{nombre} {cambio['anterior']} {FLECHA_CAMBIO} {cambio['nuevo']}")
    return partes


def _partes_diff_resumen_compacto(diff, modo):
    """
    Reduce el diff a una frase corta apta para la tabla principal.

    - En altas muestra los valores iniciales con ":" porque no existe una
      transición real desde un valor anterior.
    - En modificaciones conserva la flecha para cambios entre valores.
    - Resume cambios de observación sin volcar textos largos en el listado.
    - Limita la longitud para que la fila siga compacta y el detalle quede en la lupa.
    """
    partes = []
    for cambio in diff:
        clave = cambio["clave"]
        if modo == "alta" and clave in {"ceic", "cargo", "estado_pof"}:
            continue

        if clave == "observacion":
            partes.append("Observación modificada")
            continue

        if modo == "alta" and clave in {
            "cantidad",
            "unidad_cantidad",
            "puntos_asignados",
            "total",
        }:
            nombre = {
                "cantidad": "Cantidad",
                "unidad_cantidad": "Unidad",
                "puntos_asignados": "Puntos",
                "total": "Total",
            }[clave]
            partes.append(f"{nombre}: {cambio['nuevo']}")
            continue

        if clave == "cantidad":
            partes.append(f"Cantidad {cambio['anterior']} {FLECHA_CAMBIO} {cambio['nuevo']}")
            continue

        if clave == "total":
            partes.append(f"Total {cambio['anterior']} {FLECHA_CAMBIO} {cambio['nuevo']}")
            continue

        if clave == "estado_pof":
            partes.append(f"Estado {cambio['anterior']} {FLECHA_CAMBIO} {cambio['nuevo']}")
            continue

    return partes[:4]


def _es_movimiento_incremento(movimiento, diff):
    """
    Detecta la modificación especial generada por alta repetida de un CEIC.

    - Requiere tipo `MODIFICACION` con estado estable en Activo.
    - Identifica el patrón actual donde `valores_nuevos` solo persiste cantidad/total.
    - Evita confundirlo con otras modificaciones comunes del cargo.
    """
    if movimiento.tipo_movimiento != MovimientoCargoPof.TipoMovimiento.MODIFICACION:
        return False

    nuevos = movimiento.valores_nuevos if isinstance(movimiento.valores_nuevos, dict) else {}
    claves_nuevas = {str(clave) for clave in nuevos.keys()}
    claves_diff = {item["clave"] for item in diff}
    return (
        claves_nuevas.issubset({"cantidad", "total"})
        and "cantidad" in claves_diff
        and "total" in claves_diff
        and _valor_comparable("estado_pof", movimiento.estado_anterior)
        == _valor_comparable("estado_pof", movimiento.estado_nuevo)
        == "AFECTADO"
    )


def generar_detalle_movimiento(movimiento):
    """
    Construye el resumen corto visible en el listado del historial.

    - Usa verbos específicos según el tipo real de acción auditada.
    - Evita textos genéricos cuando sí existen cambios visibles en el diff.
    - Distingue la alta repetida como incremento de un cargo existente.
    """
    referencia = _referencia_cargo_movimiento(movimiento)
    diff = _construir_diff_movimiento(movimiento)

    if movimiento.tipo_movimiento == MovimientoCargoPof.TipoMovimiento.AFECTADO:
        if _es_movimiento_afectado_inicial(movimiento):
            partes = _partes_diff_resumen(diff, "alta")
            detalle = f"Se añadió el cargo {referencia}."
        else:
            partes = _partes_diff_resumen(diff, "modificacion")
            detalle = f"Se reactivó el cargo {referencia}."
        return f"{detalle} {'; '.join(partes)}." if partes else detalle

    if movimiento.tipo_movimiento == MovimientoCargoPof.TipoMovimiento.DESAFECTADO:
        es_inicial = _es_movimiento_desafectado_inicial(movimiento)
        partes = _partes_diff_resumen(
            diff,
            "alta" if es_inicial else "modificacion",
        )
        detalle = (
            f"Se añadió el cargo {referencia} en estado Desafectado."
            if es_inicial
            else f"Se dio de baja el cargo {referencia}."
        )
        return f"{detalle} {'; '.join(partes)}." if partes else detalle

    partes = _partes_diff_resumen(diff, "modificacion")
    if partes:
        if _es_movimiento_incremento(movimiento, diff):
            return f"Se incrementó el cargo existente {referencia}. {'; '.join(partes)}."
        return f"Se modificó el cargo {referencia}. {'; '.join(partes)}."

    return "Movimiento registrado sin cambios de valores."


def _construir_resumen_visual_movimiento(movimiento):
    """
    Separa el resumen del listado en acción principal y datos breves.

    La estructura evita convertir el detalle en una oración técnica larga y
    permite que el template presente los cambios como elementos visuales.
    """
    referencia = _referencia_cargo_movimiento(movimiento)
    diff = _construir_diff_movimiento(movimiento)

    if movimiento.tipo_movimiento == MovimientoCargoPof.TipoMovimiento.AFECTADO:
        if _es_movimiento_afectado_inicial(movimiento):
            partes = _partes_diff_resumen_compacto(diff, "alta")
            accion = f"Se añadió el cargo {referencia}."
        else:
            partes = _partes_diff_resumen_compacto(diff, "modificacion")
            accion = f"Se reactivó el cargo {referencia}."
        return {"accion": accion, "partes": partes}

    if movimiento.tipo_movimiento == MovimientoCargoPof.TipoMovimiento.DESAFECTADO:
        es_inicial = _es_movimiento_desafectado_inicial(movimiento)
        partes = _partes_diff_resumen_compacto(
            diff,
            "alta" if es_inicial else "modificacion",
        )
        accion = (
            f"Se añadió el cargo {referencia} en estado Desafectado."
            if es_inicial
            else f"Se dio de baja el cargo {referencia}."
        )
        return {"accion": accion, "partes": partes}

    partes = _partes_diff_resumen_compacto(diff, "modificacion")
    if partes:
        accion = (
            f"Se incrementó el cargo existente {referencia}."
            if _es_movimiento_incremento(movimiento, diff)
            else f"Se modificó el cargo {referencia}."
        )
        return {"accion": accion, "partes": partes}

    return {
        "accion": generar_detalle_movimiento(movimiento),
        "partes": [],
    }


def _formatear_resumen_visual_movimiento(resumen):
    """Mantiene el texto plano legacy para consumidores que aún lo utilicen."""
    accion = resumen.get("accion", "")
    partes = resumen.get("partes", [])
    return f"{accion} {'; '.join(partes)}." if partes else accion


def _resumir_detalle_movimiento(movimiento, proyecto):
    """Compatibilidad: devuelve el resumen compacto como texto plano."""
    del proyecto
    return _formatear_resumen_visual_movimiento(
        _construir_resumen_visual_movimiento(movimiento)
    )


def _preparar_movimiento_para_listado(movimiento):
    reunida, proyecto = _obtener_cabecera_movimiento(movimiento)
    movimiento.cabecera_resumen = _resumir_cabecera(reunida, proyecto)
    movimiento.detalle_resumen_visual = _construir_resumen_visual_movimiento(movimiento)
    movimiento.detalle_resumen = _formatear_resumen_visual_movimiento(
        movimiento.detalle_resumen_visual
    )
    movimiento.localizacion_resumen = _serializar_localizacion_listado(movimiento)
    movimiento.usuario_movimiento = _serializar_usuario_movimiento(movimiento.usuario)
    movimiento.tiene_observacion_real = bool(_normalizar_observacion_real(movimiento.observacion))
    movimiento.tipo_movimiento_display = _obtener_tipo_movimiento_display(movimiento)
    movimiento.tipo_movimiento_clase = movimiento.tipo_movimiento.lower()


def _obtener_page_range(paginator, page_obj):
    if hasattr(paginator, "get_elided_page_range"):
        return paginator.get_elided_page_range(
            number=page_obj.number,
            on_each_side=2,
            on_ends=1,
        )
    return paginator.page_range


def obtener_titulo_historial(filtros):
    partes = []

    if filtros["nivel"] and filtros["nivel"] != NIVEL_TODOS:
        partes.append(NIVELES_VALIDOS[filtros["nivel"]])
    elif filtros["nivel"] == NIVEL_TODOS:
        partes.append("Todos los niveles")

    if filtros["anio"]:
        partes.append(filtros["anio"])

    if filtros["cueanexo"]:
        partes.append(f"CUEANEXO {filtros['cueanexo']}")

    if filtros["ceic"]:
        partes.append(f"CEIC {filtros['ceic']}")

    if filtros.get("cuof"):
        partes.append(f"CUOF {filtros['cuof']}")

    if filtros.get("cuil"):
        partes.append(f"CUIL {filtros['cuil']}")

    if filtros.get("tipo") and filtros.get("tipo") != TIPO_MOVIMIENTO_TODOS:
        partes.append(TIPOS_MOVIMIENTO_LABELS[filtros["tipo"]])
    elif filtros.get("tipo") == TIPO_MOVIMIENTO_TODOS:
        partes.append("Todos los eventos")

    if filtros.get("vista_rapida") in {VISTA_7_DIAS, VISTA_30_DIAS}:
        partes.append(VISTAS_RAPIDAS[filtros["vista_rapida"]])

    if partes:
        return "Historial general - " + " / ".join(partes)

    return "Historial general POF"


def obtener_ultimos_movimientos_reunida(anio, nivel, limite=5):
    filtros = {
        "anio": limpiar_texto(anio, 4),
        "nivel": normalizar_nivel(nivel),
        "cueanexo": "",
        "cuof": "",
        "ceic": "",
        "cuil": "",
        "tipo": "",
        "vista_rapida": VISTA_RECIENTES,
    }

    movimientos = _aplicar_filtros_historial(
        _obtener_movimientos_queryset(), filtros
    )[:limite]

    return [
        {
            "fecha": movimiento.fecha.strftime("%d/%m/%Y %H:%M"),
            "usuario": str(movimiento.usuario) if movimiento.usuario else GUION_VACIO,
            "cueanexo": movimiento.cargo.localizacion.cueanexo or GUION_VACIO,
            "ceic": movimiento.cargo.ceic,
            "movimiento": _obtener_tipo_movimiento_display(movimiento),
            "detalle": generar_detalle_movimiento(movimiento),
        }
        for movimiento in movimientos
    ]


def obtener_ultimos_movimientos_proyecto(proyecto_especial_id, limite=5):
    proyecto_id = limpiar_texto(proyecto_especial_id, 20)
    if not proyecto_id.isdigit():
        return []

    movimientos = _obtener_movimientos_queryset().filter(
        cargo__localizacion__proyecto_especial_id=proyecto_id
    )[:limite]

    return [
        {
            "fecha": movimiento.fecha.strftime("%d/%m/%Y %H:%M"),
            "usuario": str(movimiento.usuario) if movimiento.usuario else GUION_VACIO,
            "cueanexo": movimiento.cargo.localizacion.cueanexo or GUION_VACIO,
            "ceic": movimiento.cargo.ceic,
            "movimiento": _obtener_tipo_movimiento_display(movimiento),
            "detalle": generar_detalle_movimiento(movimiento),
        }
        for movimiento in movimientos
    ]


def _serializar_cabecera_detalle(movimiento):
    reunida, proyecto = _obtener_cabecera_movimiento(movimiento)
    if reunida:
        return {
            "tipo": "REUNIDA",
            "descripcion": _resumir_cabecera(reunida, None),
            "anio": _valor_serializable(reunida.anio),
            "nivel": reunida.get_nivel_display(),
            "nombre": GUION_VACIO,
            "resolucion": GUION_VACIO,
        }
    if proyecto:
        return {
            "tipo": "PROYECTO_ESPECIAL",
            "descripcion": _resumir_cabecera(None, proyecto),
            "anio": _valor_serializable(proyecto.anio),
            "nivel": GUION_VACIO,
            "nombre": _valor_serializable(proyecto.nombre),
            "resolucion": _valor_serializable(proyecto.resolucion),
        }
    return {
        "tipo": GUION_VACIO,
        "descripcion": GUION_VACIO,
        "anio": GUION_VACIO,
        "nivel": GUION_VACIO,
        "nombre": GUION_VACIO,
        "resolucion": GUION_VACIO,
    }


def _serializar_localizacion_detalle(localizacion, snapshot):
    return {
        "cueanexo": _valor_serializable(getattr(localizacion, "cueanexo", "")),
        "cue_base": _valor_serializable(getattr(localizacion, "cue_base", "")),
        "anexo_localizacion": _valor_serializable(getattr(localizacion, "anexo_localizacion", "")),
        "cuof": _valor_serializable(getattr(localizacion, "cuof", "")),
        "cui": _valor_serializable(getattr(localizacion, "cui", "")),
        "establecimiento": _valor_serializable(getattr(snapshot, "nombre_establecimiento", "") if snapshot else ""),
        "localidad": _valor_serializable(getattr(snapshot, "localidad", "") if snapshot else ""),
        "departamento": _valor_serializable(getattr(snapshot, "departamento", "") if snapshot else ""),
    }


def _serializar_cargo_actual(cargo):
    """
    Serializa el estado vigente del cargo para el modal de historial.

    - Expone solo los datos actuales del cargo al momento de abrir la lupa.
    - Incluye la observación actual solo cuando existe texto real.
    - Mantiene separada la observación vigente del cargo respecto de la observación del movimiento.
    """
    return {
        "id": _formatear_valor_campo("id", cargo.id),
        "ceic": _formatear_valor_campo("ceic", cargo.ceic),
        "cargo": _valor_serializable(cargo.cargo),
        "cantidad": _formatear_valor_campo("cantidad", cargo.cantidad),
        "unidad_cantidad": cargo.get_unidad_cantidad_display(),
        "puntos_asignados": _formatear_valor_campo("puntos_asignados", cargo.puntos_asignados),
        "total": _formatear_valor_campo("total", cargo.total),
        "estado_pof": cargo.get_estado_pof_display(),
        "observacion_actual": _normalizar_observacion_comparable(cargo.observacion),
    }


def _normalizar_cargo_ids_historial(valores):
    if not valores:
        raise ValidationError({"cargo_ids": ["Debe indicar al menos un cargo."]})

    cargo_ids = set()
    for valor in valores:
        texto_valor = str(valor or "").strip()
        if not texto_valor.isdigit() or int(texto_valor) <= 0:
            raise ValidationError({
                "cargo_ids": ["Los identificadores de cargo deben ser enteros positivos."],
            })
        cargo_ids.add(int(texto_valor))

    if len(cargo_ids) > MAX_CARGOS_HISTORIAL:
        raise ValidationError({
            "cargo_ids": [f"No se pueden consultar más de {MAX_CARGOS_HISTORIAL} cargos."],
        })
    return sorted(cargo_ids)


def _formatear_cantidad_historial(valor):
    numero = _normalizar_decimal_comparable(valor)
    if numero is None:
        return GUION_VACIO
    if numero == numero.to_integral_value():
        return str(int(numero))
    return format(numero.normalize(), "f")


def _formatear_variacion_cantidad(valor):
    texto_variacion = _formatear_cantidad_historial(valor)
    if texto_variacion == GUION_VACIO:
        return texto_variacion
    return f"+{texto_variacion}" if valor > 0 else texto_variacion


def _validar_cargos_historial(cargos, exigir_afectados=True):
    """
    Valida que los cargos consultados pertenezcan a una misma unidad operativa.

    - Para historial de cantidad exige cargos afectados, porque la consolidación de cantidad
      se apoya en cargos vigentes.
    - Para historial de Estado POF permite cargos desafectados, porque justamente se consulta
      la trazabilidad de afectación/desafectación.
    - Evita mezclar cargos de distintas Reunidas o Proyectos Especiales.
    """
    reunida_ids = {
        cargo.localizacion.reunida_id
        for cargo in cargos
        if cargo.localizacion.reunida_id
    }
    proyecto_especial_ids = {
        cargo.localizacion.proyecto_especial_id
        for cargo in cargos
        if cargo.localizacion.proyecto_especial_id
    }

    pertenecen_reunida_normal = (
        len(reunida_ids) == 1
        and not proyecto_especial_ids
        and all(cargo.localizacion.reunida_id for cargo in cargos)
    )

    pertenecen_proyecto_especial = (
        len(proyecto_especial_ids) == 1
        and not reunida_ids
        and all(cargo.localizacion.proyecto_especial_id for cargo in cargos)
    )

    if not (pertenecen_reunida_normal or pertenecen_proyecto_especial):
        raise ValidationError({
            "cargo_ids": [
                "Los cargos deben pertenecer a una misma POF "
                "o a un mismo Proyecto Especial."
            ],
        })

    if len(cargos) <= 1:
        return

    claves = {
        obtener_clave_consolidacion_cargo(cargo)
        for cargo in cargos
    }

    if len(claves) != 1:
        raise ValidationError({
            "cargo_ids": [
                "Los cargos indicados no pertenecen a una misma fila consolidada."
            ],
        })

    if exigir_afectados and any(
        cargo.estado_pof != CargoPof.EstadoPof.AFECTADO
        for cargo in cargos
    ):
        raise ValidationError({
            "cargo_ids": [
                "Los cargos indicados no pertenecen a una misma fila consolidada afectada."
            ],
        })


def _serializar_movimiento_cantidad(movimiento):
    cantidad_anterior, cantidad_nueva = _cantidades_comparables_movimiento(movimiento)
    variacion = cantidad_nueva - cantidad_anterior
    usuario = _serializar_usuario_movimiento(movimiento.usuario)
    return {
        "id": movimiento.id,
        "fecha": _valor_serializable(movimiento.fecha),
        "cantidad_anterior": _formatear_cantidad_historial(cantidad_anterior),
        "cantidad_nueva": _formatear_cantidad_historial(cantidad_nueva),
        "variacion": _formatear_variacion_cantidad(variacion),
        "usuario": usuario["nombre"],
        "observacion": _normalizar_observacion_real(movimiento.observacion),
    }


def _observacion_inicial_movimiento(movimiento):
    """
    Devuelve la observacion con la que nacio el cargo, si el movimiento la conserva.

    La fuente canonica es el snapshot `valores_nuevos` del movimiento inicial;
    no usa `movimiento.observacion` como fallback porque ese campo tambien puede
    describir el motivo del movimiento y no necesariamente el valor del cargo.
    """
    if movimiento.tipo_movimiento not in {
        MovimientoCargoPof.TipoMovimiento.AFECTADO,
        MovimientoCargoPof.TipoMovimiento.DESAFECTADO,
    }:
        return ""
    nuevos = movimiento.valores_nuevos
    if not isinstance(nuevos, dict) or "observacion" not in nuevos:
        return ""
    return _normalizar_observacion_comparable(nuevos.get("observacion"))


def _serializar_evento_observacion_inicial(movimiento):
    observacion = _observacion_inicial_movimiento(movimiento)
    usuario = _serializar_usuario_movimiento(movimiento.usuario)
    return {
        "id": movimiento.id,
        "fecha": _valor_serializable(movimiento.fecha),
        "tipo_evento": "inicial",
        "label": "Observación inicial",
        "resumen": _valor_serializable(observacion),
        "valor_inicial": _valor_serializable(observacion),
        "usuario": usuario["nombre"],
    }


def _serializar_movimiento_observacion(movimiento):
    observacion_anterior, observacion_nueva = _observaciones_comparables_movimiento(
        movimiento
    )
    usuario = _serializar_usuario_movimiento(movimiento.usuario)
    return {
        "id": movimiento.id,
        "fecha": _valor_serializable(movimiento.fecha),
        "tipo_evento": "modificacion",
        "label": "Observación modificada",
        "resumen": _valor_serializable(observacion_nueva),
        "observacion_anterior": _valor_serializable(observacion_anterior),
        "observacion_nueva": _valor_serializable(observacion_nueva),
        "usuario": usuario["nombre"],
    }


def _serializar_movimiento_estado(movimiento):
    """
    Serializa un cambio real de Estado POF para el modal específico.

    - Expone únicamente datos necesarios para la interfaz.
    - Usa las funciones existentes para fechas, estados, usuario y observación.
    - No expone snapshots JSON internos ni información innecesaria.
    """
    usuario = _serializar_usuario_movimiento(movimiento.usuario)

    return {
        "id": movimiento.id,
        "fecha": _valor_serializable(movimiento.fecha),
        "estado_anterior": _formatear_estado_pof(
            movimiento.estado_anterior
        ),
        "estado_nuevo": _formatear_estado_pof(
            movimiento.estado_nuevo
        ),
        "usuario": usuario["nombre"],
        "observacion": _normalizar_observacion_real(
            movimiento.observacion
        ),
    }


def obtener_historial_cantidad_cargos_pof(cargo_ids_recibidos):
    cargo_ids = _normalizar_cargo_ids_historial(cargo_ids_recibidos)
    cargos = list(
        CargoPof.objects.select_related(
            "localizacion",
            "localizacion__reunida",
            "localizacion__proyecto_especial",
        ).filter(pk__in=cargo_ids).order_by("id")
    )
    if len(cargos) != len(cargo_ids):
        raise CargoPof.DoesNotExist

    _validar_cargos_historial(cargos, exigir_afectados=True)
    movimientos_por_cargo = {cargo.id: [] for cargo in cargos}
    movimientos = MovimientoCargoPof.objects.select_related("usuario").filter(
        cargo_id__in=cargo_ids,
        tipo_movimiento=MovimientoCargoPof.TipoMovimiento.MODIFICACION,
    ).order_by("cargo_id", "fecha", "id")

    for movimiento in movimientos:
        if es_cambio_real_cantidad_movimiento(movimiento):
            movimientos_por_cargo[movimiento.cargo_id].append(
                _serializar_movimiento_cantidad(movimiento)
            )

    cargo_referencia = cargos[0]
    localizacion = cargo_referencia.localizacion
    cantidad_actual = sum((cargo.cantidad for cargo in cargos), Decimal("0"))
    cargos_serializados = [
        {
            "id": cargo.id,
            "ceic": _formatear_cantidad_historial(cargo.ceic),
            "cargo": _valor_serializable(cargo.cargo),
            "cantidad_actual": _formatear_cantidad_historial(cargo.cantidad),
            "movimientos": movimientos_por_cargo[cargo.id],
        }
        for cargo in cargos
    ]

    return {
        "cargo": {
            "id": cargo_referencia.id if len(cargos) == 1 else None,
            "cargo_ids": cargo_ids,
            "ceic": _formatear_cantidad_historial(cargo_referencia.ceic),
            "cargo": _valor_serializable(cargo_referencia.cargo),
            "cueanexo": _valor_serializable(localizacion.cueanexo),
            "cuof": _valor_serializable(localizacion.cuof),
            "cantidad_actual": _formatear_cantidad_historial(cantidad_actual),
        },
        "modificado": any(
            cargo["movimientos"] for cargo in cargos_serializados
        ),
        "cargos": cargos_serializados,
    }


def obtener_historial_observacion_cargos_pof(cargo_ids_recibidos):
    """
    Devuelve la linea de tiempo completa de observacion de uno o varios cargos.

    - Incluye el valor inicial cuando el primer movimiento del cargo conserva una
      observacion real en su snapshot `valores_nuevos`.
    - Incluye cada modificacion real posterior con Antes/Despues.
    - Cada cargo se devuelve del evento mas reciente al mas antiguo.
    - No inventa eventos iniciales vacios ni modifica la auditoria existente.
    """
    cargo_ids = _normalizar_cargo_ids_historial(cargo_ids_recibidos)
    cargos = list(
        CargoPof.objects.select_related(
            "localizacion",
            "localizacion__reunida",
            "localizacion__proyecto_especial",
        ).filter(pk__in=cargo_ids).order_by("id")
    )
    if len(cargos) != len(cargo_ids):
        raise CargoPof.DoesNotExist

    _validar_cargos_historial(cargos, exigir_afectados=False)
    movimientos_por_cargo = {cargo.id: [] for cargo in cargos}
    movimiento_inicial_por_cargo = {}

    movimientos = MovimientoCargoPof.objects.select_related("usuario").filter(
        cargo_id__in=cargo_ids,
    ).order_by("cargo_id", "fecha", "id")

    for movimiento in movimientos:
        if (
            movimiento.cargo_id not in movimiento_inicial_por_cargo
            and movimiento.tipo_movimiento
            in {
                MovimientoCargoPof.TipoMovimiento.AFECTADO,
                MovimientoCargoPof.TipoMovimiento.DESAFECTADO,
            }
        ):
            movimiento_inicial_por_cargo[movimiento.cargo_id] = movimiento

        if (
            movimiento.tipo_movimiento
            == MovimientoCargoPof.TipoMovimiento.MODIFICACION
            and es_cambio_real_observacion_movimiento(movimiento)
        ):
            movimientos_por_cargo[movimiento.cargo_id].append(
                _serializar_movimiento_observacion(movimiento)
            )

    for cargo in cargos:
        movimiento_inicial = movimiento_inicial_por_cargo.get(cargo.id)
        if movimiento_inicial and _observacion_inicial_movimiento(movimiento_inicial):
            movimientos_por_cargo[cargo.id].insert(
                0,
                _serializar_evento_observacion_inicial(movimiento_inicial),
            )
        movimientos_por_cargo[cargo.id].reverse()

    cargo_referencia = cargos[0]
    localizacion = cargo_referencia.localizacion
    observaciones_actuales = []
    for cargo in cargos:
        observacion = _normalizar_observacion_comparable(cargo.observacion)
        if observacion and observacion not in observaciones_actuales:
            observaciones_actuales.append(observacion)

    cargos_serializados = [
        {
            "id": cargo.id,
            "ceic": _formatear_cantidad_historial(cargo.ceic),
            "cargo": _valor_serializable(cargo.cargo),
            "observacion_actual": _valor_serializable(
                _normalizar_observacion_comparable(cargo.observacion)
            ),
            "movimientos": movimientos_por_cargo[cargo.id],
        }
        for cargo in cargos
    ]

    return {
        "cargo": {
            "id": cargo_referencia.id if len(cargos) == 1 else None,
            "cargo_ids": cargo_ids,
            "ceic": _formatear_cantidad_historial(cargo_referencia.ceic),
            "cargo": _valor_serializable(cargo_referencia.cargo),
            "cueanexo": _valor_serializable(localizacion.cueanexo),
            "cuof": _valor_serializable(localizacion.cuof),
            "observacion_actual": _valor_serializable(
                " | ".join(observaciones_actuales)
            ),
        },
        "modificado": any(
            cargo["movimientos"] for cargo in cargos_serializados
        ),
        "cargos": cargos_serializados,
    }


def obtener_historial_estado_cargos_pof(cargo_ids_recibidos):
    """
    Obtiene el historial real de cambios entre Afectado y Desafectado.

    - Acepta uno o varios cargo_ids de una misma fila consolidada.
    - Valida existencia y coherencia antes de consultar movimientos.
    - Devuelve movimientos ordenados cronológicamente por cargo físico.
    - No realiza escrituras ni modifica el historial existente.
    """
    cargo_ids = _normalizar_cargo_ids_historial(cargo_ids_recibidos)

    cargos = list(
        CargoPof.objects.select_related(
            "localizacion",
            "localizacion__reunida",
            "localizacion__proyecto_especial",
        )
        .filter(pk__in=cargo_ids)
        .order_by("id")
    )

    if len(cargos) != len(cargo_ids):
        raise CargoPof.DoesNotExist

    _validar_cargos_historial(cargos, exigir_afectados=False)

    movimientos_por_cargo = {
        cargo.id: []
        for cargo in cargos
    }

    movimientos = (
        MovimientoCargoPof.objects
        .select_related("usuario")
        .filter(
            cargo_id__in=cargo_ids,
            tipo_movimiento__in=TIPOS_MOVIMIENTO_ESTADO,
        )
        .order_by("cargo_id", "fecha", "id")
    )

    for movimiento in movimientos:
        if es_cambio_real_estado_movimiento(movimiento):
            movimientos_por_cargo[movimiento.cargo_id].append(
                _serializar_movimiento_estado(movimiento)
            )

    cargo_referencia = cargos[0]
    localizacion = cargo_referencia.localizacion

    cargos_serializados = [
        {
            "id": cargo.id,
            "ceic": _formatear_cantidad_historial(cargo.ceic),
            "cargo": _valor_serializable(cargo.cargo),
            "estado_actual": _formatear_estado_pof(
                cargo.estado_pof
            ),
            "movimientos": movimientos_por_cargo[cargo.id],
        }
        for cargo in cargos
    ]

    return {
        "cargo": {
            "id": (
                cargo_referencia.id
                if len(cargos) == 1
                else None
            ),
            "cargo_ids": cargo_ids,
            "ceic": _formatear_cantidad_historial(
                cargo_referencia.ceic
            ),
            "cargo": _valor_serializable(
                cargo_referencia.cargo
            ),
            "cueanexo": _valor_serializable(
                localizacion.cueanexo
            ),
            "cuof": _valor_serializable(
                localizacion.cuof
            ),
            "estado_actual": _formatear_estado_pof(
                cargo_referencia.estado_pof
            ),
        },
        "modificado": any(
            cargo["movimientos"]
            for cargo in cargos_serializados
        ),
        "cargos": cargos_serializados,
    }


def _serializar_movimiento_historial_contextual(movimiento):
    """Serializa un movimiento completo para los historiales contextuales del modal."""
    _preparar_movimiento_para_listado(movimiento)
    cargo = movimiento.cargo
    observacion = _normalizar_observacion_real(movimiento.observacion)
    return {
        "id": movimiento.id,
        "fecha": _valor_serializable(movimiento.fecha),
        "tipo_movimiento": movimiento.tipo_movimiento,
        "tipo_movimiento_display": movimiento.tipo_movimiento_display,
        "tipo_movimiento_clase": movimiento.tipo_movimiento_clase,
        "detalle": movimiento.detalle_resumen,
        "detalle_visual": movimiento.detalle_resumen_visual,
        "usuario": movimiento.usuario_movimiento,
        "observacion": observacion,
        "diff": _construir_diff_movimiento(movimiento),
        "cargo": {
            "id": cargo.id,
            "ceic": _formatear_valor_campo("ceic", cargo.ceic),
            "cargo": _valor_serializable(cargo.cargo),
        },
    }


def _serializar_contexto_localizacion_historial(localizacion):
    reunida = localizacion.reunida
    proyecto = localizacion.proyecto_especial
    cueanexo = str(localizacion.cueanexo or "").strip()
    cuof = str(localizacion.cuof or "").strip()
    usar_cuof = bool(proyecto) or not cueanexo
    return {
        "id": localizacion.id,
        "cueanexo": _valor_serializable(cueanexo),
        "cuof": _valor_serializable(cuof),
        "tipo_identidad": "CUOF" if usar_cuof else "CUEANEXO",
        "identidad": _valor_serializable(cuof if usar_cuof else cueanexo),
        "cabecera": _resumir_cabecera(reunida, proyecto),
        "tipo_cabecera": (
            "REUNIDA"
            if reunida
            else "PROYECTO_ESPECIAL"
            if proyecto
            else ""
        ),
    }


def _cabecera_ciclo_cargo(cargo):
    localizacion = cargo.localizacion
    if bool(localizacion.reunida) == bool(localizacion.proyecto_especial):
        return None, ""
    if localizacion.reunida:
        return localizacion.reunida, "REUNIDA"
    return localizacion.proyecto_especial, "PROYECTO_ESPECIAL"


def _serializar_estado_inicial_ciclo(cargo, movimientos):
    """Usa exclusivamente la foto propia del ciclo, nunca el estado del padre."""
    campos = NOMBRES_CAMPOS_DIFF
    if not movimientos:
        valores = {campo: getattr(cargo, campo) for campo in campos}
    else:
        primero = movimientos[-1]  # El queryset conserva -fecha, -id.
        anteriores = primero.valores_anteriores
        nuevos = primero.valores_nuevos
        if isinstance(anteriores, dict) and anteriores:
            valores = anteriores
        elif (
            not cargo.cargo_origen_id
            and (
                _es_movimiento_afectado_inicial(primero)
                or _es_movimiento_desafectado_inicial(primero)
            )
            and isinstance(nuevos, dict)
        ):
            valores = nuevos
        else:
            valores = {}

    return {
        "heredado": bool(cargo.cargo_origen_id),
        "fecha": _valor_serializable(cargo.creado_en),
        "campos": [
            {
                "campo": campo,
                "nombre": NOMBRES_CAMPOS_DIFF[campo],
                "valor": _formatear_valor_campo(campo, valores[campo]),
            }
            for campo in NOMBRES_CAMPOS_DIFF
            if campo in valores
        ],
    }


def _serializar_observaciones_ciclo(cargo, movimientos):
    """Reutiliza los eventos de observación reales del cargo físico del ciclo."""
    eventos = [
        _serializar_movimiento_observacion(movimiento)
        for movimiento in movimientos
        if (
            movimiento.tipo_movimiento == MovimientoCargoPof.TipoMovimiento.MODIFICACION
            and es_cambio_real_observacion_movimiento(movimiento)
        )
    ]
    inicial = next((
        movimiento for movimiento in reversed(movimientos)
        if movimiento.tipo_movimiento in {
            MovimientoCargoPof.TipoMovimiento.AFECTADO,
            MovimientoCargoPof.TipoMovimiento.DESAFECTADO,
        }
    ), None)
    if inicial and _observacion_inicial_movimiento(inicial):
        eventos.append(_serializar_evento_observacion_inicial(inicial))
    datos_cargo = _serializar_cargo_actual(cargo)
    return {
        "cargo": datos_cargo,
        "cargos": [{**datos_cargo, "movimientos": eventos}],
    }


def _obtener_cadena_historica_cargo_pof(cargo_id):
    """Recorrido único y seguro hacia atrás, exclusivamente por cargo_origen."""
    cargos_queryset = CargoPof.objects.select_related(
        "localizacion",
        "localizacion__reunida",
        "localizacion__proyecto_especial",
    )
    cargo = cargos_queryset.get(pk=cargo_id)
    cadena = [cargo]
    visitados = {cargo.id}
    advertencia = ""
    actual = cargo

    while actual.cargo_origen_id:
        origen_id = actual.cargo_origen_id
        if origen_id in visitados:
            advertencia = "Se interrumpió la continuidad histórica: la cadena de origen contiene un ciclo."
            break
        try:
            origen = cargos_queryset.get(pk=origen_id)
        except CargoPof.DoesNotExist:
            advertencia = "Se interrumpió la continuidad histórica: no existe el cargo de origen."
            break

        cabecera_actual, tipo_actual = _cabecera_ciclo_cargo(actual)
        cabecera_origen, tipo_origen = _cabecera_ciclo_cargo(origen)
        if (
            not cabecera_actual or not cabecera_origen
            or tipo_actual != tipo_origen
            or cabecera_origen.anio >= cabecera_actual.anio
        ):
            advertencia = "Se interrumpió la continuidad histórica: el origen no pertenece a un ciclo anterior compatible."
            break

        visitados.add(origen.id)
        cadena.append(origen)
        actual = origen

    return cadena, advertencia


def obtener_historial_completo_cargo_pof(cargo_id):
    """Consulta los ciclos enlazados por cargo_origen, del más reciente al más antiguo."""
    cadena, advertencia = _obtener_cadena_historica_cargo_pof(cargo_id)
    visitados = {item.id for item in cadena}
    movimientos_por_cargo = {item.id: [] for item in cadena}
    for movimiento in _obtener_movimientos_queryset().filter(cargo_id__in=visitados):
        movimientos_por_cargo[movimiento.cargo_id].append(movimiento)

    ciclos = []
    for item in cadena:
        cabecera, _ = _cabecera_ciclo_cargo(item)
        movimientos = movimientos_por_cargo[item.id]
        ciclos.append({
            "anio": cabecera.anio if cabecera else None,
            "cargo_id": item.id,
            "cargo_origen_id": item.cargo_origen_id,
            "cargo": _serializar_cargo_actual(item),
            "localizacion": _serializar_contexto_localizacion_historial(item.localizacion),
            "estado_inicial": _serializar_estado_inicial_ciclo(item, movimientos),
            "movimientos": [
                _serializar_movimiento_historial_contextual(movimiento)
                for movimiento in movimientos
            ],
            "observaciones": _serializar_observaciones_ciclo(item, movimientos),
        })

    # El contrato global sigue representando siempre el cargo abierto/ciclo actual.
    ciclo_actual = ciclos[0]
    return {
        "cargo": ciclo_actual["cargo"],
        "localizacion": ciclo_actual["localizacion"],
        "movimientos": ciclo_actual["movimientos"],
        "ciclos": ciclos,
        "advertencia_continuidad": advertencia,
    }


def _obtener_historial_contextual_por_ciclos(cargo_id, localizacion_id, consultar_localizacion):
    cargo_id = _normalizar_cargo_ids_historial([cargo_id])[0]
    cadena, advertencia = _obtener_cadena_historica_cargo_pof(cargo_id)
    if cadena[0].localizacion.id != localizacion_id:
        raise ValidationError({
            "cargo_id": ["El cargo indicado no pertenece a la localización solicitada."],
        })

    ciclos = []
    historial_actual = {}
    for indice, item in enumerate(cadena):
        # La identidad sólo se resuelve dentro de la localización/cabecera del ciclo.
        historial_ciclo = consultar_localizacion(item.localizacion.id)
        if indice == 0:
            historial_actual = historial_ciclo
        cabecera, _ = _cabecera_ciclo_cargo(item)
        ciclos.append({
            **historial_ciclo,
            "anio": cabecera.anio if cabecera else None,
            "cargo_id": item.id,
            "localizacion": _serializar_contexto_localizacion_historial(item.localizacion),
        })

    return {
        **historial_actual,
        "ciclos": ciclos,
        "advertencia_continuidad": advertencia,
    }


def obtener_historial_zona_cargo_pof(localizacion_id, cargo_id):
    """Consulta los snapshots originales de cada localización de la cadena."""
    return _obtener_historial_contextual_por_ciclos(
        cargo_id, localizacion_id, obtener_historial_zona_localizacion,
    )


def obtener_historial_localizacion_cargos_pof(localizacion_id, *, cargo_id=None):
    """
    Devuelve movimientos de todos los cargos de la identidad de la localizacion.

    - Con cargo_id, consulta cada ciclo de la cadena explícita del cargo abierto.
    - Sin cargo_id, mantiene la consulta de una sola cabecera/localización.
    - Reunida usa CUEANEXO como identidad y agrupa sus distintos CUOF.
    - Proyecto Especial usa siempre CUOF, aunque conserve CUEANEXO de Padron.
    - Nunca mezcla la misma identidad existente en otra POF, proyecto o ciclo.
    """
    if cargo_id is not None:
        return _obtener_historial_contextual_por_ciclos(
            cargo_id, localizacion_id, obtener_historial_localizacion_cargos_pof,
        )

    localizacion = LocalizacionPof.objects.select_related(
        "reunida",
        "proyecto_especial",
    ).get(pk=localizacion_id)
    movimientos = _obtener_movimientos_queryset()
    cueanexo = str(localizacion.cueanexo or "").strip()
    cuof = str(localizacion.cuof or "").strip()

    if localizacion.reunida_id:
        movimientos = movimientos.filter(
            cargo__localizacion__reunida_id=localizacion.reunida_id
        )
        if cueanexo:
            movimientos = movimientos.filter(
                cargo__localizacion__cueanexo=cueanexo
            )
        else:
            movimientos = movimientos.filter(
                cargo__localizacion__cuof__iexact=cuof
            )
    else:
        movimientos = movimientos.filter(
            cargo__localizacion__proyecto_especial_id=localizacion.proyecto_especial_id
        )
        movimientos = movimientos.filter(
            cargo__localizacion__cuof__iexact=cuof
        )

    return {
        "localizacion": _serializar_contexto_localizacion_historial(localizacion),
        "movimientos": [
            _serializar_movimiento_historial_contextual(movimiento)
            for movimiento in movimientos
        ],
    }


def obtener_detalle_movimiento_pof(movimiento_id):
    movimiento = MovimientoCargoPof.objects.select_related(
        "cargo",
        "cargo__localizacion",
        "cargo__localizacion__reunida",
        "cargo__localizacion__proyecto_especial",
        "lote_carga",
        "lote_carga__localizacion",
        "lote_carga__reunida",
        "lote_carga__proyecto_especial",
        "usuario",
        "snapshot_padron",
        "snapshot_padron__localizacion",
    ).get(pk=movimiento_id)

    cargo = movimiento.cargo
    localizacion = cargo.localizacion
    snapshot = movimiento.snapshot_padron
    cabecera = _serializar_cabecera_detalle(movimiento)
    usuario_movimiento = _serializar_usuario_movimiento(movimiento.usuario)

    return {
        "id": movimiento.id,
        "fecha": _valor_serializable(movimiento.fecha),
        "usuario": usuario_movimiento["nombre"],
        "usuario_movimiento": usuario_movimiento,
        "tipo_movimiento": movimiento.tipo_movimiento,
        "tipo_movimiento_display": _obtener_tipo_movimiento_display(movimiento),
        "estado_anterior": _formatear_estado_pof(movimiento.estado_anterior),
        "estado_nuevo": _formatear_estado_pof(movimiento.estado_nuevo),
        "observacion": _valor_serializable(_normalizar_observacion_real(movimiento.observacion)),
        "cabecera": cabecera,
        "cabecera_resumen": cabecera["descripcion"],
        "localizacion": _serializar_localizacion_detalle(localizacion, snapshot),
        "cargo_actual": _serializar_cargo_actual(cargo),
        "valores_anteriores": _serializar_mapa(movimiento.valores_anteriores),
        "valores_nuevos": _serializar_mapa(movimiento.valores_nuevos),
        "diff": _construir_diff_movimiento(movimiento),
    }



def _evento_cargo_desde_movimiento(movimiento):
    _preparar_movimiento_para_listado(movimiento)
    return {
        "id": movimiento.id,
        "fecha": movimiento.fecha,
        "usuario_movimiento": movimiento.usuario_movimiento,
        "cabecera_resumen": movimiento.cabecera_resumen,
        "localizacion_resumen": {
            **movimiento.localizacion_resumen,
            "cue": (
                str(movimiento.localizacion_resumen.get("cueanexo") or "")[:7]
                if str(movimiento.localizacion_resumen.get("cueanexo") or "").isdigit()
                and len(str(movimiento.localizacion_resumen.get("cueanexo") or "")) == 9
                else GUION_VACIO
            ),
        },
        "tipo_movimiento": movimiento.tipo_movimiento,
        "tipo_movimiento_display": movimiento.tipo_movimiento_display,
        "tipo_movimiento_clase": movimiento.tipo_movimiento_clase,
        "detalle_resumen_visual": movimiento.detalle_resumen_visual,
        "tiene_observacion_real": movimiento.tiene_observacion_real,
        "permite_detalle": True,
    }


def _tipo_evento_habilitado(filtros, tipo_evento):
    tipo = filtros.get("tipo")
    return not tipo or tipo == TIPO_MOVIMIENTO_TODOS or tipo == tipo_evento


def _umbral_vista_rapida(filtros):
    vista = filtros.get("vista_rapida")
    if vista == VISTA_7_DIAS:
        return timezone.now() - timedelta(days=7)
    if vista == VISTA_30_DIAS:
        return timezone.now() - timedelta(days=30)
    return None


def _usuario_coincide_cuil(usuario, cuil_busqueda):
    if not cuil_busqueda:
        return True
    identificador = str(
        getattr(usuario, "cuil", "")
        or getattr(usuario, "cuit", "")
        or getattr(usuario, "username", "")
        or ""
    )
    digitos = "".join(caracter for caracter in identificador if caracter.isdigit())
    return str(cuil_busqueda) in digitos


def _asignacion_zona_snapshot_historial(snapshot):
    return {
        "tipo": str(snapshot.zona_educativa_tipo or "").strip().upper(),
        "zona": " ".join(str(snapshot.zona_educativa or "").strip().split()),
        "puntos": snapshot.puntos_zona_educativa,
    }


def _clave_asignacion_zona_historial(asignacion):
    return (
        str(asignacion.get("tipo") or "").strip().upper(),
        str(asignacion.get("zona") or "").strip().casefold(),
        asignacion.get("puntos"),
    )


def _descripcion_zona_historial(asignacion):
    if not asignacion or not asignacion.get("zona"):
        return "Sin Zona Educativa"
    puntos = asignacion.get("puntos")
    return (
        f"{asignacion['zona']} · {puntos} puntos"
        if puntos not in (None, "")
        else str(asignacion["zona"])
    )


def _identidad_zona_historial(localizacion):
    if localizacion.reunida_id:
        anio = localizacion.reunida.anio
    elif localizacion.proyecto_especial_id:
        anio = localizacion.proyecto_especial.anio
    else:
        return None

    cueanexo = str(localizacion.cueanexo or "").strip()
    if cueanexo.isdigit() and len(cueanexo) == 9:
        return ("CUEANEXO", int(anio), cueanexo)

    cuof = str(localizacion.cuof or "").strip()
    if cuof:
        return ("CUOF", int(anio), cuof)
    return None


def _agregar_detalle_evento_historial(evento, secciones, *, diff=None, observacion=""):
    """Expone el detalle de Zona/Anexo usando los datos del evento ya autorizado."""
    evento["permite_detalle"] = True
    evento["detalle_evento"] = {
        "id": evento["id"],
        "fecha": _valor_serializable(evento["fecha"]),
        "usuario_movimiento": evento["usuario_movimiento"],
        "cabecera_resumen": evento["cabecera_resumen"],
        "tipo_movimiento_display": evento["tipo_movimiento_display"],
        "es_evento_general": True,
        "resumen": evento["detalle_resumen_visual"]["accion"],
        "secciones": [
            {
                "titulo": titulo,
                "campos": [
                    [etiqueta, _valor_serializable(valor)]
                    for etiqueta, valor in campos
                ],
            }
            for titulo, campos in secciones
        ],
        "diff": diff or [],
        "observacion": observacion,
    }
    return evento


def _construir_evento_zona_historial(snapshot, anterior, nuevo):
    localizacion = snapshot.localizacion
    cueanexo = str(localizacion.cueanexo or "").strip()
    cuof = str(localizacion.cuof or "").strip()
    cue = cueanexo[:7] if cueanexo.isdigit() and len(cueanexo) == 9 else GUION_VACIO
    observacion = str(
        getattr(snapshot, "observacion_zona_educativa", "") or ""
    ).strip()

    if not anterior.get("zona") and nuevo.get("zona"):
        accion = f"Se asignó la Zona Educativa {_descripcion_zona_historial(nuevo)}."
    elif anterior.get("zona") and not nuevo.get("zona"):
        accion = "Se quitó la Zona Educativa."
    else:
        accion = "Se modificó la Zona Educativa."

    partes = []
    if anterior.get("tipo") != nuevo.get("tipo"):
        partes.append(
            f"Tipo: {anterior.get('tipo') or GUION_VACIO} {FLECHA_CAMBIO} "
            f"{nuevo.get('tipo') or GUION_VACIO}"
        )
    if anterior.get("zona") != nuevo.get("zona"):
        partes.append(
            f"Zona: {anterior.get('zona') or GUION_VACIO} {FLECHA_CAMBIO} "
            f"{nuevo.get('zona') or GUION_VACIO}"
        )
    if anterior.get("puntos") != nuevo.get("puntos"):
        partes.append(
            f"Puntos: {_valor_serializable(anterior.get('puntos'))} {FLECHA_CAMBIO} "
            f"{_valor_serializable(nuevo.get('puntos'))}"
        )
    if observacion:
        partes.append(f"Observación: {observacion}")

    evento = {
        "id": f"zona-{snapshot.id}",
        "fecha": snapshot.fecha_snapshot,
        "usuario_movimiento": _serializar_usuario_movimiento(snapshot.usuario),
        "cabecera_resumen": _resumir_cabecera(
            localizacion.reunida if localizacion.reunida_id else None,
            localizacion.proyecto_especial if localizacion.proyecto_especial_id else None,
        ),
        "localizacion_resumen": {
            "cue": cue,
            "cueanexo": cueanexo or GUION_VACIO,
            "cuof": cuof or GUION_VACIO,
        },
        "tipo_movimiento": TIPO_EVENTO_ZONA_EDUCATIVA,
        "tipo_movimiento_display": TIPOS_MOVIMIENTO_LABELS[TIPO_EVENTO_ZONA_EDUCATIVA],
        "tipo_movimiento_clase": "modificacion",
        "detalle_resumen_visual": {
            "accion": accion,
            "partes": partes,
        },
        "tiene_observacion_real": bool(observacion),
    }

    diff = [
        {
            "clave": campo,
            "campo": etiqueta,
            "anterior": _valor_serializable(anterior.get(campo)),
            "nuevo": _valor_serializable(nuevo.get(campo)),
        }
        for campo, etiqueta in (
            ("tipo", "Tipo de Zona"),
            ("zona", "Zona Educativa"),
            ("puntos", "Puntos Zona"),
        )
        if anterior.get(campo) != nuevo.get(campo)
    ]
    return _agregar_detalle_evento_historial(
        evento,
        [
            ("Zona Educativa registrada", [
                ("Tipo de Zona", nuevo.get("tipo")),
                ("Zona Educativa", nuevo.get("zona")),
                ("Puntos Zona", nuevo.get("puntos")),
            ]),
            ("Identidad del evento", [
                ("CUE", cue),
                ("CUEANEXO", cueanexo),
                ("CUOF", cuof),
            ]),
        ],
        diff=diff,
        observacion=observacion,
    )


def _obtener_eventos_zona_historial(filtros):
    if not _tipo_evento_habilitado(filtros, TIPO_EVENTO_ZONA_EDUCATIVA):
        return []
    if filtros.get("ceic"):
        return []

    localizaciones = LocalizacionPof.objects.select_related(
        "reunida",
        "proyecto_especial",
    )

    if filtros.get("anio"):
        anio = int(filtros["anio"])
        localizaciones = localizaciones.filter(
            Q(reunida__anio=anio) | Q(proyecto_especial__anio=anio)
        )

    nivel = filtros.get("nivel")
    if nivel and nivel != NIVEL_TODOS:
        localizaciones = localizaciones.filter(reunida__nivel=nivel)

    if filtros.get("cueanexo"):
        localizaciones = localizaciones.filter(cueanexo=filtros["cueanexo"])
    if filtros.get("cuof"):
        localizaciones = localizaciones.filter(cuof__iexact=filtros["cuof"])

    canonicas = {}
    for localizacion in localizaciones.order_by("id"):
        identidad = _identidad_zona_historial(localizacion)
        if identidad is not None and identidad not in canonicas:
            canonicas[identidad] = localizacion

    if not canonicas:
        return []

    snapshots = (
        SnapshotPadronLocalizacionPof.objects
        .select_related(
            "usuario",
            "localizacion",
            "localizacion__reunida",
            "localizacion__proyecto_especial",
        )
        .filter(localizacion_id__in=[item.id for item in canonicas.values()])
        .order_by("localizacion_id", "fecha_snapshot", "id")
    )

    umbral = _umbral_vista_rapida(filtros)
    cuil = filtros.get("cuil")
    eventos = []
    anterior_por_localizacion = {}

    for snapshot in snapshots:
        actual = _asignacion_zona_snapshot_historial(snapshot)
        anterior = anterior_por_localizacion.get(snapshot.localizacion_id)
        anterior_por_localizacion[snapshot.localizacion_id] = actual

        if anterior is None:
            if not getattr(snapshot, "zona_educativa_evento", False):
                continue
            anterior = {
                "tipo": "",
                "zona": "",
                "puntos": None,
            }

        if _clave_asignacion_zona_historial(anterior) == _clave_asignacion_zona_historial(actual):
            continue
        if umbral is not None and snapshot.fecha_snapshot < umbral:
            continue
        if not _usuario_coincide_cuil(snapshot.usuario, cuil):
            continue

        eventos.append(
            _construir_evento_zona_historial(snapshot, anterior, actual)
        )

    eventos.sort(key=lambda item: (item["fecha"], str(item["id"])), reverse=True)
    return eventos


def _aplicar_vista_rapida_historial_anexo(queryset, filtros):
    umbral = _umbral_vista_rapida(filtros)
    if umbral is not None:
        queryset = queryset.filter(fecha__gte=umbral)
    return queryset


def _obtener_propietarios_anexo_contexto(filtros):
    nivel = filtros.get("nivel")
    tiene_contexto = bool(
        filtros.get("anio")
        or filtros.get("cueanexo")
        or filtros.get("cuof")
        or (nivel and nivel != NIVEL_TODOS)
    )
    if not tiene_contexto:
        return None

    localizaciones = LocalizacionPof.objects.select_related(
        "reunida",
        "proyecto_especial",
    )

    if filtros.get("anio"):
        anio = int(filtros["anio"])
        localizaciones = localizaciones.filter(
            Q(reunida__anio=anio) | Q(proyecto_especial__anio=anio)
        )

    if nivel and nivel != NIVEL_TODOS:
        localizaciones = localizaciones.filter(reunida__nivel=nivel)

    if filtros.get("cueanexo"):
        localizaciones = localizaciones.filter(cueanexo=filtros["cueanexo"])
    if filtros.get("cuof"):
        localizaciones = localizaciones.filter(cuof__iexact=filtros["cuof"])

    cueanexos = set()
    cuofs = set()
    for localizacion in localizaciones:
        cueanexo = str(localizacion.cueanexo or "").strip()
        if cueanexo.isdigit() and len(cueanexo) == 9:
            cueanexos.add(cueanexo)
            continue

        if localizacion.proyecto_especial_id:
            cuof = str(localizacion.cuof or "").strip()
            if cuof:
                cuofs.add(cuof)

    return cueanexos, cuofs


def _obtener_historial_anexo_queryset(filtros):
    if not _tipo_evento_habilitado(filtros, TIPO_EVENTO_ANEXO_POF):
        return HistorialAsociacionAnexoPof.objects.none()

    if filtros.get("ceic"):
        return HistorialAsociacionAnexoPof.objects.none()

    queryset = HistorialAsociacionAnexoPof.objects.select_related(
        "asociacion",
        "asociacion__codigo_catalogo",
        "usuario",
    )
    queryset = _aplicar_vista_rapida_historial_anexo(queryset, filtros)

    propietarios_contexto = _obtener_propietarios_anexo_contexto(filtros)
    if propietarios_contexto is not None:
        cueanexos, cuofs = propietarios_contexto
        filtro_propietarios = Q()
        if cueanexos:
            filtro_propietarios |= Q(
                asociacion__cueanexo__in=sorted(cueanexos),
                asociacion__cuof="",
            )
        if cuofs:
            filtro_propietarios |= Q(
                asociacion__cueanexo="",
                asociacion__cuof__in=sorted(cuofs),
            )
        if not cueanexos and not cuofs:
            return HistorialAsociacionAnexoPof.objects.none()
        queryset = queryset.filter(filtro_propietarios)
    if filtros.get("cuil"):
        queryset = queryset.filter(
            usuario__username__contains=filtros["cuil"]
        )

    return queryset.order_by("-fecha", "-id")


def _construir_evento_anexo_historial(historial):
    asociacion = historial.asociacion
    cueanexo = str(asociacion.cueanexo or "").strip()
    tipo_propietario = "CUEANEXO" if cueanexo else "CUOF"
    propietario = cueanexo or asociacion.cuof
    codigo = asociacion.codigo_catalogo.codigo
    cue = (
        cueanexo[:7]
        if cueanexo.isdigit() and len(cueanexo) == 9
        else GUION_VACIO
    )

    acciones = {
        HistorialAsociacionAnexoPof.Accion.ASOCIAR: "Se asoció",
        HistorialAsociacionAnexoPof.Accion.DESACTIVAR: "Se desactivó",
        HistorialAsociacionAnexoPof.Accion.REACTIVAR: "Se reactivó",
    }
    verbo = acciones.get(historial.accion, "Se actualizó")

    evento = {
        "id": f"anexo-{historial.id}",
        "fecha": historial.fecha,
        "usuario_movimiento": _serializar_usuario_movimiento(historial.usuario),
        "cabecera_resumen": f"Global · {tipo_propietario} {propietario}",
        "localizacion_resumen": {
            "cue": cue,
            "cueanexo": cueanexo or GUION_VACIO,
            "cuof": asociacion.cuof or GUION_VACIO,
        },
        "tipo_movimiento": TIPO_EVENTO_ANEXO_POF,
        "tipo_movimiento_display": TIPOS_MOVIMIENTO_LABELS[TIPO_EVENTO_ANEXO_POF],
        "tipo_movimiento_clase": "modificacion",
        "detalle_resumen_visual": {
            "accion": (
                f"{verbo} el Código Anexo POF {codigo} para "
                f"{tipo_propietario} {propietario}."
            ),
            "partes": [
                f"Código: {codigo}",
                f"Propietario: {tipo_propietario} {propietario}",
            ],
        },
        "tiene_observacion_real": False,
    }

    return _agregar_detalle_evento_historial(
        evento,
        [
            ("Asociación Anexo POF", [
                ("Código Anexo POF", codigo),
                ("Acción registrada", historial.get_accion_display()),
                ("Origen", historial.get_origen_display()),
                ("Tipo de propietario", tipo_propietario),
                ("Propietario", propietario),
            ]),
            ("Identidad del evento", [
                ("CUE", cue),
                ("CUEANEXO", cueanexo),
                ("CUOF", asociacion.cuof),
            ]),
        ],
    )


def _clave_orden_evento_historial(evento):
    return (evento["fecha"], str(evento["id"]))


def construir_contexto_historial(request):
    filtros, errores_filtros = obtener_filtros_historial_pof_con_errores(request)
    filtros_suficientes = not errores_filtros and filtros_historial_suficientes(filtros)

    movimientos_queryset = _obtener_movimientos_queryset()
    eventos_zona = []
    historial_anexo_queryset = HistorialAsociacionAnexoPof.objects.none()

    if filtros_suficientes:
        tipo_evento = filtros.get("tipo")
        if (
            tipo_evento
            and tipo_evento != TIPO_MOVIMIENTO_TODOS
            and tipo_evento not in TIPOS_EVENTO_CARGO
        ):
            movimientos_queryset = movimientos_queryset.none()
        else:
            movimientos_queryset = _aplicar_filtros_historial(
                movimientos_queryset,
                filtros,
            )
        eventos_zona = _obtener_eventos_zona_historial(filtros)
        historial_anexo_queryset = _obtener_historial_anexo_queryset(filtros)
    else:
        movimientos_queryset = movimientos_queryset.none()

    total_cargos = movimientos_queryset.count()
    total_zona = len(eventos_zona)
    total_anexo = historial_anexo_queryset.count()
    total_registros = total_cargos + total_zona + total_anexo

    paginator = Paginator(range(total_registros), 10)
    page_obj = paginator.get_page(request.GET.get("page", 1))
    limite_necesario = page_obj.end_index() if total_registros else 0

    eventos_cargo = [
        _evento_cargo_desde_movimiento(movimiento)
        for movimiento in movimientos_queryset[:limite_necesario]
    ]
    eventos_anexo = [
        _construir_evento_anexo_historial(historial)
        for historial in historial_anexo_queryset[:limite_necesario]
    ]

    candidatos = [
        *eventos_cargo,
        *eventos_zona[:limite_necesario],
        *eventos_anexo,
    ]
    candidatos.sort(key=_clave_orden_evento_historial, reverse=True)

    indice_inicio = page_obj.start_index() - 1 if total_registros else 0
    indice_fin = page_obj.end_index() if total_registros else 0
    eventos_pagina = candidatos[indice_inicio:indice_fin]
    page_obj.object_list = eventos_pagina

    query_params = request.GET.copy()
    query_params.pop("page", None)
    query_params.pop("texto", None)
    query_params.pop("page_size", None)
    tiene_contexto = bool(
        filtros["anio"]
        and filtros["nivel"]
        and filtros["nivel"] != NIVEL_TODOS
    )

    return {
        "anio_activo": filtros["anio"] if tiene_contexto else "",
        "nivel_codigo": filtros["nivel"] if tiene_contexto else "",
        "filtros": filtros,
        "niveles": NIVELES_VALIDOS,
        "tipos_movimiento": TIPOS_MOVIMIENTO_LABELS,
        "vistas_rapidas": VISTAS_RAPIDAS,
        "errores_filtros": errores_filtros,
        "filtros_activos": construir_chips_filtros_historial(
            request,
            filtros,
            errores_filtros,
        ),
        "filtros_suficientes": filtros_suficientes,
        "mensaje_filtros": (
            MENSAJE_FILTROS_INVALIDOS
            if errores_filtros
            else (
                ""
                if filtros_suficientes
                else obtener_mensaje_filtros_insuficientes_historial(filtros)
            )
        ),
        "limpiar_filtros_querystring": querystring_limpio_historial(),
        "page_obj": page_obj,
        "paginator": paginator,
        "movimientos": eventos_pagina,
        "detalles_eventos": {
            evento["id"]: evento["detalle_evento"]
            for evento in eventos_pagina
            if evento.get("detalle_evento")
        },
        "total_registros": total_registros,
        "total_movimientos_cargo": total_cargos,
        "total_eventos_zona": total_zona,
        "total_eventos_anexo": total_anexo,
        "showing_start": page_obj.start_index() if total_registros else 0,
        "showing_end": page_obj.end_index() if total_registros else 0,
        "query_params_base": query_params.urlencode(),
        "page_range": _obtener_page_range(paginator, page_obj),
        "titulo": obtener_titulo_historial(filtros),
    }
