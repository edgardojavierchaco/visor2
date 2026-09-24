from django.urls import path

from . import views


app_name = "asistencia_dashboard"


urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("api/filtros/", views.api_filtros, name="api_filtros"),
    path("api/semanas/", views.api_semanas, name="api_semanas"),
    path("api/resumen/", views.api_resumen, name="api_resumen"),
    path("api/evolucion/", views.api_evolucion, name="api_evolucion"),
    path("api/niveles/", views.api_niveles, name="api_niveles"),
    path("api/ranking/", views.api_ranking, name="api_ranking"),
    path("api/secciones/", views.api_secciones, name="api_secciones"),
    path("api/establecimientos/", views.api_establecimientos, name="api_establecimientos"),
    path("api/alertas/", views.api_alertas, name="api_alertas"),
    path("api/mensual/", views.api_mensual, name="api_mensual"),
    path("api/calidad-registro/", views.api_calidad_registro, name="api_calidad_registro"),
    path("api/alertas-alumnos/", views.api_alertas_alumnos, name="api_alertas_alumnos"),

    path("api/resumen-alertas-semana/", views.api_resumen_alertas_semana, name="api_resumen_alertas_semana"),
    path("api/tendencia-alertas/", views.api_tendencia_alertas, name="api_tendencia_alertas"),
    path("api/ranking-alertas/", views.api_ranking_alertas, name="api_ranking_alertas"),
]
