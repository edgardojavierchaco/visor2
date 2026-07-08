from django.http import HttpResponse
from django.views.generic import TemplateView, View

import csv
import json

from apps.sirtee.models.intervenciones import Intervencion

from apps.sirtee.reportes.metrics import (
    dashboard_metrics,
)

from apps.sirtee.reportes.charts import (
    dashboard_charts,
)

from apps.sirtee.reportes.queries import (
    empresas_mas_activas,
    intervenciones_por_estado,
)


class ReporteDashboardView(TemplateView):
    """
    Dashboard institucional SIRTEE.
    """

    template_name = "sirtee/reportes/dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # =====================================
        # KPIs
        # =====================================

        context["metrics"] = dashboard_metrics()

        # =====================================
        # TABLAS
        # =====================================

        context["empresas"] = (
            empresas_mas_activas()
        )

        context["estados"] = (
            intervenciones_por_estado()
        )

        # =====================================
        # CHARTS
        # =====================================

        charts = dashboard_charts()

        context["chart_estado"] = json.dumps(
            charts["estado"]
        )

        context["chart_tipo"] = json.dumps(
            charts["tipo"]
        )

        context["chart_hallazgos"] = json.dumps(
            charts["hallazgos"]
        )

        context["chart_empresas"] = json.dumps(
            charts["empresas"]
        )

        context["chart_costos"] = json.dumps(
            charts["costos"]
        )

        context["chart_avance"] = json.dumps(
            charts["avance"]
        )

        context["chart_evolucion"] = json.dumps(
            charts["evolucion"]
        )

        context["chart_prioridades"] = json.dumps(
            charts["prioridades"]
        )

        return context


class ExportIntervencionesCSV(View):
    """
    Exportación completa de intervenciones.
    """

    def get(self, request):

        response = HttpResponse(
            content_type="text/csv"
        )

        response[
            "Content-Disposition"
        ] = (
            'attachment; '
            'filename="intervenciones.csv"'
        )

        writer = csv.writer(response)

        writer.writerow(
            [
                "ID",
                "Título",
                "Escuela",
                "Empresa",
                "Estado",
                "Tipo",
                "Prioridad",
                "Avance",
                "Costo estimado",
                "Costo real",
                "Fecha inicio",
                "Fecha fin",
            ]
        )

        queryset = (
            Intervencion.objects
            .select_related(
                "hallazgo",
                "hallazgo__relevamiento",
                "empresa",
                "estado",
                "tipo",
                "prioridad",
            )
            .order_by("id")
        )

        for obj in queryset:

            writer.writerow(
                [
                    obj.id,
                    obj.titulo,
                    getattr(
                        obj.hallazgo.relevamiento,
                        "cueanexo",
                        "",
                    ),
                    (
                        obj.empresa.razon_social
                        if obj.empresa
                        else ""
                    ),
                    (
                        obj.estado.nombre
                        if obj.estado
                        else ""
                    ),
                    (
                        obj.tipo.nombre
                        if obj.tipo
                        else ""
                    ),
                    (
                        obj.prioridad.nombre
                        if obj.prioridad
                        else ""
                    ),
                    obj.porcentaje_avance,
                    obj.costo_estimado,
                    obj.costo_real,
                    obj.fecha_inicio,
                    obj.fecha_fin,
                ]
            )

        return response