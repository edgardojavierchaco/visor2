from django.urls import path

from . import views
from .views_gestor import (
    gestor_dashboard,
    gestor_consultas,
    gestor_responder,
    cerrar_consulta,
    gestor_dashboard_interactivo_json,
    gestor_dashboard_interactivo_template
)

from .views_admin import (
    admin_dashboard_interactivo, 
    admin_dashboard_datos, 
    exportar_excel_admin, 
    exportar_pdf_admin
)

app_name='consultasge'

urlpatterns = [
    path("",views.dashboard,name="consultas_dashboard"),
    path("nueva/",views.nueva_consulta,name="consultas_nueva"),
    path("mis/",views.consultas_lista,name="consultas_lista"),
    path("<int:id>/",views.consulta_detalle,name="consulta_detalle"),
    path("gestor/dashboard/", gestor_dashboard, name="gestor_dashboard"),
    path("gestor/", gestor_consultas, name="gestor_consultas"),
    path("gestor/<int:pk>/", gestor_responder, name="gestor_responder"),
    path("gestor/cerrar/<int:pk>/", cerrar_consulta, name="cerrar_consulta"),
    
    # Dashboard interactivo (template + datos JSON)
    path(
        "gestor/dashboard/barras/", 
        gestor_dashboard_interactivo_template, 
        name="gestor_dashboard_barras_template"
    ),
    path(
        "gestor/dashboard/barras/json/", 
        gestor_dashboard_interactivo_json, 
        name="gestor_dashboard_barras_json"
    ),
    
    # Administrador
    path("admin/dashboard/", admin_dashboard_interactivo, name="admin_dashboard_interactivo"),
    path("admin/dashboard/datos/", admin_dashboard_datos, name="admin_dashboard_datos"),
    path("admin/dashboard/exportar/excel/", exportar_excel_admin, name="admin_dashboard_exportar_excel"),
    path("admin/dashboard/exportar/pdf/", exportar_pdf_admin, name="admin_dashboard_exportar_pdf"),
]