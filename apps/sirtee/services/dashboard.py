from django.utils import timezone
from datetime import timedelta

from apps.sirtee.models.relevamientos import Relevamiento
from apps.sirtee.models.hallazgos import Hallazgo
from apps.sirtee.models.intervenciones import Intervencion


class SirteeDashboardService:
    """
    Servicio central de KPIs del sistema SIRTEE.
    """

    # --------------------------------------
    # DASHBOARD PRINCIPAL
    # --------------------------------------

    def get_dashboard(self):
        return {
            "relevamientos": self._relevamientos_kpis(),
            "hallazgos": self._hallazgos_kpis(),
            "intervenciones": self._intervenciones_kpis(),
            "resumen_general": self._resumen_general(),
        }

    # --------------------------------------
    # RELEVAMIENTOS
    # --------------------------------------

    def _relevamientos_kpis(self):
        total = Relevamiento.objects.count()

        activos = Relevamiento.objects.filter(finalizado=False).count()
        finalizados = Relevamiento.objects.filter(finalizado=True).count()

        ultimos_7_dias = timezone.now() - timedelta(days=7)
        recientes = Relevamiento.objects.filter(fecha__gte=ultimos_7_dias).count()

        return {
            "total": total,
            "activos": activos,
            "finalizados": finalizados,
            "ultimos_7_dias": recientes,
        }

    # --------------------------------------
    # HALLAZGOS
    # --------------------------------------

    def _hallazgos_kpis(self):
        total = Hallazgo.objects.count()

        abiertos = Hallazgo.objects.filter(estado="ABIERTO").count()
        criticos = Hallazgo.objects.filter(criticidad="CRITICA").count()

        en_analisis = Hallazgo.objects.filter(estado="EN_ANALISIS").count()

        return {
            "total": total,
            "abiertos": abiertos,
            "criticos": criticos,
            "en_analisis": en_analisis,
        }

    # --------------------------------------
    # INTERVENCIONES
    # --------------------------------------

    def _intervenciones_kpis(self):
        total = Intervencion.objects.count()

        pendientes = Intervencion.objects.filter(estado="PENDIENTE").count()
        en_ejecucion = Intervencion.objects.filter(estado="EN_EJECUCION").count()
        finalizadas = Intervencion.objects.filter(estado="FINALIZADA").count()

        retrasadas = Intervencion.objects.filter(
            estado="EN_EJECUCION",
            fecha_estimada_fin__lt=timezone.now().date()
        ).count()

        return {
            "total": total,
            "pendientes": pendientes,
            "en_ejecucion": en_ejecucion,
            "finalizadas": finalizadas,
            "retrasadas": retrasadas,
        }

    # --------------------------------------
    # RESUMEN GENERAL
    # --------------------------------------

    def _resumen_general(self):
        relevamientos = Relevamiento.objects.count()
        hallazgos = Hallazgo.objects.count()
        intervenciones = Intervencion.objects.count()

        return {
            "total_relevamientos": relevamientos,
            "total_hallazgos": hallazgos,
            "total_intervenciones": intervenciones,
            "estado_sistema": "OPERATIVO",
        }