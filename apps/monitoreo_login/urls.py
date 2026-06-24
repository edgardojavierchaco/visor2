from django.urls import path
from . import views


app_name="monitoreo"


urlpatterns=[


path(
"dashboard/",
views.dashboard_accesos,
name="dashboard"
),


path(
"exportar/",
views.exportar_csv,
name="exportar"
),


]