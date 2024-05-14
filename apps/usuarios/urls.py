from config.urls import path
from apps.usuarios.views import *

app_name='usuarios'

urlpatterns=[
    path('listado/',listado_usuarios.as_view(),name='listado')
]