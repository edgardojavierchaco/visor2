from django.urls import path

from . import views

app_name = "reportes"

urlpatterns = [
    path(
        "estado-carga-regional/",
        views.estado_carga_regional,
        name="estado_carga_regional",
    ),
    path(
        "estado-carga-regional/exportar-resumen.csv",
        views.exportar_resumen_regional,
        name="exportar_resumen_regional",
    ),
    path(
        "estado-carga-regional/exportar-detalle.csv",
        views.exportar_detalle_cue,
        name="exportar_detalle_cue",
    ),
]
