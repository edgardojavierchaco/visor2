from django.db.models import Avg
from django.db.models import Count
from django.db.models import Sum
from django.db.models.functions import TruncMonth

from apps.sirtee.models.empresas import Empresa
from apps.sirtee.models.hallazgos import Hallazgo
from apps.sirtee.models.intervenciones import Intervencion
from apps.sirtee.models.relevamientos import Relevamiento


# ==========================================================
# INTERVENCIONES POR ESTADO
# ==========================================================

def intervenciones_por_estado():

    return (
        Intervencion.objects
        .values(
            "estado__codigo",
            "estado__nombre",
        )
        .annotate(
            cantidad=Count("id")
        )
        .order_by("estado__nombre")
    )


# ==========================================================
# INTERVENCIONES POR PRIORIDAD
# ==========================================================

def intervenciones_por_prioridad():

    return (
        Intervencion.objects
        .values(
            "prioridad__codigo",
            "prioridad__nombre",
        )
        .annotate(
            cantidad=Count("id")
        )
        .order_by("prioridad__nombre")
    )


# ==========================================================
# HALLAZGOS POR CATEGORÍA
# ==========================================================

def hallazgos_por_categoria():

    return (
        Hallazgo.objects
        .values(
            "categoria__codigo",
            "categoria__nombre",
        )
        .annotate(
            cantidad=Count("id")
        )
        .order_by("-cantidad")
    )


# ==========================================================
# HALLAZGOS POR CRITICIDAD
# ==========================================================

def hallazgos_por_criticidad():

    return (
        Hallazgo.objects
        .values(
            "criticidad__codigo",
            "criticidad__nombre",
        )
        .annotate(
            cantidad=Count("id")
        )
        .order_by("-cantidad")
    )


# ==========================================================
# EMPRESAS CON MÁS INTERVENCIONES
# ==========================================================

def empresas_mas_activas():

    return (
        Empresa.objects
        .annotate(
            cantidad=Count(
                "intervenciones"
            )
        )
        .order_by(
            "-cantidad",
            "razon_social",
        )
    )


# ==========================================================
# ORGANISMOS
# ==========================================================

def intervenciones_por_organismo():

    return (
        Intervencion.objects
        .values(
            "organismo_responsable__nombre",
        )
        .annotate(
            cantidad=Count("id")
        )
        .order_by("-cantidad")
    )


# ==========================================================
# FINANCIAMIENTO
# ==========================================================

def intervenciones_por_financiamiento():

    return (
        Intervencion.objects
        .values(
            "fuente_financiamiento__nombre",
        )
        .annotate(
            cantidad=Count("id")
        )
        .order_by("-cantidad")
    )


# ==========================================================
# ESCUELAS CON MÁS HALLAZGOS
# ==========================================================

def escuelas_con_mas_hallazgos():

    return (
        Relevamiento.objects
        .annotate(
            cantidad=Count(
                "hallazgos"
            )
        )
        .order_by("-cantidad")
    )


# ==========================================================
# ESCUELAS CON MÁS INTERVENCIONES
# ==========================================================

def escuelas_con_mas_intervenciones():

    return (
        Relevamiento.objects
        .annotate(
            cantidad=Count(
                "hallazgos__intervenciones"
            )
        )
        .order_by("-cantidad")
    )


# ==========================================================
# COSTOS POR EMPRESA
# ==========================================================

def costos_por_empresa():

    return (
        Empresa.objects
        .annotate(
            costo_estimado=Sum(
                "intervenciones__costo_estimado"
            ),
            costo_real=Sum(
                "intervenciones__costo_real"
            ),
            cantidad=Count(
                "intervenciones"
            ),
        )
        .order_by("-costo_estimado")
    )


# ==========================================================
# COSTOS POR ORGANISMO
# ==========================================================

def costos_por_organismo():

    return (
        Intervencion.objects
        .values(
            "organismo_responsable__nombre",
        )
        .annotate(
            costo=Sum(
                "costo_estimado"
            )
        )
        .order_by("-costo")
    )


# ==========================================================
# COSTOS POR TIPO
# ==========================================================

def costos_por_tipo():

    return (
        Intervencion.objects
        .values(
            "tipo__nombre",
        )
        .annotate(
            costo=Sum(
                "costo_estimado"
            )
        )
        .order_by("-costo")
    )


# ==========================================================
# AVANCE PROMEDIO POR EMPRESA
# ==========================================================

def avance_por_empresa():

    return (
        Empresa.objects
        .annotate(
            avance=Avg(
                "intervenciones__porcentaje_avance"
            )
        )
        .order_by("-avance")
    )


# ==========================================================
# EVOLUCIÓN MENSUAL
# ==========================================================

def evolucion_intervenciones():

    return (
        Intervencion.objects
        .annotate(
            mes=TruncMonth(
                "created"
            )
        )
        .values("mes")
        .annotate(
            cantidad=Count("id")
        )
        .order_by("mes")
    )


# ==========================================================
# COSTOS MENSUALES
# ==========================================================

def evolucion_costos():

    return (
        Intervencion.objects
        .annotate(
            mes=TruncMonth(
                "created"
            )
        )
        .values("mes")
        .annotate(
            costo=Sum(
                "costo_estimado"
            )
        )
        .order_by("mes")
    )


# ==========================================================
# TOP 10 INTERVENCIONES MÁS COSTOSAS
# ==========================================================

def top_intervenciones_costosas():

    return (
        Intervencion.objects
        .select_related(
            "hallazgo",
            "empresa",
        )
        .order_by(
            "-costo_estimado"
        )[:10]
    )


# ==========================================================
# TOP 10 EMPRESAS
# ==========================================================

def top_empresas():

    return (
        Empresa.objects
        .annotate(
            obras=Count(
                "intervenciones"
            )
        )
        .order_by(
            "-obras"
        )[:10]
    )


# ==========================================================
# TOP 10 ESCUELAS
# ==========================================================

def top_escuelas():

    return (
        Relevamiento.objects
        .annotate(
            obras=Count(
                "hallazgos__intervenciones"
            )
        )
        .order_by(
            "-obras"
        )[:10]
    )

# ==========================================================
# COMPATIBILIDAD CON VERSIONES ANTERIORES
# ==========================================================

def intervenciones_por_empresa():
    """
    Alias de compatibilidad.
    """
    return empresas_mas_activas()


def ranking_empresas():
    return empresas_mas_activas()


def empresas_con_mas_intervenciones():
    return empresas_mas_activas()