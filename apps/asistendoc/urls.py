from django.urls import path
from .views import asistencia_view, asistencia_cargos_view

app_name='asistendoc'

urlpatterns = [    
    path('asistencias/', asistencia_view, name='asistencias'),
    path('asistencia_cargos/', asistencia_cargos_view, name='asistencia_cargos'),
]
