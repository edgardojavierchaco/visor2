from config.urls import path
from apps.usuarios.views import *

app_name='usuarios'

urlpatterns=[
    path('listado/',listado_usuarios.as_view(),name='listado'),
    path('crear/',crear_usuarios.as_view(),name='crear'),
    path('editar/', editar_usuarios.as_view(), name='editar'),
    path('eliminar/', EliminarUsuarioView.as_view(), name='eliminar'),
]