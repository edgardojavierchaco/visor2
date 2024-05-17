from config.urls import path
from apps.archivar.views import *

app_name='archivos'

urlpatterns=[    
    path('crear/',ArchivoCreateView.as_view(),name='crear'),
    path('listar/',ArchivosListView.as_view(),name='listar'),
    path('buscar/',BuscarPDFView.as_view(),name='buscar'), 
    path('editar/',editar_archivos.as_view(),name='editar'), 
    path('eliminar/',EliminarArchivosView.as_view(),name='eliminar'), 
]