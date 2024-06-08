from config.urls import path
from apps.usuarios.views import *
from django.contrib.auth import views as auth_views
from .views import check_user_status, ResetPassWordView, PasswordResetConfirmView


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
    path('reset_password',ResetPassWordView.as_view(),name='reset_password'),
    path('reset/<str:uidb64>/<str:token>/', PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
]