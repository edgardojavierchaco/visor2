# apps/especial/views_localizaciones.py
# -*- coding: utf-8 -*-

import json
import logging
import time
import unicodedata
from datetime import datetime
from io import BytesIO

from django.core.cache import cache
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.http import HttpResponse
from django.shortcuts import render
from django.views.decorators.csrf import ensure_csrf_cookie
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font
from openpyxl.utils import get_column_letter

from .models import (
    get_escuelas_especiales_base_queryset,
    normalizar_cueanexo,
)
from .permisos import especial_required
from .views_contexto import contexto_base


logger = logging.getLogger(__name__)


PAGE_SIZE = 10
PAGE_SIZE_OPTIONS = [10, 25, 50, 100]
CACHE_TTL_LOCALIZACIONES_ESPECIAL = 60 * 5
CACHE_VERSION_LOCALIZACIONES_ESPECIAL = "v1_especial_20260623"

# Columnas que se leen desde Padrón y se exponen en tabla, filtros y Excel.
COLUMNAS_LOCALIZACIONES_ESPECIAL = [
    "cueanexo",
    "nom_est",
    "oferta",
    "ambito",
    "sector",
    "region_loc",
    "ref_loc",
    "calle",
    "numero",
    "localidad",
    "departamento",
    "estado_loc",
    "est_oferta",
    "estado_est",
    "resploc_cuitcuil",
    "resploc_doc",
    "apellido_resp",
    "nombre_resp",
    "resploc_email",
    "resploc_telefono",
    "sup_tecnico",
    "email_suptecnico",
    "tel_suptecnico",
    "categoria",
    "jornada",
]

LABELS_COLUMNAS = {
    "cueanexo": "CUE-Anexo",
    "nom_est": "Establecimiento",
    "oferta": "Oferta",
    "ambito": "Ámbito",
    "sector": "Sector",
    "region_loc": "Región",
    "ref_loc": "Referencia localización",
    "calle": "Calle",
    "numero": "Número",
    "localidad": "Localidad",
    "departamento": "Departamento",
    "estado_loc": "Estado localización",
    "est_oferta": "Estado oferta",
    "estado_est": "Estado establecimiento",
    "resploc_cuitcuil": "CUIL/CUIT responsable",
    "resploc_doc": "Documento responsable",
    "apellido_resp": "Apellido responsable",
    "nombre_resp": "Nombre responsable",
    "resploc_email": "Email responsable",
    "resploc_telefono": "Teléfono responsable",
    "sup_tecnico": "Supervisor técnico",
    "email_suptecnico": "Email supervisor técnico",
    "tel_suptecnico": "Teléfono supervisor técnico",
    "categoria": "Categoría",
    "jornada": "Jornada",
}

COLUMNAS_VISIBLES_DEFAULT = [
    "cueanexo",
    "nom_est",
    "oferta",
    "region_loc",
    "localidad",
    "departamento",
    "apellido_resp",
    "nombre_resp",
    "sup_tecnico",
    "categoria",
    "jornada",
]

ONLY_FIELDS_LOCALIZACIONES_ESPECIAL = COLUMNAS_LOCALIZACIONES_ESPECIAL
SORTABLE_FIELDS_LOCALIZACIONES_ESPECIAL = {col: col for col in COLUMNAS_LOCALIZACIONES_ESPECIAL}
DEFAULT_ORDER_LOCALIZACIONES_ESPECIAL = (
    "region_loc",
    "departamento",
    "localidad",
    "cueanexo",
)

def _get_filter_options(items):
    """Extrae opciones únicas para los filtros desde los items cacheados."""
    regiones = sorted(set(item.get("region_loc", "") for item in items if item.get("region_loc")))
    departamentos = sorted(set(item.get("departamento", "") for item in items if item.get("departamento")))
    localidades = sorted(set(item.get("localidad", "") for item in items if item.get("localidad")))
    
    return {
        "region_loc": [r for r in regiones if r],
        "departamento": [d for d in departamentos if d],
        "localidad": [l for l in localidades if l],
    }



def _log_perf(label, started):
    logger.debug(
        "ESPECIAL_LOCALIZACIONES %s %.1fms",
        label,
        (time.perf_counter() - started) * 1000,
    )


def _clean(value):
    if value is None:
        return ""
    return str(value).strip()


def _serialize_item(item):
    return {
        "cueanexo": _clean(getattr(item, "cueanexo", "")),
        "nom_est": _clean(getattr(item, "nom_est", "")),
        "oferta": _clean(getattr(item, "oferta", "")),
        "ambito": _clean(getattr(item, "ambito", "")),
        "sector": _clean(getattr(item, "sector", "")),
        "region_loc": _clean(getattr(item, "region_loc", "")),
        "ref_loc": _clean(getattr(item, "ref_loc", "")),
        "calle": _clean(getattr(item, "calle", "")),
        "numero": _clean(getattr(item, "numero", "")),
        "localidad": _clean(getattr(item, "localidad", "")),
        "departamento": _clean(getattr(item, "departamento", "")),
        "estado_loc": _clean(getattr(item, "estado_loc", "")),
        "est_oferta": _clean(getattr(item, "est_oferta", "")),
        "estado_est": _clean(getattr(item, "estado_est", "")),
        "resploc_cuitcuil": _clean(getattr(item, "resploc_cuitcuil", "")),
        "resploc_doc": _clean(getattr(item, "resploc_doc", "")),
        "apellido_resp": _clean(getattr(item, "apellido_resp", "")),
        "nombre_resp": _clean(getattr(item, "nombre_resp", "")),
        "resploc_email": _clean(getattr(item, "resploc_email", "")),
        "resploc_telefono": _clean(getattr(item, "resploc_telefono", "")),
        "sup_tecnico": _clean(getattr(item, "sup_tecnico", "")),
        "email_suptecnico": _clean(getattr(item, "email_suptecnico", "")),
        "tel_suptecnico": _clean(getattr(item, "tel_suptecnico", "")),
        "categoria": _clean(getattr(item, "categoria", "")),
        "jornada": _clean(getattr(item, "jornada", "")),
    }


def _cache_key_localizaciones_especial(request):
    user_id = getattr(request.user, "pk", None) or "anon"
    return f"especial:localizaciones:{CACHE_VERSION_LOCALIZACIONES_ESPECIAL}:user:{user_id}"


def _normalizar_orden_localizaciones(orden_param):
    orden = (orden_param or "").strip()
    if not orden:
        return ""
    signo = "-" if orden.startswith("-") else ""
    campo = orden[1:] if signo else orden
    if campo not in SORTABLE_FIELDS_LOCALIZACIONES_ESPECIAL:
        return ""
    return f"{signo}{campo}"


def _get_items_base_cached(request):
    """Obtiene y serializa las escuelas especiales visibles."""
    started = time.perf_counter()
    cache_key = _cache_key_localizaciones_especial(request)
    if request.GET.get("refresh") == "1":
        cache.delete(cache_key)

    sentinel = object()
    cached_items = cache.get(cache_key, sentinel)
    if cached_items is not sentinel:
        _log_perf("_get_items_base_cached hit", started)
        return cached_items

    qs = get_escuelas_especiales_base_queryset()
    qs = qs.only(*ONLY_FIELDS_LOCALIZACIONES_ESPECIAL)
    items = [_serialize_item(item) for item in qs]

    cache.set(cache_key, items, CACHE_TTL_LOCALIZACIONES_ESPECIAL)
    _log_perf("_get_items_base_cached miss", started)
    return items


def _normalize_text(value):
    """Normaliza texto para comparar sin distinguir mayúsculas ni acentos."""
    text = _clean(value).casefold()
    text = unicodedata.normalize("NFKD", text)
    return "".join(char for char in text if not unicodedata.combining(char))


def _contains(value, needle):
    return _normalize_text(needle) in _normalize_text(value)


def _iexact(value, needle):
    return _normalize_text(value) == _normalize_text(needle)


def _compare_text(value, operator, needle):
    left = _normalize_text(value)
    right = _normalize_text(needle)
    return {
        "3": left > right,
        "4": left >= right,
        "5": left < right,
        "6": left <= right,
    }.get(operator, False)


def _item_matches_operator(item, field_key, operator, value):
    item_value = item.get(field_key, "")
    if operator == "1":
        return not _contains(item_value, value)
    if operator == "2":
        return _iexact(item_value, value)
    if operator in {"3", "4", "5", "6"}:
        return _compare_text(item_value, operator, value)
    if operator == "7":
        return not _iexact(item_value, value)
    return _contains(item_value, value)


def _apply_filters_list(items, request, establecimientos=None):
    """Aplica filtros de búsqueda sobre la lista cacheada."""
    started = time.perf_counter()
    q = request.GET.get("q", "").strip()
    if q:
        items = [
            item
            for item in items
            if any(_contains(item.get(field, ""), q) for field in COLUMNAS_LOCALIZACIONES_ESPECIAL)
        ]

    smart_col = request.GET.get("smart_ui_col", "").strip()
    smart_val = request.GET.get("smart_ui_val", "").strip()
    if smart_col in COLUMNAS_LOCALIZACIONES_ESPECIAL and smart_val:
        items = [item for item in items if _contains(item.get(smart_col, ""), smart_val)]

    if establecimientos is None:
        establecimientos = {
            normalizar_cueanexo(value)
            for value in request.GET.getlist("establecimientos")
        }
    else:
        establecimientos = {normalizar_cueanexo(value) for value in establecimientos}
    establecimientos.discard("")
    if establecimientos:
        items = [
            item
            for item in items
            if normalizar_cueanexo(item.get("cueanexo", "")) in establecimientos
        ]

    for campo in COLUMNAS_LOCALIZACIONES_ESPECIAL:
        value = request.GET.get(campo, "").strip()
        if not value:
            continue
        items = [item for item in items if _contains(item.get(campo, ""), value)]

    campos = request.GET.getlist("campo_filtro")
    operadores = request.GET.getlist("operador_filtro")
    valores = request.GET.getlist("valor_filtro")
    grouped_filters = {}
    for index, campo in enumerate(campos):
        campo = campo.strip()
        valor = valores[index].strip() if index < len(valores) else ""
        operador = operadores[index].strip() if index < len(operadores) else "0"
        if not campo or not valor or campo not in COLUMNAS_LOCALIZACIONES_ESPECIAL:
            continue
        grouped_filters.setdefault((campo, operador), [])
        if valor not in grouped_filters[(campo, operador)]:
            grouped_filters[(campo, operador)].append(valor)

    for (campo, operador), valores_grupo in grouped_filters.items():
        items = [
            item
            for item in items
            if any(
                _item_matches_operator(item, campo, operador, valor)
                for valor in valores_grupo
            )
        ]

    _log_perf("_apply_filters_list", started)
    return items


def _sort_key_default(item):
    return (
        _normalize_text(item.get("region_loc", "")),
        _normalize_text(item.get("departamento", "")),
        _normalize_text(item.get("localidad", "")),
        _normalize_text(item.get("cueanexo", "")),
    )


def _apply_order_list(items, request):
    """Ordena la lista filtrada completa antes de paginar."""
    started = time.perf_counter()
    orden = _normalizar_orden_localizaciones(request.GET.get("orden", ""))
    ordered_items = sorted(items, key=_sort_key_default)

    if not orden:
        _log_perf("_apply_order_list", started)
        return ordered_items, ""

    reverse = orden.startswith("-")
    campo = orden[1:] if reverse else orden
    if campo not in COLUMNAS_LOCALIZACIONES_ESPECIAL:
        _log_perf("_apply_order_list", started)
        return ordered_items, ""

    ordered_items = sorted(
        ordered_items,
        key=lambda item: _normalize_text(item.get(campo, "")),
        reverse=reverse,
    )
    _log_perf("_apply_order_list", started)
    return ordered_items, orden


def _get_page_size(request):
    try:
        page_size = int(request.GET.get("page_size", PAGE_SIZE))
    except (TypeError, ValueError):
        return PAGE_SIZE
    return page_size if page_size in PAGE_SIZE_OPTIONS else PAGE_SIZE


def _resolver_columnas_exportar(request, formato):
    if formato == "excel_todo":
        return [(LABELS_COLUMNAS[col], col) for col in COLUMNAS_LOCALIZACIONES_ESPECIAL]

    visibles = {
        value.strip().replace("-", "_")
        for value in request.GET.getlist("visible_col")
        if value.strip()
    }
    columnas = [
        (LABELS_COLUMNAS[col], col)
        for col in COLUMNAS_LOCALIZACIONES_ESPECIAL
        if col in visibles
    ]
    return columnas or [
        (LABELS_COLUMNAS[col], col) for col in COLUMNAS_LOCALIZACIONES_ESPECIAL
    ]


def _exportar_excel_especial(datos, request, formato):
    """Genera el archivo Excel."""
    from openpyxl.worksheet.worksheet import Worksheet
    from openpyxl.cell.cell import Cell
    
    columnas = _resolver_columnas_exportar(request, formato)

    wb = Workbook()
    ws = wb.active
    assert ws is not None
    ws.title = "Localizaciones Especial"

    num_columnas: int = len(columnas)
    ultima_columna: str = get_column_letter(num_columnas)

    # Encabezado del informe
    rango_titulo: str = f"A1:{ultima_columna}1"
    ws.merge_cells(rango_titulo)
    celda_titulo: Cell = ws["A1"]
    celda_titulo.value = "Informe Localizaciones Educación Especial"
    celda_titulo.font = Font(bold=True, size=10)
    celda_titulo.alignment = Alignment(horizontal="left", vertical="center")

    fecha_str: str = datetime.now().strftime("%d/%m/%Y a las %I:%M %p").lstrip("0")
    fecha_str = fecha_str.replace("AM", "a. m.").replace("PM", "p. m.")
    
    rango_fecha: str = f"A2:{ultima_columna}2"
    ws.merge_cells(rango_fecha)
    celda_fecha: Cell = ws["A2"]
    celda_fecha.value = f"Informe generado el: {fecha_str}"
    celda_fecha.font = Font(size=9)
    celda_fecha.alignment = Alignment(horizontal="left", vertical="center")

    ws.merge_cells(f"A3:{ultima_columna}3")
    ws["A3"] = (
        "Filtros aplicados: Sin filtros aplicados"
        if formato == "excel_todo"
        else "Filtros aplicados desde la vista"
    )
    ws["A3"].font = Font(size=9)
    ws["A3"].alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)

    # Encabezados de columnas
    header_row: int = 4
    for col_idx, (label, _) in enumerate(columnas, start=1):
        cell: Cell = ws.cell(row=header_row, column=col_idx, value=label)
        cell.font = Font(bold=True, size=9)
        cell.alignment = Alignment(horizontal="left", vertical="center")

    # Datos
    for item in datos:
        fila: list = [item.get(field, "") for _, field in columnas]
        ws.append(fila)

    ws.freeze_panes = "A5"
    max_row: int = ws.max_row or header_row
    rango_filtro: str = f"A{header_row}:{ultima_columna}{max_row}"
    ws.auto_filter.ref = rango_filtro

    # Ajuste de ancho de columnas
    for col_num in range(1, num_columnas + 1):
        col_letter: str = get_column_letter(col_num)
        max_length: int = 0
        for row in ws.iter_rows(min_row=header_row, max_col=col_num, max_row=max_row):
            if not row:
                continue
            cell_value = row[0].value
            if cell_value is not None:
                max_length = max(max_length, len(str(cell_value)))
        ws.column_dimensions[col_letter].width = min(max_length + 2, 42)

    # Generar respuesta
    output = BytesIO()
    wb.save(output)
    output.seek(0)

    sufijo = "Filtros" if formato == "excel_pagina" else "Todo"
    nombre_archivo: str = f"Localizaciones_Especial_{sufijo}_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
    response = HttpResponse(
        output.getvalue(),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    response["Content-Disposition"] = f'attachment; filename="{nombre_archivo}"'
    return response

@especial_required
@ensure_csrf_cookie
def visualizacion_localizaciones(request):
    """Vista principal de Localizaciones de Educación Especial."""
    view_started = time.perf_counter()
    formato = request.GET.get("formato")

    base_items = _get_items_base_cached(request)
    total_escuelas = len(base_items)

    # Obtener opciones de filtros UNA SOLA VEZ
    filter_options = _get_filter_options(base_items)

    establecimientos_seleccionados = []
    establecimientos_visibles = {
        normalizar_cueanexo(item.get("cueanexo", "")) for item in base_items
    }
    for value in request.GET.getlist("establecimientos"):
        normalized = normalizar_cueanexo(value)
        if normalized in establecimientos_visibles and normalized not in establecimientos_seleccionados:
            establecimientos_seleccionados.append(normalized)
    seleccion_establecimientos_explicita = bool(establecimientos_seleccionados)

    if formato == "excel_todo":
        return _exportar_excel_especial(list(base_items), request, formato)

    items = list(base_items)
    if seleccion_establecimientos_explicita:
        seleccion_set = set(establecimientos_seleccionados)
        items = [
            item
            for item in items
            if normalizar_cueanexo(item.get("cueanexo", "")) in seleccion_set
        ]
    items = _apply_filters_list(items, request, establecimientos=establecimientos_seleccionados)
    items, orden_actual = _apply_order_list(items, request)

    if formato == "excel_pagina":
        return _exportar_excel_especial(items, request, formato)

    page_size = _get_page_size(request)
    lista_items_total = items

    paginator = Paginator(lista_items_total, page_size)
    page_number = request.GET.get("page", 1)
    try:
        page_obj = paginator.page(page_number)
    except (EmptyPage, PageNotAnInteger):
        page_obj = paginator.page(1)

    lista_items = list(page_obj.object_list)
    total = paginator.count
    desde = (page_obj.number - 1) * page_size + 1 if total else 0
    hasta = min(page_obj.number * page_size, total)

    establecimientos_options = [
        {"cueanexo": str(item["cueanexo"]), "nom_est": item.get("nom_est", "")}
        for item in base_items
    ]
    establecimientos_options = list({v['cueanexo']:v for v in establecimientos_options}.values())
    establecimientos_options.sort(key=lambda x: x["cueanexo"])

    columnas_config = [
        {
            "key": col,
            "label": LABELS_COLUMNAS[col],
            "slug": col.replace("_", "-"),
            "default": col in COLUMNAS_VISIBLES_DEFAULT,
        }
        for col in COLUMNAS_LOCALIZACIONES_ESPECIAL
    ]
    columnas_config_json = json.dumps(columnas_config)

    context = contexto_base(request, "localizaciones")
    especial_context = context["especial_context"]

    context.update({
        "establecimientos_options": establecimientos_options,
        "establecimientos_seleccionados": establecimientos_seleccionados,
        "total_establecimientos_seleccionados": len(establecimientos_seleccionados),
        "seleccion_establecimientos_explicita": seleccion_establecimientos_explicita,
        "lista_items": lista_items,
        "localizaciones": lista_items,
        "total_localizaciones": total,
        "resultado_total": total,
        "resultado_desde": desde,
        "resultado_hasta": hasta,
        "page_size": page_size,
        "page_size_options": PAGE_SIZE_OPTIONS,
        "page_obj": page_obj,
        "paginator": paginator,
        "filter_options": filter_options,
        "columnas": COLUMNAS_LOCALIZACIONES_ESPECIAL,
        "labels_columnas": LABELS_COLUMNAS,
        "columnas_visibles_default": COLUMNAS_VISIBLES_DEFAULT,
        "columnas_config": columnas_config,
        "columnas_config_json": columnas_config_json,
        "orden": orden_actual,
        "mostrar_contexto": False,
        "region_loc": sorted(set(item["region_loc"] for item in base_items if item["region_loc"])),
        "departamento": sorted(set(item["departamento"] for item in base_items if item["departamento"])),
        "localidad": sorted(set(item["localidad"] for item in base_items if item["localidad"])),
        "limpiar_filtros_url": request.path,
        "request": request,
        # ✅ AGREGAR ESTO PARA QUE LOS FILTROS FUNCIONEN:
        **filter_options,
        "smart_search_col": request.GET.get("smart_ui_col", "") or ("all" if request.GET.get("q") else "cueanexo"),
        "smart_search_value": request.GET.get("smart_ui_val", "") or request.GET.get("q", ""),
    })

    render_started = time.perf_counter()
    is_fragment_request = (
        request.GET.get("fragmento") == "resultados"
        or request.headers.get("X-Requested-With") == "XMLHttpRequest"
    )
    template_name = (
        "especial/componentes/localizaciones_resultados_especial.html"
        if is_fragment_request
        else "especial/localizaciones_especial.html"
    )
    response = render(request, template_name, context)
    _log_perf("render final", render_started)
    _log_perf("visualizacion_localizaciones total", view_started)
    return response
