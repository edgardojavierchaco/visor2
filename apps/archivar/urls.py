from apps.biblioteca.models import FocalLicDocentes
from config.urls import path
from apps.archivar.views import *
from apps.archivar.views_portada import DepGestorPortada
from .views_listdocnodoc import DocentePonMensualListView, NoDocentePonMensualListView, DocentePonMensualSumaListView
from .views_reporteinformes import generar_informe, generar_informe_list
from .view_supervisorexport import export_supervisores_excel

from .views_biblio import (
    servicio_prestamo_view, 
    filtrar_servicio_prestamo, 
    filtrar_mat_biblio, 
    servicio_matbiblio_view,
    filtrar_servicio_referencia,
    servicio_referencia_view,
    servicio_referencia_virtual_view,
    filtrar_servicio_referencia_virtual,
    informe_pedagogico_view,
    filtrar_informe_pedagogico,
    asistencia_usuario_view,
    filtrar_asistencia_usuario,
    proceso_tecnico_view,
    filtrar_proceso_tecnico,
    destino_fondos_view,
    filtrar_destino_fondos,
    planillas_anexas_view,
    filtrar_planillas_anexas
)

app_name='archivos'

urlpatterns=[    
    path('crear/',ArchivoCreateView.as_view(),name='crear'),
    path('listar/',ArchivosListView.as_view(),name='listar'),
    path('buscar/',BuscarPDFView.as_view(),name='buscar'), 
    path('editar/<int:pk>/',editar_archivos.as_view(),name='editar'), 
    path('eliminar/<int:pk>/',EliminarArchivosView.as_view(),name='eliminar'), 
    path('portada_gestor/',DepGestorPortada,name='portada_gestor'),
    
    # Nómina Docentes y no Docentes
    path('nom_doc/', DocentePonMensualListView.as_view(), name='nom_doc'),
    path('nom_ndoc/', NoDocentePonMensualListView.as_view(), name='nom_ndoc'),
    path('ver_doc/<str:cuil>/', DocentePonMensualSumaListView.as_view(), name='ver_doc'),
    
    # Bibliotecas - Monitoreo
    path('generar_informe_list/', generar_informe_list, name='generar_informe_list'),
    path('generar_informe/', generar_informe, name='generar_informe'),
    
    # exportar archivo supervisores
    path('export_superv/', export_supervisores_excel, name='export_superv'),
    
    # Resultados
    path("servicio_prestamo/", servicio_prestamo_view, name="servicio_prestamo"),
    path("filtrar_servicio_prestamo/", filtrar_servicio_prestamo, name="filtrar_servicio_prestamo"),
    path("servicio_matbiblio/", servicio_matbiblio_view, name="servicio_matbiblio"),
    path("filtrar_matbiblio/", filtrar_mat_biblio, name="filtrar_matbiblio"),
    path("servicio_referencia/", servicio_referencia_view, name="servicio_referencia"),
    path("filtrar_referencia/", filtrar_servicio_referencia, name="filtrar_referencia"),
    path("servicio_refvirtual/", servicio_referencia_virtual_view, name="servicio_refvirtual"),
    path("filtrar_refvirtual/", filtrar_servicio_referencia_virtual, name="filtrar_refvirtual"),
    path("infopedagres/", informe_pedagogico_view, name="infopedagres"),
    path("filtrar_infopedag/", filtrar_informe_pedagogico, name="filtrar_infopedag"),
    path("asist_usua/", asistencia_usuario_view, name="asist_usua"),
    path("filtrar_asisusua/", filtrar_asistencia_usuario, name="filtrar_asisusua"),
    path("proctecres/", proceso_tecnico_view, name="proctecres"),
    path("filtrar_proctec/", filtrar_proceso_tecnico, name="filtrar_proctec"),
    path("destinofondos/", destino_fondos_view, name="destinofondos"),
    path("filtrar_desfondos/", filtrar_destino_fondos, name="filtrar_desfondos"),
    path("plan_anex/", planillas_anexas_view, name="plan_anex"),
    path("filtrar_plananex/", filtrar_planillas_anexas, name="filtrar_plananex"), 
]