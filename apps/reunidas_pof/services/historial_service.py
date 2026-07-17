from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation

from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db.models import Q
from django.utils import timezone

from ..models import CargoPof, MovimientoCargoPof
from .exportacion_rows import obtener_clave_consolidacion_cargo
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


PAGE_SIZE_OPTIONS = (10, 30, 50, 100)
MAX_CARGOS_HISTORIAL = 100
TIPOS_MOVIMIENTO_ESTADO = (
    MovimientoCargoPof.TipoMovimiento.AFECTACION,
    MovimientoCargoPof.TipoMovimiento.DESAFECTACION,
)
FLECHA_CAMBIO = "\u2192"
GUION_VACIO = "\u2014"
MOJIBAKE_GUION_VACIO = "\u00e2\u20ac\u201d"
OBSERVACION_PLACEHOLDERS = {"-", "--", "---", MOJIBAKE_GUION_VACIO, GUION_VACIO}

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

CAMPOS_EXCLUIDOS_DIFF = {"observacion"}
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

    - Acepta solo movimientos de afectación o desafectación.
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
        estado_nuevo
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


def enriquecer_filas_con_historial_estado(filas):
    """
    Marca en lote las filas que poseen cambios reales de Estado POF.

    - Obtiene todos los cargo_ids de las filas recibidas.
    - Ejecuta una única consulta para afectaciones y desafectaciones.
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


def _construir_diff_movimiento(movimiento):
    """
    Genera el diff visible del movimiento a partir de sus snapshots JSON.

    - Compara cada campo con normalización por tipo para evitar falsos positivos.
    - Incluye observación cuando cambió de forma real entre antes y después.
    - Fuerza la presencia del cambio de estado en afectaciones/desafectaciones.
    """
    anteriores = movimiento.valores_anteriores if isinstance(movimiento.valores_anteriores, dict) else {}
    nuevos = movimiento.valores_nuevos if isinstance(movimiento.valores_nuevos, dict) else {}
    claves = _ordenar_claves_diff(
        clave for clave in set(anteriores.keys()) | set(nuevos.keys())
        if str(clave) not in (CAMPOS_EXCLUIDOS_DIFF - {"observacion"})
    )
    diff = []
    es_alta = movimiento.tipo_movimiento == MovimientoCargoPof.TipoMovimiento.ALTA

    for clave in claves:
        anterior_crudo = anteriores.get(clave)
        nuevo_crudo = nuevos.get(clave)
        anterior = _formatear_valor_campo(clave, anterior_crudo)
        nuevo = _formatear_valor_campo(clave, nuevo_crudo)

        if _valores_equivalentes(clave, anterior_crudo, nuevo_crudo) and not (es_alta and clave in nuevos and not anteriores):
            continue

        if es_alta and clave in nuevos and not anteriores:
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

    if movimiento.tipo_movimiento in (
        MovimientoCargoPof.TipoMovimiento.AFECTACION,
        MovimientoCargoPof.TipoMovimiento.DESAFECTACION,
    ):
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


def _obtener_page_size(request):
    try:
        page_size = int(request.GET.get("page_size", PAGE_SIZE_OPTIONS[0]))
    except (TypeError, ValueError):
        return PAGE_SIZE_OPTIONS[0]

    return page_size if page_size in PAGE_SIZE_OPTIONS else PAGE_SIZE_OPTIONS[0]


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
        return f"Reunida · {reunida.get_nivel_display()} {reunida.anio}"
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

    nombre = str(usuario).strip() or GUION_VACIO
    cuil = (
        getattr(usuario, "cuil", "")
        or getattr(usuario, "cuit", "")
        or getattr(usuario, "username", "")
        or ""
    )
    cuil = "".join(caracter for caracter in str(cuil) if caracter.isdigit())

    return {
        "nombre": nombre,
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

    - Prioriza cambios estructurales visibles como cantidad, total y estado.
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

        if clave == "cantidad":
            partes.append(f"Cantidad {cambio['anterior']} {FLECHA_CAMBIO} {cambio['nuevo']}")
            continue

        if clave == "total":
            partes.append(f"Total {cambio['anterior']} {FLECHA_CAMBIO} {cambio['nuevo']}")
            continue

        if clave == "estado_pof":
            partes.append(f"Estado {cambio['anterior']} {FLECHA_CAMBIO} {cambio['nuevo']}")
            continue

        if modo == "alta" and clave in {"unidad_cantidad", "puntos_asignados"}:
            nombre = "Unidad" if clave == "unidad_cantidad" else "Puntos"
            partes.append(f"{nombre}: {cambio['nuevo']}")

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

    if movimiento.tipo_movimiento == MovimientoCargoPof.TipoMovimiento.ALTA:
        partes = _partes_diff_resumen(diff, "alta")
        detalle = f"Se añadió el cargo {referencia}."
        return f"{detalle} {'; '.join(partes)}." if partes else detalle

    if movimiento.tipo_movimiento == MovimientoCargoPof.TipoMovimiento.AFECTACION:
        partes = _partes_diff_resumen(diff, "modificacion")
        detalle = f"Se reactivó el cargo {referencia}."
        return f"{detalle} {'; '.join(partes)}." if partes else detalle

    if movimiento.tipo_movimiento == MovimientoCargoPof.TipoMovimiento.DESAFECTACION:
        partes = _partes_diff_resumen(diff, "modificacion")
        detalle = f"Se dio de baja el cargo {referencia}."
        return f"{detalle} {'; '.join(partes)}." if partes else detalle

    partes = _partes_diff_resumen(diff, "modificacion")
    if partes:
        if _es_movimiento_incremento(movimiento, diff):
            return f"Se incrementó el cargo existente {referencia}. {'; '.join(partes)}."
        return f"Se modificó el cargo {referencia}. {'; '.join(partes)}."

    return "Movimiento registrado sin cambios de valores."


def _resumir_detalle_movimiento(movimiento, proyecto):
    """
    Construye el texto compacto que se muestra en la columna Detalle del listado.

    - Conserva el verbo principal de cada movimiento para que el listado sea entendible.
    - Resume observaciones largas como un cambio breve sin mostrar su contenido completo.
    - Deja el diff completo y el detalle extenso exclusivamente para el modal AJAX.
    """
    del proyecto
    referencia = _referencia_cargo_movimiento(movimiento)
    diff = _construir_diff_movimiento(movimiento)

    if movimiento.tipo_movimiento == MovimientoCargoPof.TipoMovimiento.ALTA:
        partes = _partes_diff_resumen_compacto(diff, "alta")
        detalle = f"Se añadió el cargo {referencia}."
        return f"{detalle} {'; '.join(partes)}." if partes else detalle

    if movimiento.tipo_movimiento == MovimientoCargoPof.TipoMovimiento.AFECTACION:
        partes = _partes_diff_resumen_compacto(diff, "modificacion")
        detalle = f"Se reactivó el cargo {referencia}."
        return f"{detalle} {'; '.join(partes)}." if partes else detalle

    if movimiento.tipo_movimiento == MovimientoCargoPof.TipoMovimiento.DESAFECTACION:
        partes = _partes_diff_resumen_compacto(diff, "modificacion")
        detalle = f"Se dio de baja el cargo {referencia}."
        return f"{detalle} {'; '.join(partes)}." if partes else detalle

    partes = _partes_diff_resumen_compacto(diff, "modificacion")
    if partes:
        if _es_movimiento_incremento(movimiento, diff):
            return f"Se incrementó el cargo existente {referencia}. {'; '.join(partes)}."
        return f"Se modificó el cargo {referencia}. {'; '.join(partes)}."

    return generar_detalle_movimiento(movimiento)


def _preparar_movimiento_para_listado(movimiento):
    reunida, proyecto = _obtener_cabecera_movimiento(movimiento)
    movimiento.cabecera_resumen = _resumir_cabecera(reunida, proyecto)
    movimiento.detalle_resumen = _resumir_detalle_movimiento(movimiento, proyecto)
    movimiento.localizacion_resumen = _serializar_localizacion_listado(movimiento)
    movimiento.usuario_movimiento = _serializar_usuario_movimiento(movimiento.usuario)
    movimiento.tiene_observacion_real = bool(_normalizar_observacion_real(movimiento.observacion))
    movimiento.tipo_movimiento_display = movimiento.get_tipo_movimiento_display()
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
        partes.append("Todos los movimientos")

    if filtros.get("vista_rapida") in {VISTA_7_DIAS, VISTA_30_DIAS}:
        partes.append(VISTAS_RAPIDAS[filtros["vista_rapida"]])

    if partes:
        return "Historial de movimientos - " + " / ".join(partes)

    return "Historial de movimientos POF"


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
            "movimiento": movimiento.get_tipo_movimiento_display(),
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
            "movimiento": movimiento.get_tipo_movimiento_display(),
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
                "Los cargos deben pertenecer a una misma Reunida POF normal "
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


def _serializar_movimiento_observacion(movimiento):
    observacion_anterior, observacion_nueva = _observaciones_comparables_movimiento(
        movimiento
    )
    usuario = _serializar_usuario_movimiento(movimiento.usuario)
    return {
        "id": movimiento.id,
        "fecha": _valor_serializable(movimiento.fecha),
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
    movimientos = MovimientoCargoPof.objects.select_related("usuario").filter(
        cargo_id__in=cargo_ids,
        tipo_movimiento=MovimientoCargoPof.TipoMovimiento.MODIFICACION,
    ).order_by("cargo_id", "fecha", "id")

    for movimiento in movimientos:
        if es_cambio_real_observacion_movimiento(movimiento):
            movimientos_por_cargo[movimiento.cargo_id].append(
                _serializar_movimiento_observacion(movimiento)
            )

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
    Obtiene el historial real de afectaciones y desafectaciones de una fila.

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
        "tipo_movimiento_display": movimiento.get_tipo_movimiento_display(),
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


def construir_contexto_historial(request):
    filtros, errores_filtros = obtener_filtros_historial_pof_con_errores(request)
    page_size = _obtener_page_size(request)
    filtros_suficientes = not errores_filtros and filtros_historial_suficientes(filtros)
    queryset = _obtener_movimientos_queryset()
    if filtros_suficientes:
        queryset = _aplicar_filtros_historial(queryset, filtros)
    else:
        queryset = queryset.none()
    paginator = Paginator(queryset, page_size)
    page_obj = paginator.get_page(request.GET.get("page", 1))

    for movimiento in page_obj.object_list:
        _preparar_movimiento_para_listado(movimiento)

    query_params = request.GET.copy()
    query_params.pop("page", None)
    query_params.pop("texto", None)
    query_params["page_size"] = page_size
    total_registros = paginator.count
    tiene_contexto = bool(filtros["anio"] and filtros["nivel"] and filtros["nivel"] != NIVEL_TODOS)

    return {
        "anio_activo": filtros["anio"] if tiene_contexto else "",
        "nivel_codigo": filtros["nivel"] if tiene_contexto else "",
        "filtros": filtros,
        "niveles": NIVELES_VALIDOS,
        "tipos_movimiento": TIPOS_MOVIMIENTO_LABELS,
        "vistas_rapidas": VISTAS_RAPIDAS,
        "errores_filtros": errores_filtros,
        "filtros_activos": construir_chips_filtros_historial(request, filtros, errores_filtros),
        "filtros_suficientes": filtros_suficientes,
        "mensaje_filtros": (
            MENSAJE_FILTROS_INVALIDOS
            if errores_filtros
            else ("" if filtros_suficientes else obtener_mensaje_filtros_insuficientes_historial(filtros))
        ),
        "limpiar_filtros_querystring": querystring_limpio_historial(request, page_size),
        "page_obj": page_obj,
        "paginator": paginator,
        "movimientos": page_obj.object_list,
        "total_registros": total_registros,
        "showing_start": page_obj.start_index() if total_registros else 0,
        "showing_end": page_obj.end_index() if total_registros else 0,
        "page_size": page_size,
        "page_size_options": PAGE_SIZE_OPTIONS,
        "query_params_base": query_params.urlencode(),
        "page_range": _obtener_page_range(paginator, page_obj),
        "titulo": obtener_titulo_historial(filtros),
    }
