from django.db.models import (
    Avg,
    Count,
    Sum,
    Q,
)
from django.utils import timezone

from apps.sirtee.models.relevamientos import Relevamiento
from apps.sirtee.models.hallazgos import Hallazgo
from apps.sirtee.models.intervenciones import Intervencion
from apps.sirtee.models.empresas import Empresa


# ==========================================================
# KPI GENERALES
# ==========================================================

def indicadores_generales():

    total_relevamientos = Relevamiento.objects.count()

    total_hallazgos = Hallazgo.objects.count()

    total_intervenciones = Intervencion.objects.count()

    total_empresas = Empresa.objects.filter(
        activa=True
    ).count()

    costo_estimado = (
        Intervencion.objects.aggregate(
            total=Sum("costo_estimado")
        )["total"]
        or 0
    )

    costo_real = (
        Intervencion.objects.aggregate(
            total=Sum("costo_real")
        )["total"]
        or 0
    )

    avance = (
        Intervencion.objects.aggregate(
            promedio=Avg("porcentaje_avance")
        )["promedio"]
        or 0
    )

    return {

        "relevamientos": total_relevamientos,

        "hallazgos": total_hallazgos,

        "intervenciones": total_intervenciones,

        "empresas": total_empresas,

        "costo_estimado": costo_estimado,

        "costo_real": costo_real,

        "avance_promedio": round(avance, 2),

    }


# ==========================================================
# TOP ESCUELAS
# ==========================================================

def ranking_escuelas(limit=10):

    return (

        Relevamiento.objects

        .values(
            "cueanexo"
        )

        .annotate(

            hallazgos=Count(
                "hallazgos",
                distinct=True
            ),

            intervenciones=Count(
                "hallazgos__intervenciones",
                distinct=True
            ),

        )

        .order_by(
            "-intervenciones",
            "-hallazgos"
        )[:limit]

    )


# ==========================================================
# TOP EMPRESAS
# ==========================================================

def ranking_empresas(limit=10):

    return (

        Empresa.objects

        .annotate(

            intervenciones=Count(
                "intervenciones"
            ),

            costo=Sum(
                "intervenciones__costo_real"
            ),

            avance=Avg(
                "intervenciones__porcentaje_avance"
            ),

        )

        .order_by(
            "-intervenciones",
            "-costo"
        )[:limit]

    )


# ==========================================================
# ORGANISMOS
# ==========================================================

def ranking_organismos(limit=10):

    return (

        Intervencion.objects

        .values(
            "organismo_responsable__nombre"
        )

        .annotate(

            cantidad=Count("id"),

            costo=Sum("costo_real"),

            avance=Avg("porcentaje_avance"),

        )

        .order_by(
            "-cantidad"
        )[:limit]

    )


# ==========================================================
# COSTOS
# ==========================================================

def indicadores_financieros():

    datos = Intervencion.objects.aggregate(

        estimado=Sum(
            "costo_estimado"
        ),

        real=Sum(
            "costo_real"
        ),

        promedio=Avg(
            "costo_real"
        ),

    )

    datos["estimado"] = datos["estimado"] or 0
    datos["real"] = datos["real"] or 0
    datos["promedio"] = datos["promedio"] or 0

    datos["desvio"] = (
        datos["real"] -
        datos["estimado"]
    )

    return datos


# ==========================================================
# AVANCE PROMEDIO
# ==========================================================

def avance_por_estado():

    return (

        Intervencion.objects

        .values(
            "estado__nombre"
        )

        .annotate(

            promedio=Avg(
                "porcentaje_avance"
            ),

            cantidad=Count("id"),

        )

        .order_by(
            "estado__nombre"
        )

    )


# ==========================================================
# INTERVENCIONES CRÍTICAS
# ==========================================================

def intervenciones_criticas():

    return (

        Intervencion.objects

        .filter(

            prioridad__codigo__in=[

                "MUY_ALTA",

                "ALTA",

            ]

        )

        .select_related(

            "hallazgo",

            "empresa",

            "estado",

            "prioridad",

        )

        .order_by(

            "-prioridad__codigo",

            "fecha_estimada_fin",

        )

    )


# ==========================================================
# OBRAS ATRASADAS
# ==========================================================

def obras_atrasadas():

    hoy = timezone.now().date()

    return (

        Intervencion.objects

        .filter(

            fecha_estimada_fin__lt=hoy

        )

        .exclude(

            estado__codigo="FINALIZADA"

        )

        .select_related(

            "empresa",

            "hallazgo",

            "estado",

        )

        .order_by(

            "fecha_estimada_fin"

        )

    )


# ==========================================================
# ÚLTIMOS MOVIMIENTOS
# ==========================================================

def ultimos_movimientos(limit=20):

    return (

        Intervencion.objects

        .select_related(

            "empresa",

            "hallazgo",

            "estado",

        )

        .order_by(

            "-updated_at"

        )[:limit]

    )


# ==========================================================
# TABLERO EJECUTIVO
# ==========================================================

def tablero_ejecutivo():

    return {

        "kpis": indicadores_generales(),

        "escuelas": ranking_escuelas(),

        "empresas": ranking_empresas(),

        "organismos": ranking_organismos(),

        "finanzas": indicadores_financieros(),

        "avance": avance_por_estado(),

        "criticas": intervenciones_criticas(),

        "atrasadas": obras_atrasadas(),

        "movimientos": ultimos_movimientos(),

    }