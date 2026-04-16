from config.urls import path
from apps.usuarios.views import *
from apps.usuarios.views_users import UserListView, DashboardView, UserCreateView
from django.contrib.auth import views as auth_views
from .views import check_user_status
from apps.usuarios.views_admin import (
     estado_sync, 
    iniciar_sync,
    progreso_sync, 
    exportar_rechazados_excel,
    limpiar_historial,
    cancelar_sync,
    sync_stream
)
from .views_abm import (
    usuarios_list,
    usuario_create,
    usuario_update,
    usuario_delete,
    usuarios_list_ajax
)
from .views_trace import (
    trazabilidad_panel,
    trazabilidad_data,
    trazabilidad_resumen,
    trazabilidad_usuario
)
from .views_trace_dashboard import dashboard_data, dashboard_view
from .views_estado import guardar_estado


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
    path("sync/", estado_sync, name="sync"),
    path("sync/iniciar/", iniciar_sync, name="iniciar_sync"),
    path("sync/progreso/", progreso_sync, name="progreso_sync"),
    path("sync/exportar-rechazados/", exportar_rechazados_excel, name="exportar_rechazados"),
    path("sync/limpiar/", limpiar_historial, name="limpiar_historial"),
    path("sync/cancelar/", cancelar_sync, name="cancelar_sync"),
    path("sync/stream/", sync_stream, name="sync_stream"),
    path('usuarios/', usuarios_list, name='usuarios_list'), 
    path("usuarios/data/", usuarios_list_ajax, name="usuarios_list_ajax"),
    path('usuarios/crear/', usuario_create, name='usuario_create'),
    path('usuarios/<int:pk>/editar/', usuario_update, name='usuario_update'),
    path('usuarios/<int:pk>/eliminar/', usuario_delete, name='usuario_delete'),
    path('trazabilidad/', trazabilidad_panel, name='trazabilidad'),
    path('trazabilidad/data/', trazabilidad_data, name='trazabilidad_data'),
    path('trazabilidad/resumen/', trazabilidad_resumen),
    path('trazabilidad/<str:username>/', trazabilidad_usuario),
    path('dashboard_trace/data/', dashboard_data, name='dashboard_trace_data'),
    path('dashboard_trace/', dashboard_view, name='dashboard_trace'),
    path('guardar-estado/', guardar_estado, name='guardar_estado'),
]