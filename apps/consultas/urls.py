from django.urls import path
from . import views

app_name='consultas_api'

urlpatterns = [
    path('consulta/', views.consulta_form_view, name='consulta_form'),
    path('consulta-renpe/', views.consulta_renpe_form_view, name='consulta_renpe_form'),
    path('enviar-consulta/', views.enviar_consulta_ajax, name='enviar_consulta_ajax'),
    path('enviar-consulta-renpe/', views.enviar_consulta_renpe_ajax, name='enviar_consulta_renpe_ajax'),
    path('monitoreo/', views.monitoreo_consultas, name='monitoreo_consultas'),
    path('actualizar-estado/<int:consulta_id>/', views.actualizar_estado, name='actualizar_estado'),
]