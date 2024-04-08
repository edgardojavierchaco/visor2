from config.urls import path
from apps.usuarios.views import *

app_name='usuarios'

urlpatterns=[
    path('listado/',UsuariosListView.as_view(),name='Listado_usuarios'),
    path('crear/',UsuariosCreateView.as_view(),name='Crear_usuario'),
    path('editar/<int:pk>/',UsuariosUpdateView.as_view(),name='Editar_usuario'),
    path('eliminar/<int:pk>/',UsuariosDeleteView.as_view(),name='Eliminar_usuario'),
]