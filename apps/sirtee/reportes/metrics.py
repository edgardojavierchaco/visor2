from django.db.models import Avg
from django.db.models import Count
from django.db.models import Sum

from apps.sirtee.models.relevamientos import Relevamiento
from apps.sirtee.models.hallazgos import Hallazgo
from apps.sirtee.models.intervenciones import Intervencion
from apps.sirtee.models.empresas import Empresa


# ==========================================================
# KPIs GENERALES
# ==========================================================


def total_relevamientos():
    return Relevamiento.objects.count()


def total_hallazgos():
    return Hallazgo.objects.count()


def total_intervenciones():
    return Intervencion.objects.count()


def total_empresas():
    return Empresa.objects.count()


def empresas_activas():
    return Empresa.objects.filter(
        activa=True
    ).count()


# ==========================================================
# INTERVENCIONES POR ESTADO
# ==========================================================


def intervenciones_pendientes():

    return Intervencion.objects.filter(
        estado__codigo="PENDIENTE"
    ).count()


def intervenciones_programadas():

    return Intervencion.objects.filter(
        estado__codigo="PROGRAMADA"
    ).count()


def intervenciones_en_ejecucion():

    return Intervencion.objects.filter(
        estado__codigo="EN_EJECUCION"
    ).count()


def intervenciones_finalizadas():

    return Intervencion.objects.filter(
        estado__codigo="FINALIZADA"
    ).count()


def intervenciones_canceladas():

    return Intervencion.objects.filter(
        estado__codigo="CANCELADA"
    ).count()


# ==========================================================
# AVANCE
# ==========================================================


def avance_promedio():

    valor = (
        Intervencion.objects.aggregate(
            promedio=Avg(
                "porcentaje_avance"
            )
        )["promedio"]
    )

    return round(valor or 0, 2)


# ==========================================================
# COSTOS
# ==========================================================


def costo_estimado_total():

    return (
        Intervencion.objects.aggregate(
            total=Sum(
                "costo_estimado"
            )
        )["total"]
        or 0
    )


def costo_real_total():

    return (
        Intervencion.objects.aggregate(
            total=Sum(
                "costo_real"
            )
        )["total"]
        or 0
    )


def diferencia_costos():

    return (
        costo_real_total()
        - costo_estimado_total()
    )


# ==========================================================
# HALLAZGOS
# ==========================================================


def hallazgos_resueltos():

    return Hallazgo.objects.filter(
        estado__codigo="RESUELTO"
    ).count()


def hallazgos_pendientes():

    return Hallazgo.objects.exclude(
        estado__codigo="RESUELTO"
    ).count()


# ==========================================================
# EMPRESAS
# ==========================================================


def empresas_con_intervenciones():

    return Empresa.objects.filter(
        intervenciones__isnull=False
    ).distinct().count()


def empresas_sin_intervenciones():

    return Empresa.objects.filter(
        intervenciones__isnull=True
    ).count()


# ==========================================================
# RESUMEN GENERAL
# ==========================================================


def dashboard_metrics():

    return {

        # -------------------------
        # Relevamientos
        # -------------------------

        "relevamientos":
            total_relevamientos(),

        "hallazgos":
            total_hallazgos(),

        "intervenciones":
            total_intervenciones(),

        "empresas":
            total_empresas(),

        "empresas_activas":
            empresas_activas(),

        # -------------------------
        # Estados
        # -------------------------

        "pendientes":
            intervenciones_pendientes(),

        "programadas":
            intervenciones_programadas(),

        "en_ejecucion":
            intervenciones_en_ejecucion(),

        "finalizadas":
            intervenciones_finalizadas(),

        "canceladas":
            intervenciones_canceladas(),

        # -------------------------
        # Avance
        # -------------------------

        "avance_promedio":
            avance_promedio(),

        # -------------------------
        # Costos
        # -------------------------

        "costo_estimado":
            costo_estimado_total(),

        "costo_real":
            costo_real_total(),

        "diferencia":
            diferencia_costos(),

        # -------------------------
        # Hallazgos
        # -------------------------

        "hallazgos_resueltos":
            hallazgos_resueltos(),

        "hallazgos_pendientes":
            hallazgos_pendientes(),

        # -------------------------
        # Empresas
        # -------------------------

        "empresas_con_intervenciones":
            empresas_con_intervenciones(),

        "empresas_sin_intervenciones":
            empresas_sin_intervenciones(),

    }

# ==========================================================
# COMPATIBILIDAD CON VERSIONES ANTERIORES
# ==========================================================

def obtener_kpis_generales():
    return dashboard_metrics()


def resumen_general():
    return dashboard_metrics()


def metricas_dashboard():
    return dashboard_metrics()
    return dashboard_metrics()