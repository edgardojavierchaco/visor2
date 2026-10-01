from django.core.paginator import Paginator
from django.shortcuts import render
from django.views.decorators.http import require_GET

from apps.bnhpersonas.monitoring.access import monitoring_required, resolve_scope

from .selectors import (
    ESTADOS_CARGA,
    available_regions,
    general_summary,
    regional_load_summary,
    report_rows,
)
from .services import export_cue_detail_csv, export_regional_summary_csv


@monitoring_required
@require_GET
def estado_carga_regional(request):
    rows = report_rows(request.user, request.GET)
    regional = regional_load_summary(rows)
    summary = general_summary(rows)

    paginator = Paginator(rows, 60)
    page_obj = paginator.get_page(request.GET.get("page"))

    context = {
        "scope": resolve_scope(request.user),
        "regiones": available_regions(request.user),
        "estados": ESTADOS_CARGA,
        "summary": summary,
        "regional_summary": regional,
        "page_obj": page_obj,
        "result_count": len(rows),
        "query": request.GET,
    }
    return render(request, "bnh/reportes/estado_carga_regional.html", context)


@monitoring_required
@require_GET
def exportar_resumen_regional(request):
    rows = report_rows(request.user, request.GET)
    return export_regional_summary_csv(regional_load_summary(rows))


@monitoring_required
@require_GET
def exportar_detalle_cue(request):
    rows = report_rows(request.user, request.GET)
    return export_cue_detail_csv(rows)
