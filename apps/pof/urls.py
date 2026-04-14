from django.urls import path
from .views_unidadservicio import *
from .views_asingacionpof import *
from .views_dashboard import *


app_name = 'pof'

urlpatterns = [    
    # Unidades de Servicio
    path('us/list/', USListView.as_view(), name='us_list'),
    path('us/add/', USCreateView.as_view(), name='us_create'),
    path('us/update/<int:pk>/', USUpdateView.as_view(), name='us_update'),
    path('us/delete/<int:pk>/', USDeleteView.as_view(), name='us_delete'), 
    path('cargar_localidades/', cargar_localidades, name='cargar_localidades'),   
    # Asignaciones Cargos-Horas
    path('cargoshoras/add/', AsignacionPofCreateView.as_view(), name='cargoshoras_create'),
    # Home
    path('dashboard/', DashboardView.as_view(), name='dashboard'),
]

