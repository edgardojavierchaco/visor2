from django.urls import path
from apps.evaluaciones_educativas.views import monitoreo_personas_2026

app_name = "monitoreo_personas_2026"

urlpatterns = [
    path('', monitoreo_personas_2026.monitoreo_regionales, name='monitoreo'),
    path('regional/<str:region>/', monitoreo_personas_2026.detalle_regional, name='detalle_regional'),
]
