from django.http import HttpResponse
from django.views import View
import csv

from apps.sirtee.models.relevamientos import Relevamiento
from apps.sirtee.models.hallazgos import Hallazgo
from apps.sirtee.models.intervenciones import Intervencion

from apps.sirtee.security.permissions import SirteePermissions


class ReporteGeneralView(View):

    def get(self, request):

        perms = SirteePermissions(request.user)

        relevamientos = perms.filter_relevamientos(
            Relevamiento.objects.all()
        )

        hallazgos = perms.filter_hallazgos(
            Hallazgo.objects.all()
        )

        intervenciones = perms.filter_intervenciones(
            Intervencion.objects.all()
        )

        return HttpResponse(
            f"""
            RELEVAMIENTOS: {relevamientos.count()}
            HALLAZGOS: {hallazgos.count()}
            INTERVENCIONES: {intervenciones.count()}
            """,
            content_type="text/plain"
        )


class ExportRelevamientosCSV(View):

    def get(self, request):

        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="relevamientos.csv"'

        writer = csv.writer(response)
        writer.writerow(["ID", "Escuela", "Estado", "Fecha"])

        for r in Relevamiento.objects.all():
            writer.writerow([
                r.id,
                r.escuela.nom_est,
                r.estado,
                r.fecha
            ])

        return response