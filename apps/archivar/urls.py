from apps.biblioteca.models import FocalLicDocentes
from config.urls import path
from apps.archivar.views import *
from apps.archivar.views_portada import DepGestorPortada
from .views_listdocnodoc import DocentePonMensualListView, NoDocentePonMensualListView, DocentePonMensualSumaListView
from .views_reporteinformes import generar_informe, generar_informe_list
from .view_supervisorexport import export_supervisores_excel

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
]