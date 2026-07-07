# apps/especial/views_localizaciones.py
# -*- coding: utf-8 -*-

import json
import logging
import time
import unicodedata
from datetime import datetime
from io import BytesIO
from urllib import request

from django.core.cache import cache
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.http import HttpResponse
from django.shortcuts import render
from django.views.decorators.csrf import ensure_csrf_cookie
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font
from openpyxl.utils import get_column_letter

from .models import (
    get_todas_las_escuelas_especiales,
    normalizar_cueanexo,
)
from .permisos import especial_required


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

def _get_filter_options(items):
    """Extrae opciones únicas para los filtros desde los items cacheados."""
    regiones = sorted(set(item.get("region_loc", "") for item in items if item.get("region_loc")))
    departamentos = sorted(set(item.get("departamento", "") for item in items if item.get("departamento")))
    localidades = sorted(set(item.get("localidad", "") for item in items if item.get("localidad")))
    
    return {
        "opciones_regiones": [r for r in regiones if r],
        "opciones_departamentos": [d for d in departamentos if d],
        "opciones_localidades": [l for l in localidades if l],
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

    qs = get_todas_las_escuelas_especiales()
    try:
        qs = qs.only(*ONLY_FIELDS_LOCALIZACIONES_ESPECIAL)
        items = [_serialize_item(item) for item in qs]
    except Exception:
        items = [_serialize_item(item) for item in get_todas_las_escuelas_especiales()]

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


def _apply_filters_list(items, request):
    """Aplica filtros de búsqueda sobre la lista cacheada."""
    started = time.perf_counter()
    q = request.GET.get("q", "").strip()
    if q:
        items = [
            item
            for item in items
            if any(_contains(item.get(field, ""), q) for field in COLUMNAS_LOCALIZACIONES_ESPECIAL)
        ]

    for campo in COLUMNAS_LOCALIZACIONES_ESPECIAL:
        value = request.GET.get(campo, "").strip()
        if not value:
            continue
        items = [item for item in items if _contains(item.get(campo, ""), value)]

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
    """Ordena los items."""
    started = time.perf_counter()
    orden_param = request.GET.get("orden", "region_loc").strip()
    raw_field = orden_param.lstrip("-")
    reverse = orden_param.startswith("-")

    ordered_items = sorted(items, key=_sort_key_default)
    if raw_field in COLUMNAS_LOCALIZACIONES_ESPECIAL:
        ordered_items = sorted(
            ordered_items,
            key=lambda item: _normalize_text(item.get(raw_field, "")),
            reverse=reverse,
        )
        _log_perf("_apply_order_list", started)
        return ordered_items, orden_param

    _log_perf("_apply_order_list", started)
    return ordered_items, ""


def _get_page_size(request):
    try:
        page_size = int(request.GET.get("page_size", PAGE_SIZE))
    except (TypeError, ValueError):
        return PAGE_SIZE
    return page_size if page_size in PAGE_SIZE_OPTIONS else PAGE_SIZE


def _exportar_excel_especial(datos, request):
    """Genera el archivo Excel."""
    from openpyxl.worksheet.worksheet import Worksheet
    from openpyxl.cell.cell import Cell
    
    columnas: list[tuple[str, str]] = [
        (LABELS_COLUMNAS[col], col) for col in COLUMNAS_LOCALIZACIONES_ESPECIAL
    ]

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

    # Encabezados de columnas
    header_row: int = 3
    for col_idx, (label, _) in enumerate(columnas, start=1):
        cell: Cell = ws.cell(row=header_row, column=col_idx, value=label)
        cell.font = Font(bold=True, size=9)
        cell.alignment = Alignment(horizontal="left", vertical="center")

    # Datos
    for item in datos:
        fila: list = [item.get(field, "") for _, field in columnas]
        ws.append(fila)

    ws.freeze_panes = "A4"
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

    nombre_archivo: str = f"Localizaciones_Especial_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
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

    if formato == "excel":
        items = list(base_items)
        items = _apply_filters_list(items, request)
        items, orden = _apply_order_list(items, request)
        return _exportar_excel_especial(items, request)

    items = list(base_items)
    items = _apply_filters_list(items, request)
    items, orden = _apply_order_list(items, request)

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

# En views_localizaciones.py, dentro de visualizacion_localizaciones():

    context = {
        "title": "Localizaciones Educación Especial",
        "active_menu": "localizaciones",
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
        "columnas": COLUMNAS_LOCALIZACIONES_ESPECIAL,
        "labels_columnas": LABELS_COLUMNAS,
        "columnas_visibles_default": COLUMNAS_VISIBLES_DEFAULT,
        "orden": orden,
        "mostrar_contexto": False,
        "opciones_regiones": sorted(set(item["region_loc"] for item in base_items if item["region_loc"])),
        "opciones_departamentos": sorted(set(item["departamento"] for item in base_items if item["departamento"])),
        "opciones_localidades": sorted(set(item["localidad"] for item in base_items if item["localidad"])),
        "limpiar_filtros_url": request.path,
        "request": request,
        # ✅ AGREGAR ESTO PARA QUE LOS FILTROS FUNCIONEN:
        **filter_options, 
    }

    render_started = time.perf_counter()
    response = render(request, "especial/localizaciones_especial.html", context)
    _log_perf("render final", render_started)
    _log_perf("visualizacion_localizaciones total", view_started)
    return response