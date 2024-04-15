from config.urls import path
from apps.usuarios.views import *

app_name='usuarios'

urlpatterns=[
    path('listado/',listado_usuarios.as_view(),name='listado'),
    path('crear/',UsuariosCreateView.as_view(),name='crear'),
    path('editar/<int:pk>/',UsuariosEditarView.as_view(),name='editar')
]