from django.core.paginator import Paginator
from django.db.models import Count, Max, Q
from django.http import Http404, JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET

from .access import (
    assert_cue_access,
    monitoring_required,
    resolve_scope,
)

from .selectors import (
    apply_institution_filters,
    coverage_summary,
    enrich_institutions,
    institution_activities,
    institution_audit,
    institution_coverage,
    institution_offers,
    jurisdiction_kpis,
    pof_bnh_breakdown,
    recent_audit,
    regional_summary,
)

from .services import (
    export_institutions,
    export_personnel,
)


# ============================================================
# FILTROS DISPONIBLES
# ============================================================

def _filter_values(rows):

    return {

        "regiones": sorted(
            {
                item["region"]
                for item in rows
                if item["region"]
            }
        ),

        "estados": [
            (
                "SIN_CARGA",
                "Sin carga",
            ),
            (
                "EN_PROCESO",
                "En proceso",
            ),
            (
                "OBSERVADO",
                "Con observaciones",
            ),
            (
                "VALIDADO",
                "Registros validados",
            ),
        ],
    }


# ============================================================
# DASHBOARD GENERAL / REGIONAL / SUPERVISOR
# ============================================================

@monitoring_required
@require_GET
def dashboard(request):

    # --------------------------------------------------------
    # Ámbito del usuario
    # --------------------------------------------------------

    scope = resolve_scope(
        request.user
    )

    # --------------------------------------------------------
    # Todas las instituciones permitidas para el usuario
    #
    # enrich_institutions ya incorpora:
    # - métricas BNH
    # - comparativa RA vs BNH
    # --------------------------------------------------------

    all_rows = enrich_institutions(
        request.user
    )

    # --------------------------------------------------------
    # Valores posibles para filtros
    # --------------------------------------------------------

    filters = _filter_values(
        all_rows
    )

    # --------------------------------------------------------
    # Aplicar filtros seleccionados
    # --------------------------------------------------------

    rows = apply_institution_filters(
        all_rows,
        request.GET,
    )

    # --------------------------------------------------------
    # KPI operativos BNH
    #
    # Ejemplos:
    # - instituciones alcanzadas
    # - con carga
    # - sin carga
    # - personas
    # - actividades
    # - borradores
    # - observados
    # - validados
    # --------------------------------------------------------

    kpis = jurisdiction_kpis(
        request.user,
        rows,
    )

    # --------------------------------------------------------
    # COBERTURA RA 2026 vs BNH
    #
    # IMPORTANTE:
    #
    # No se promedian porcentajes por escuela.
    #
    # Se calcula:
    #
    # SUM(BNH)
    # -------- × 100
    # SUM(RA)
    #
    # sobre el universo actualmente visible/autorizado.
    # --------------------------------------------------------

    ra_coverage = coverage_summary(
        rows
    )

    # --------------------------------------------------------
    # Resumen por Regional
    #
    # También incluye:
    # - cargos RA
    # - cargos BNH
    # - % cobertura cargos
    # - horas RA
    # - horas BNH
    # - % cobertura horas
    # --------------------------------------------------------

    regions = regional_summary(
        rows
    )

    # --------------------------------------------------------
    # CUEANEXO actualmente visibles
    # --------------------------------------------------------

    cues = [
        item["cueanexo"]
        for item in rows
    ]

    # --------------------------------------------------------
    # Paginación
    # --------------------------------------------------------

    paginator = Paginator(
        rows,
        40,
    )

    page_obj = paginator.get_page(
        request.GET.get("page")
    )

    # --------------------------------------------------------
    # Contexto
    # --------------------------------------------------------

    context = {

        "scope":
            scope,

        "kpis":
            kpis,

        "ra_coverage":
            ra_coverage,

        "regional_summary":
            regions,

        "page_obj":
            page_obj,

        "filters":
            filters,

        "audit":
            recent_audit(
                request.user,
                cues,
                limit=20,
            ),

        "query":
            request.GET,

        "result_count":
            len(rows),
    }

    return render(
        request,
        "bnh/monitoreo/dashboard.html",
        context,
    )


# ============================================================
# DETALLE POR CUEANEXO
# ============================================================

@monitoring_required
@require_GET
def institution_detail(
    request,
    cueanexo,
):

    # --------------------------------------------------------
    # Seguridad
    #
    # Verifica que el usuario tenga acceso al CUEANEXO.
    # --------------------------------------------------------

    cueanexo = assert_cue_access(
        request.user,
        cueanexo,
    )

    # --------------------------------------------------------
    # Datos institucionales / ofertas
    # --------------------------------------------------------

    offers = institution_offers(
        request.user,
        cueanexo,
    )

    if not offers:

        # assert_cue_access ya protege el acceso.
        # Este caso cubre una eventual inconsistencia
        # del padrón entre consultas.

        raise Http404(
            "CUEANEXO no disponible."
        )

    # --------------------------------------------------------
    # Actividades BNH
    # --------------------------------------------------------

    activities = institution_activities(
        request.user,
        cueanexo,
    )

    # --------------------------------------------------------
    # Métricas operativas BNH
    # --------------------------------------------------------

    metrics = activities.aggregate(

        cargos=Count(
            "id"
        ),

        personas=Count(
            "persona_id",
            distinct=True,
        ),

        docentes=Count(
            "id",
            filter=Q(
                tipo_personal_id=1
            ),
        ),

        no_docentes=Count(
            "id",
            filter=Q(
                tipo_personal_id=2
            ),
        ),

        borradores=Count(
            "id",
            filter=Q(
                validacion="BORRADOR"
            ),
        ),

        observados=Count(
            "id",
            filter=Q(
                validacion="OBSERVADO"
            ),
        ),

        validados=Count(
            "id",
            filter=Q(
                validacion="VALIDADO"
            ),
        ),

        ultima_actualizacion=Max(
            "fecha_modificacion"
        ),
    )

    # --------------------------------------------------------
    # COBERTURA RA 2026 DEL CUEANEXO
    #
    # Esto va FUERA del aggregate().
    # --------------------------------------------------------

    ra_coverage = institution_coverage(
        request.user,
        cueanexo,
    )

    # --------------------------------------------------------
    # Paginación del personal / actividades
    # --------------------------------------------------------

    paginator = Paginator(
        activities,
        50,
    )

    page_obj = paginator.get_page(
        request.GET.get("page")
    )

    # --------------------------------------------------------
    # Datos de encabezado de institución
    # --------------------------------------------------------

    first = offers[0]

    institution = {

        "cueanexo":
            cueanexo,

        "nom_est":
            first.get(
                "nom_est"
            )
            or "",

        "region":
            first.get(
                "region_loc"
            )
            or "",

        "ofertas": [
            {
                "oferta":
                    row.get(
                        "oferta"
                    )
                    or "",

                "acronimo":
                    row.get(
                        "acronimo"
                    )
                    or "",
            }
            for row in offers
        ],
    }

    # --------------------------------------------------------
    # Render
    # --------------------------------------------------------

    return render(
        request,
        "bnh/monitoreo/institucion.html",
        {

            "scope":
                resolve_scope(
                    request.user
                ),

            "institution":
                institution,

            "metrics":
                metrics,

            "ra_coverage":
                ra_coverage,

            "page_obj":
                page_obj,

            "audit":
                institution_audit(
                    cueanexo,
                    limit=50,
                ),
        },
    )



# ============================================================
# API POF vs BNH POR CEIC
# ============================================================

@monitoring_required
@require_GET
def pof_bnh_breakdown_json(
    request,
    cueanexo,
):
    """
    Devuelve el desglose por CEIC de Reunidas POF vs BNH.

    La seguridad se valida antes de consultar la información.
    """

    cueanexo = assert_cue_access(
        request.user,
        cueanexo,
    )

    data = pof_bnh_breakdown(
        cueanexo,
        anio_objetivo=2026,
    )

    return JsonResponse(
        data,
        safe=True,
    )


# ============================================================
# EXPORTAR INSTITUCIONES
# ============================================================

@monitoring_required
@require_GET
def export_institutions_csv(
    request,
):

    rows = apply_institution_filters(
        enrich_institutions(
            request.user
        ),
        request.GET,
    )

    return export_institutions(
        rows
    )


# ============================================================
# EXPORTAR PERSONAL
# ============================================================

@monitoring_required
@require_GET
def export_personnel_csv(
    request,
):

    rows = apply_institution_filters(
        enrich_institutions(
            request.user
        ),
        request.GET,
    )

    return export_personnel(
        request.user,
        [
            item["cueanexo"]
            for item in rows
        ],
    )


# ============================================================
# RESUMEN JSON
# ============================================================

@monitoring_required
@require_GET
def summary_json(
    request,
):

    # --------------------------------------------------------
    # Mismo universo que el dashboard
    # --------------------------------------------------------

    rows = apply_institution_filters(
        enrich_institutions(
            request.user
        ),
        request.GET,
    )

    # --------------------------------------------------------
    # Construcción del JSON
    # --------------------------------------------------------

    data = {

        "scope":
            resolve_scope(
                request.user
            ).label,

        "kpis":
            jurisdiction_kpis(
                request.user,
                rows,
            ),

        # Comparativa RA 2026 vs BNH vivo
        "cobertura_ra_2026":
            coverage_summary(
                rows
            ),

        "regiones":
            regional_summary(
                rows
            ),
    }

    return JsonResponse(
        data,
        json_dumps_params={
            "ensure_ascii":
                False,
        },
    )