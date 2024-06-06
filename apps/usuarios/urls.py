from config.urls import path
from apps.usuarios.views import *
from django.contrib.auth import views as auth_views


app_name='usuarios'

urlpatterns=[
    path('listado/',listado_usuarios.as_view(),name='listado'),
    path('listado_op/',listado_usuarios_op.as_view(),name='listado_op'),
    path('crear/',crear_usuarios.as_view(),name='crear'),
    path('editar/', editar_usuarios.as_view(), name='editar'),
    path('editar_op/', editar_usuarios_op.as_view(), name='editar_op'),
    path('eliminar/', EliminarUsuarioView.as_view(), name='eliminar'),
    path('eliminar_op/', EliminarUsuarioView_op.as_view(), name='eliminar_op'),
    path('registro/',registrar_usuarios.as_view(), name='registro'),
    
]