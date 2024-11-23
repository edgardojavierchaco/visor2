from config.urls import path
from apps.usuarios.views import *
from apps.usuarios.views_users import UserListView, DashboardView, UserCreateView
from django.contrib.auth import views as auth_views
from .views import check_user_status


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
    path('api/check_user_status/', check_user_status, name='check_user_status'),  
    path('user_list/', UserListView.as_view(), name='user_list'),
    path('dashboard/',DashboardView.as_view(),name='dashboard'),
    path('user_create/',UserCreateView.as_view(),name='user_create'),
]