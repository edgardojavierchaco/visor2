from django.db.models import Count, Sum
from django.db.models.functions import TruncMonth

from apps.sirtee.models.intervenciones import Intervencion
from apps.sirtee.models.hallazgos import Hallazgo
from apps.sirtee.models.empresas import Empresa


# ==========================================================
# DASHBOARD
# ==========================================================

def chart_intervenciones_estado():
    """
    Gráfico de barras:
    Cantidad de intervenciones por estado.
    """

    datos = (
        Intervencion.objects
        .values("estado__nombre")
        .annotate(total=Count("id"))
        .order_by("estado__nombre")
    )

    return {
        "labels": [
            x["estado__nombre"]
            for x in datos
        ],
        "datasets": [
            {
                "label": "Intervenciones",
                "data": [
                    x["total"]
                    for x in datos
                ],
            }
        ],
    }


# ==========================================================

def chart_intervenciones_tipo():
    """
    Pie chart.
    """

    datos = (
        Intervencion.objects
        .values("tipo__nombre")
        .annotate(total=Count("id"))
        .order_by("tipo__nombre")
    )

    return {
        "labels": [
            x["tipo__nombre"]
            for x in datos
        ],
        "datasets": [
            {
                "label": "Tipos",
                "data": [
                    x["total"]
                    for x in datos
                ],
            }
        ],
    }


# ==========================================================

def chart_hallazgos_categoria():
    """
    Hallazgos por categoría.
    """

    datos = (
        Hallazgo.objects
        .values("tipo_hallazgo__nombre")
        .annotate(total=Count("id"))
        .order_by("tipo_hallazgo__nombre")
    )

    return {
        "labels": [
            x["tipo_hallazgo__nombre"]
            for x in datos
        ],
        "datasets": [
            {
                "label": "Hallazgos",
                "data": [
                    x["total"]
                    for x in datos
                ],
            }
        ],
    }


# ==========================================================

def chart_empresas():
    """
    Empresas con mayor cantidad de intervenciones.
    """

    datos = (
        Empresa.objects
        .annotate(
            total=Count("intervenciones")
        )
        .order_by("-total")[:10]
    )

    return {
        "labels": [
            empresa.razon_social
            for empresa in datos
        ],
        "datasets": [
            {
                "label": "Intervenciones",
                "data": [
                    empresa.total
                    for empresa in datos
                ],
            }
        ],
    }


# ==========================================================

def chart_costos():
    """
    Comparación costo estimado vs real.
    """

    totales = Intervencion.objects.aggregate(
        estimado=Sum("costo_estimado"),
        real=Sum("costo_real"),
    )

    return {
        "labels": [
            "Estimado",
            "Real",
        ],
        "datasets": [
            {
                "label": "Costos",
                "data": [
                    float(
                        totales["estimado"] or 0
                    ),
                    float(
                        totales["real"] or 0
                    ),
                ],
            }
        ],
    }


# ==========================================================

def chart_avance():
    """
    Distribución del avance.
    """

    rangos = [
        (
            "0-25%",
            Intervencion.objects.filter(
                porcentaje_avance__lte=25
            ).count(),
        ),
        (
            "26-50%",
            Intervencion.objects.filter(
                porcentaje_avance__gt=25,
                porcentaje_avance__lte=50,
            ).count(),
        ),
        (
            "51-75%",
            Intervencion.objects.filter(
                porcentaje_avance__gt=50,
                porcentaje_avance__lte=75,
            ).count(),
        ),
        (
            "76-100%",
            Intervencion.objects.filter(
                porcentaje_avance__gt=75
            ).count(),
        ),
    ]

    return {
        "labels": [
            r[0]
            for r in rangos
        ],
        "datasets": [
            {
                "label": "Intervenciones",
                "data": [
                    r[1]
                    for r in rangos
                ],
            }
        ],
    }


# ==========================================================

def chart_evolucion():
    """
    Evolución mensual de intervenciones.
    """

    datos = (
        Intervencion.objects
        .annotate(
            mes=TruncMonth("fecha_inicio")
        )
        .values("mes")
        .annotate(total=Count("id"))
        .order_by("mes")
    )

    return {
        "labels": [
            item["mes"].strftime("%m/%Y")
            if item["mes"] else ""
            for item in datos
        ],
        "datasets": [
            {
                "label": "Intervenciones",
                "data": [
                    item["total"]
                    for item in datos
                ],
            }
        ],
    }


# ==========================================================

def chart_prioridades():
    """
    Distribución por prioridad.
    """

    datos = (
        Intervencion.objects
        .values("prioridad__nombre")
        .annotate(total=Count("id"))
        .order_by("prioridad__nombre")
    )

    return {
        "labels": [
            x["prioridad__nombre"]
            for x in datos
        ],
        "datasets": [
            {
                "label": "Prioridades",
                "data": [
                    x["total"]
                    for x in datos
                ],
            }
        ],
    }


# ==========================================================

def dashboard_charts():
    """
    Devuelve todos los gráficos utilizados
    por el Dashboard institucional.
    """

    return {
        "estado": chart_intervenciones_estado(),
        "tipo": chart_intervenciones_tipo(),
        "hallazgos": chart_hallazgos_categoria(),
        "empresas": chart_empresas(),
        "costos": chart_costos(),
        "avance": chart_avance(),
        "evolucion": chart_evolucion(),
        "prioridades": chart_prioridades(),
    }