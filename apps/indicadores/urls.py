from django.urls import path
from .views import filter_data_evolucion_matricula, filter_data_retencion, filter_data_efec_aban_rep, filter_data_sobreedad
from apps.indicadores import viewssecundaria, viewshorassec, viewsprimaria

app_name='indicadores'

urlpatterns = [
    path('evolucion/', filter_data_evolucion_matricula, name='evolucion'),
    path('retencion/', filter_data_retencion, name='retencion'),
    path('efectiva/', filter_data_efec_aban_rep, name='efectiva'),
    path('sobreedad/', filter_data_sobreedad, name='sobreedad'),
    path('efectivasec/', viewssecundaria.filter_data_efec_aban_rep, name='efectivasec'),
    path('efectivasectotal/', viewssecundaria.filter_data_efec_aban_rep_total, name='efectivasectotal'),
    path('efectivaprim/', viewsprimaria.filter_data_efec_aban_rep, name='efectivaprim'),
    path('efectivaprimtotal/', viewsprimaria.filter_data_efec_aban_rep_total, name='efectivaprimtotal'),
    path('docentes-por-horas/', viewshorassec.DocentesPorHorasView.as_view(), name='docentes-por-horas'),
    
]