from django.urls import path

from . import views

app_name = "monitoring"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path(
        "institucion/<str:cueanexo>/",
        views.institution_detail,
        name="institution_detail",
    ),
    path(
        "exportar/instituciones.csv",
        views.export_institutions_csv,
        name="export_institutions",
    ),
    path(
        "exportar/personal.csv",
        views.export_personnel_csv,
        name="export_personnel",
    ),
    path(
        "api/institucion/<str:cueanexo>/pof-bnh/",
        views.pof_bnh_breakdown_json,
        name="pof_bnh_breakdown",
    ),
    path(
        "api/resumen/",
        views.summary_json,
        name="summary_json",
    ),
]
