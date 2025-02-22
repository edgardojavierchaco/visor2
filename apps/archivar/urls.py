from config.urls import path
from apps.archivar.views import *
from apps.archivar.views_portada import DepGestorPortada

app_name='archivos'

urlpatterns=[    
    path('crear/',ArchivoCreateView.as_view(),name='crear'),
    path('listar/',ArchivosListView.as_view(),name='listar'),
    path('buscar/',BuscarPDFView.as_view(),name='buscar'), 
    path('editar/<int:pk>/',editar_archivos.as_view(),name='editar'), 
    path('eliminar/',EliminarArchivosView.as_view(),name='eliminar'), 
    path('portada_gestor/',DepGestorPortada,name='portada_gestor'),
]