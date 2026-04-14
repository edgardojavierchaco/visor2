from django.urls import path
from . import views

app_name='consultas_api'

urlpatterns = [
    path('consulta/', views.consulta_form_view, name='consulta_form'),
    path('consulta-renpe/', views.consulta_renpe_form_view, name='consulta_renpe_form'),
    path('enviar-consulta/', views.enviar_consulta_ajax, name='enviar_consulta_ajax'),
    path('enviar-consulta-renpe/', views.enviar_consulta_renpe_ajax, name='enviar_consulta_renpe_ajax'),
    path('monitoreo/', views.monitoreo_consultas, name='monitoreo_consultas'),
    path('monitoreo_renpe/', views.monitoreo_consultas_renpe, name='monitoreo_consultas_renpe'),
    path('actualizar-estado/<int:consulta_id>/', views.actualizar_estado, name='actualizar_estado'),
    path('actualizar-estado-renpe/<int:consulta_id>/', views.actualizar_estado_renpe, name='actualizar_estado_renpe'),
    path("exportar_excel/", views.exportar_excel, name="exportar_excel"),
    path("exportar_excel_renpe/", views.exportar_excel_renpe, name="exportar_excel_renpe"),
    path("consulta/docente/", views.consulta_renpe_view, name="consulta_docente_renpe"),
    path("consulta/exito/docente/", views.consulta_renpe_exito, name="consulta_renpe_docente_exito"),
]