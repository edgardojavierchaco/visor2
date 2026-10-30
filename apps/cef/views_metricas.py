# -*- coding: utf-8 -*-

import logging
from io import BytesIO

from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse, JsonResponse, QueryDict
from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET, require_http_methods
from openpyxl import Workbook
from openpyxl.drawing.image import Image as ExcelImage
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from .models import CefCiclo
from .permisos import cef_metricas_required, get_permisos_cef_request
from .services_metricas import (
    MetricasValidationError,
    construir_configuracion_metricas,
)

from .services_consultas import configurar_consultas, ejecutar_consulta


logger = logging.getLogger(__name__)


def _alcance_metricas(request):
    permisos = get_permisos_cef_request(request)
    if not (permisos.get("solo_metricas") or permisos.get("es_director_cef")):
        return permisos, None, None

    cefs_permitidos = tuple(
        dict.fromkeys(
            str(valor or "").strip()
            for valor in permisos.get("cueanexos_cargables", [])
            if str(valor or "").strip()
        )
    )
    if permisos.get("es_director_cef"):
        return permisos, cefs_permitidos, None

    ciclo_actual = (
        CefCiclo.objects.filter(actual=True)
        .order_by("-anio", "-pk")
        .values_list("pk", flat=True)
        .first()
    )
    if ciclo_actual is None:
        ultimo_ciclo = (
            CefCiclo.objects.order_by("-anio", "-pk")
            .values("pk", "cerrado", "activo")
            .first()
        )
        if ultimo_ciclo and ultimo_ciclo["cerrado"] and ultimo_ciclo["activo"]:
            ciclo_actual = ultimo_ciclo["pk"]
    ciclos_permitidos = (ciclo_actual,) if ciclo_actual is not None else ()
    return permisos, cefs_permitidos, ciclos_permitidos


def _mensaje_sin_ciclo_metricas():
    if not CefCiclo.objects.exists():
        return "Todavía no hay ciclos creados para Consultas CEF."
    return (
        "Estado de ciclos inconsistente: no hay un ciclo actual y el ciclo más reciente "
        "no está cerrado y activo. Solicitá su revisión a un Administrador."
    )


def _parametros_metricas_autorizados_desde(request, origen):
    permisos, cefs_permitidos, ciclos_permitidos = _alcance_metricas(request)
    params = origen.copy()
    if not (permisos.get("solo_metricas") or permisos.get("es_director_cef")):
        return params

    if not cefs_permitidos:
        raise PermissionDenied("No tenés CEF asociados para realizar consultas.")
    if ciclos_permitidos == ():
        raise PermissionDenied(_mensaje_sin_ciclo_metricas())

    cefs_solicitados = []
    for valor in params.getlist("cefs"):
        limpio = str(valor or "").strip()
        if limpio and limpio not in cefs_solicitados:
            cefs_solicitados.append(limpio)

    permitidos = set(cefs_permitidos)
    if any(valor not in permitidos for valor in cefs_solicitados):
        raise PermissionDenied("No tenés permisos para consultar uno o más CEF seleccionados.")

    params.setlist("cefs", cefs_solicitados or list(cefs_permitidos))
    if ciclos_permitidos is not None:
        params.setlist("ciclos", [str(ciclos_permitidos[0])])
    return params


def _parametros_metricas_autorizados(request):
    return _parametros_metricas_autorizados_desde(request, request.GET)


def _contexto_pagina_metricas(request):
    """Configura Consultas según el alcance permitido para la persona usuaria."""
    permisos, cefs_permitidos, ciclos_permitidos = _alcance_metricas(request)
    config_kwargs = {}
    if permisos.get("solo_metricas") or permisos.get("es_director_cef"):
        if ciclos_permitidos == ():
            messages.warning(request, _mensaje_sin_ciclo_metricas())
        config_kwargs = {
            "cefs_permitidos": cefs_permitidos,
            "ciclos_permitidos": ciclos_permitidos,
        }
    return {
        "title": "Consultas CEF",
        "active_menu": "metricas",
        "es_admin_cef": permisos.get("es_admin", False),
        "puede_metricas": permisos.get("puede_metricas", False),
        "solo_metricas": permisos.get("solo_metricas", False),
        "metricas_config": configurar_consultas(construir_configuracion_metricas(**config_kwargs)),
    }


@never_cache
@cef_metricas_required
@require_GET
def metricas(request):
    return render(
        request,
        "cef/metricas_cef.html",
        _contexto_pagina_metricas(request),
    )


@never_cache
@cef_metricas_required
@require_GET
def metricas_consulta(request):
    params = _parametros_metricas_autorizados(request)
    try:
        resultado = ejecutar_consulta(params, paginar=True)
    except MetricasValidationError as exc:
        return JsonResponse(
            {"ok": False, "message": str(exc)},
            status=400,
            json_dumps_params={"ensure_ascii": False},
        )
    except Exception:
        logger.exception("Error al calcular una consulta de Métricas CEF")
        return JsonResponse(
            {
                "ok": False,
                "message": "No se pudo calcular la consulta. Revisá los filtros e intentá nuevamente.",
            },
            status=500,
            json_dumps_params={"ensure_ascii": False},
        )

    payload = dict(resultado)
    payload["ok"] = True
    return JsonResponse(
        payload,
        json_dumps_params={"ensure_ascii": False},
    )


def _lista_texto(valor, vacio="Sin selección"):
    if valor is None:
        return vacio
    if isinstance(valor, (list, tuple, set)):
        textos = []
        for item in valor:
            if isinstance(item, dict):
                item = item.get("label") or item.get("nombre") or item.get("value")
            texto = str(item or "").strip()
            if texto:
                textos.append(texto)
        return ", ".join(textos) or vacio
    if isinstance(valor, dict):
        valor = valor.get("label") or valor.get("nombre") or valor.get("value")
    return str(valor or "").strip() or vacio


def _consulta_valor(consulta, *claves, vacio="—"):
    for clave in claves:
        if clave in consulta and consulta[clave] not in (None, "", []):
            return _lista_texto(consulta[clave], vacio=vacio)
    return vacio


def _cefs_consulta_texto(consulta):
    if consulta.get("todos_cef"):
        return "Todos los CEF"
    return _consulta_valor(
        consulta,
        "cef_labels",
        "cefs_etiquetas",
        "cefs",
        vacio="Todos los CEF",
    )


def _filtros_consulta_texto(consulta):
    filtros = consulta.get("filters") or consulta.get("filtros") or []
    partes = []
    for filtro in filtros:
        if not isinstance(filtro, dict):
            continue
        etiqueta = str(filtro.get("label") or filtro.get("key") or "Filtro")
        resumen = str(filtro.get("summary") or "").strip()
        if resumen:
            partes.append(f"{etiqueta}: {resumen}")
    return "; ".join(partes) or "Sin filtros adicionales"


def _valor_excel(valor):
    if isinstance(valor, dict):
        if "value" in valor:
            valor = (
                valor["value"]
                if valor["value"] is not None
                else valor.get("formatted") or valor.get("display") or ""
            )
        elif "valor" in valor:
            valor = (
                valor["valor"]
                if valor["valor"] is not None
                else valor.get("valor_formateado") or ""
            )
        else:
            valor = valor.get("formatted") or valor.get("display") or ""
    if isinstance(valor, str) and valor.startswith(("=", "+", "-", "@")):
        return "'" + valor
    return valor


def _tabla_resultado(resultado):
    tabla = resultado.get("table") or resultado.get("tabla") or {}
    columnas = tabla.get("columns") or tabla.get("columnas") or []
    filas = tabla.get("rows") or tabla.get("filas") or []
    columnas_normalizadas = []
    for indice, columna in enumerate(columnas):
        if isinstance(columna, dict):
            clave = str(
                columna.get("key")
                or columna.get("value")
                or columna.get("id")
                or indice
            )
            etiqueta = str(
                columna.get("label")
                or columna.get("nombre")
                or clave
            )
        else:
            clave = str(indice)
            etiqueta = str(columna)
        columnas_normalizadas.append((clave, etiqueta))
    return columnas_normalizadas, filas


def _agregar_imagen_grafico_excel(
    ws,
    grafico_png_bytes,
    *,
    ancla="A15",
    max_ancho=720,
    max_alto=390,
):
    """Inserta el PNG ya renderizado por Consultas CEF sin alterar su proporción."""
    if not grafico_png_bytes:
        return False

    imagen_stream = BytesIO(grafico_png_bytes)
    imagen = ExcelImage(imagen_stream)
    escala = min(1, max_ancho / imagen.width, max_alto / imagen.height)
    imagen.width = max(1, round(imagen.width * escala))
    imagen.height = max(1, round(imagen.height * escala))
    ws.add_image(imagen, ancla)
    return imagen.height


def _metadatos_estadistica(resultado):
    consulta = resultado.get("query") or resultado.get("consulta") or {}
    definicion = resultado.get("definition") or resultado.get("definicion") or ""
    notas = resultado.get("notes") or resultado.get("notas") or []
    if isinstance(notas, str):
        notas = [notas]
    total = resultado.get("total") or {}
    total_texto = (
        total.get("formatted", "—")
        + (" " + total.get("unit", "") if total.get("unit") != "%" else "")
    )
    metadatos = [
        ("Fecha de generación", timezone.localtime().strftime("%d/%m/%Y %H:%M")),
        ("Categoría", _consulta_valor(consulta, "area_label", "area_etiqueta", "area")),
        (
            "Consulta",
            resultado.get("question")
            or _consulta_valor(
                consulta,
                "indicator_label",
                "indicador_label",
                "indicador_etiqueta",
                "indicador",
            ),
        ),
        ("Ciclos", _consulta_valor(consulta, "cycle_labels", "ciclos_etiquetas", "ciclos")),
        ("CEF", _cefs_consulta_texto(consulta)),
        ("Filtros", _filtros_consulta_texto(consulta)),
        ("Resultados por", _consulta_valor(consulta, "agrupar_label")),
    ]
    comparacion = _consulta_valor(consulta, "comparar_label", vacio="")
    if comparacion:
        metadatos.append(("Comparación", comparacion))
    metadatos.extend([
        ("Total general", total_texto),
        ("Qué incluye el resultado", definicion or "—"),
    ])
    if notas:
        metadatos.append(
            ("Cómo se calculó", " ".join(str(nota) for nota in notas if nota))
        )
    return metadatos


def _agregar_hoja_resumen_estadistico(wb, resultado, grafico_png_bytes):
    """Hoja compacta: resumen arriba y gráfico inmediatamente debajo."""
    ws = wb.create_sheet("Estadística + gráfico")
    ultima_columna = "H"
    ws.merge_cells(f"A1:{ultima_columna}1")
    ws["A1"] = "Estadística CEF"
    ws["A1"].font = Font(bold=True, size=14, color="FFFFFF")
    ws["A1"].fill = PatternFill("solid", fgColor="17365D")
    ws["A1"].alignment = Alignment(horizontal="left", vertical="center")
    ws.row_dimensions[1].height = 24

    fila = 3
    for etiqueta, valor in _metadatos_estadistica(resultado):
        ws.cell(row=fila, column=1, value=etiqueta).font = Font(bold=True, size=9)
        valor_celda = ws.cell(row=fila, column=2, value=_valor_excel(valor))
        valor_celda.alignment = Alignment(wrap_text=True, vertical="top")
        ws.merge_cells(start_row=fila, start_column=2, end_row=fila, end_column=8)
        if etiqueta in {"Qué incluye el resultado", "Cómo se calculó"}:
            ws.row_dimensions[fila].height = 34
        fila += 1

    fila_grafico = fila + 1
    if not _agregar_imagen_grafico_excel(
        ws,
        grafico_png_bytes,
        ancla=f"A{fila_grafico}",
    ):
        ws.cell(
            row=fila_grafico,
            column=1,
            value="No se pudo incorporar el gráfico a este archivo.",
        )

    ws.column_dimensions["A"].width = 22
    for columna in range(2, 9):
        ws.column_dimensions[get_column_letter(columna)].width = 18
    ws.sheet_view.showGridLines = False
    return ws


def _agregar_hoja_datos_estadisticos(wb, resultado):
    """Tabla estadística separada para no empujar el gráfico miles de filas."""
    columnas, filas = _tabla_resultado(resultado)
    ws = wb.create_sheet("Datos estadísticos")

    if not columnas:
        columnas = [("resultado", "Resultado")]
        filas = []

    for indice, (_, etiqueta) in enumerate(columnas, start=1):
        celda = ws.cell(row=1, column=indice, value=etiqueta)
        celda.font = Font(bold=True, color="FFFFFF", size=9)
        celda.fill = PatternFill("solid", fgColor="2F75B5")
        celda.alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)

    for fila_resultado in filas:
        valores = []
        for indice, (clave, _) in enumerate(columnas):
            if isinstance(fila_resultado, (list, tuple)):
                valor = fila_resultado[indice] if indice < len(fila_resultado) else ""
            else:
                valor = fila_resultado.get(clave, "")
            valores.append(_valor_excel(valor))
        ws.append(valores)

    if filas:
        ws.auto_filter.ref = f"A1:{get_column_letter(len(columnas))}{ws.max_row}"

    for indice in range(1, max(1, len(columnas)) + 1):
        letra = get_column_letter(indice)
        longitud = len(str(columnas[indice - 1][1])) if indice <= len(columnas) else 0
        for celdas in ws.iter_rows(min_col=indice, max_col=indice, min_row=2):
            valor = celdas[0].value
            if valor is not None:
                longitud = max(longitud, len(str(valor)))
        ws.column_dimensions[letra].width = min(max(longitud + 2, 12), 48)

    return ws


def _rellenar_hoja_listado(ws, resultado, *, congelar):
    """Construye únicamente la hoja de listado."""
    consulta = resultado.get("query") or resultado.get("consulta") or {}
    definicion = resultado.get("definition") or resultado.get("definicion") or ""
    notas = resultado.get("notes") or resultado.get("notas") or []
    if isinstance(notas, str):
        notas = [notas]
    columnas, filas = _tabla_resultado(resultado)
    total = resultado.get("total") or {}

    if not columnas:
        columnas = [("resultado", "Resultado")]
        filas = []

    ancho = max(2, len(columnas))
    ultima_columna = get_column_letter(ancho)

    ws.merge_cells(f"A1:{ultima_columna}1")
    ws["A1"] = "Consulta CEF - Listado"
    ws["A1"].font = Font(bold=True, size=14, color="FFFFFF")
    ws["A1"].fill = PatternFill("solid", fgColor="17365D")
    ws["A1"].alignment = Alignment(horizontal="left", vertical="center")
    ws.row_dimensions[1].height = 24

    total_texto = (
        total.get("formatted", "—")
        + (" " + total.get("unit", "") if total.get("unit") != "%" else "")
    )
    metadatos = [
        ("Fecha de generación", timezone.localtime().strftime("%d/%m/%Y %H:%M")),
        ("Categoría", _consulta_valor(consulta, "area_label", "area_etiqueta", "area")),
        ("Consulta", _consulta_valor(
            consulta,
            "indicator_label",
            "indicador_label",
            "indicador_etiqueta",
            "indicador",
        )),
        ("Ciclos", _consulta_valor(consulta, "cycle_labels", "ciclos_etiquetas", "ciclos")),
        ("CEF", _cefs_consulta_texto(consulta)),
        ("Filtros", _filtros_consulta_texto(consulta)),
        ("Búsqueda", consulta.get("buscar") or "Sin búsqueda"),
        ("Total del listado", total_texto),
        ("Filas incluidas en este archivo", len(filas)),
        ("Qué incluye el resultado", definicion or "—"),
    ]
    if notas:
        metadatos.append(
            ("Cómo se calculó", " ".join(str(nota) for nota in notas if nota))
        )

    fila = 3
    for etiqueta, valor in metadatos:
        ws.cell(row=fila, column=1, value=etiqueta).font = Font(bold=True, size=9)
        ws.cell(row=fila, column=2, value=_valor_excel(valor)).alignment = Alignment(
            wrap_text=True,
            vertical="top",
        )
        if ancho > 2:
            ws.merge_cells(
                start_row=fila,
                start_column=2,
                end_row=fila,
                end_column=ancho,
            )
        fila += 1

    encabezado = fila + 1
    for indice, (_, etiqueta) in enumerate(columnas, start=1):
        celda = ws.cell(row=encabezado, column=indice, value=etiqueta)
        celda.font = Font(bold=True, color="FFFFFF", size=9)
        celda.fill = PatternFill("solid", fgColor="2F75B5")
        celda.alignment = Alignment(
            horizontal="left",
            vertical="center",
            wrap_text=True,
        )

    for fila_resultado in filas:
        valores = []
        for indice, (clave, _) in enumerate(columnas):
            if isinstance(fila_resultado, (list, tuple)):
                valor = fila_resultado[indice] if indice < len(fila_resultado) else ""
            else:
                valor = fila_resultado.get(clave, "")
            valores.append(_valor_excel(valor))
        ws.append(valores)

    if congelar:
        ws.freeze_panes = f"A{encabezado + 1}"
    if filas:
        ws.auto_filter.ref = (
            f"A{encabezado}:{get_column_letter(len(columnas))}{ws.max_row}"
        )

    for indice in range(1, max(2, len(columnas)) + 1):
        letra = get_column_letter(indice)
        longitud = 0
        for celdas in ws.iter_rows(min_col=indice, max_col=indice):
            valor = celdas[0].value
            if valor is not None:
                longitud = max(longitud, len(str(valor)))
        ws.column_dimensions[letra].width = min(max(longitud + 2, 12), 48)

    return ws


def _agregar_detalles_personas(wb, resultado, *, congelar):
    """Agrega los detalles del listado de alumnos/profesores cuando corresponda."""
    if (
        resultado.get("mode") != "listados"
        or resultado.get("entity") not in {"alumnos", "profesores"}
    ):
        return

    tabla = resultado["table"]
    es_alumno = resultado["entity"] == "alumnos"
    titulo_grupos = "Inscripciones a grupos" if es_alumno else "Asignaciones a grupos"
    titulo_banco = (
        "Registro del alumno en los CEF"
        if es_alumno
        else "Registro del profesor en los CEF"
    )
    etiqueta_persona = "Alumno" if es_alumno else "Profesor"

    for clave, titulo, definiciones in (
        ("relations", titulo_grupos, tabla["detail_columns"]),
        ("bank", titulo_banco, tabla["bank_columns"]),
    ):
        detalle = wb.create_sheet(titulo)
        detalle.append(
            [etiqueta_persona, "Documento", "CUIL"]
            + [columna["label"] for columna in definiciones]
        )
        for persona in tabla["rows"]:
            identidad = [
                persona.get(campo, "")
                for campo in ("persona", "documento", "cuil")
            ]
            for relacion in persona.get(clave, []):
                detalle.append([
                    _valor_excel(valor)
                    for valor in identidad
                    + [
                        relacion.get(columna["key"], "")
                        for columna in definiciones
                    ]
                ])

        for celda in detalle[1]:
            celda.font = Font(bold=True, color="FFFFFF", size=9)
            celda.fill = PatternFill("solid", fgColor="2F75B5")
        if congelar:
            detalle.freeze_panes = "A2"
        detalle.auto_filter.ref = detalle.dimensions
        for indice in range(1, detalle.max_column + 1):
            detalle.column_dimensions[get_column_letter(indice)].width = 24


def _workbook_bytes(wb):
    output = BytesIO()
    wb.save(output)
    return output.getvalue()


def _crear_excel_listado(resultado):
    """Exportación independiente: listado."""
    wb = Workbook()
    ws = wb.active
    ws.title = "Listado"
    _rellenar_hoja_listado(ws, resultado, congelar=True)
    _agregar_detalles_personas(wb, resultado, congelar=True)
    wb.active = ws
    return _workbook_bytes(wb)


def _crear_excel_estadistica_grafico(resultado, grafico_png_bytes):
    """Exportación independiente: descripción estadística + gráfico."""
    wb = Workbook()
    hoja_vacia = wb.active
    resumen = _agregar_hoja_resumen_estadistico(
        wb,
        resultado,
        grafico_png_bytes,
    )
    wb.remove(hoja_vacia)
    wb.active = resumen
    return _workbook_bytes(wb)


def _crear_excel_completo(
    resultado_listado,
    resultado_estadistica,
    grafico_png_bytes,
):
    """Compone las mismas piezas independientes en un único archivo."""
    wb = Workbook()

    listado = wb.active
    listado.title = "Listado"
    _rellenar_hoja_listado(
        listado,
        resultado_listado,
        congelar=False,
    )

    _agregar_hoja_resumen_estadistico(
        wb,
        resultado_estadistica,
        grafico_png_bytes,
    )

    _agregar_detalles_personas(
        wb,
        resultado_listado,
        congelar=False,
    )

    # El completo abre siempre en Listado para que los registros sean evidentes.
    wb.active = listado
    return _workbook_bytes(wb)


def _crear_excel_metricas(
    resultado,
    incluir_grafico=False,
    grafico_png_bytes=None,
    resultado_estadistica=None,
):
    """Router fino: cada salida reutiliza su generador independiente."""
    if resultado_estadistica is not None:
        return _crear_excel_completo(
            resultado,
            resultado_estadistica,
            grafico_png_bytes,
        )

    if resultado.get("mode") == "listados":
        return _crear_excel_listado(resultado)

    return _crear_excel_estadistica_grafico(
        resultado,
        grafico_png_bytes if incluir_grafico else None,
    )


@never_cache
@cef_metricas_required
@require_http_methods(["GET", "POST"])
def metricas_exportar(request):
    params = _parametros_metricas_autorizados(request).copy()
    incluir_grafico = params.get("incluir_grafico") == "1"
    incluir_estadistica = params.get("incluir_estadistica") == "1"
    params.pop("incluir_grafico", None)
    params.pop("incluir_estadistica", None)

    grafico_png = request.FILES.get("grafico_png") if incluir_grafico else None
    grafico_png_bytes = None
    estadistica_serializada = str(request.POST.get("estadistica_params") or "").strip()
    resultado_estadistica = None

    if incluir_grafico:
        if not grafico_png:
            return HttpResponse(
                "No se recibió la imagen del gráfico actual.",
                status=400,
                content_type="text/plain; charset=utf-8",
            )
        if grafico_png.content_type != "image/png" or grafico_png.size > 20 * 1024 * 1024:
            return HttpResponse(
                "La imagen del gráfico no es válida.",
                status=400,
                content_type="text/plain; charset=utf-8",
            )
        grafico_png_bytes = grafico_png.read()
        if not grafico_png_bytes:
            return HttpResponse(
                "La imagen del gráfico está vacía.",
                status=400,
                content_type="text/plain; charset=utf-8",
            )

    try:
        resultado = ejecutar_consulta(params, paginar=False)
        if incluir_estadistica:
            if not estadistica_serializada:
                raise MetricasValidationError(
                    "No se recibió la estadística que debe acompañar al listado."
                )
            params_estadistica = QueryDict(estadistica_serializada, mutable=True)
            params_estadistica = _parametros_metricas_autorizados_desde(
                request, params_estadistica
            )
            resultado_estadistica = ejecutar_consulta(
                params_estadistica,
                paginar=False,
            )
            if resultado_estadistica.get("mode") != "estadisticas":
                raise MetricasValidationError(
                    "La consulta complementaria no corresponde a una estadística."
                )
    except MetricasValidationError as exc:
        return HttpResponse(str(exc), status=400, content_type="text/plain; charset=utf-8")
    except PermissionDenied:
        raise
    except Exception:
        logger.exception("Error al exportar una consulta de Métricas CEF")
        return HttpResponse(
            "No se pudo generar el archivo Excel.",
            status=500,
            content_type="text/plain; charset=utf-8",
        )

    contenido = _crear_excel_metricas(
        resultado,
        incluir_grafico=incluir_grafico and resultado.get("mode") == "estadisticas",
        grafico_png_bytes=grafico_png_bytes,
        resultado_estadistica=resultado_estadistica,
    )
    prefijo = (
        "Consulta_CEF_Completa"
        if incluir_estadistica or (incluir_grafico and resultado.get("mode") == "estadisticas")
        else "Consulta_CEF"
    )
    nombre = f"{prefijo}_{timezone.localtime().strftime('%Y%m%d_%H%M')}.xlsx"
    response = HttpResponse(
        contenido,
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    response["Content-Disposition"] = f'attachment; filename="{nombre}"'
    return response