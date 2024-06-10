from django.urls import path
from .views import filter_data_evolucion_matricula, filter_data_retencion

app_name='indicadores'

urlpatterns = [
    path('evolucion/', filter_data_evolucion_matricula, name='evolucion'),
    path('retencion/', filter_data_retencion, name='retencion'),
]