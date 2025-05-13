from django.urls import path
from .views_dash import (
    DashboardSeguimientoSIE2025View,
    seguimiento_sie_json,
    seguimiento_sie_niveles_json
)
from .views import (
    SeguimientoSIE2025ListView, 
    dashboard_prueba, 
    dashboard_prueba_superv, 
    dashboard_prueba_func, 
    dashboard_prueba_regional,
    dashboard_prueba_fluidez,
)

app_name = 'indicsie'

urlpatterns = [
    path('seguimiento/', SeguimientoSIE2025ListView.as_view(), name='seguimiento'),
    path('dashboard/', DashboardSeguimientoSIE2025View.as_view(), name='dashboard_seguimiento_sie'),
    path('api/seguimiento-sie/', seguimiento_sie_json, name='seguimiento_sie_json'),
    path('api/seguimiento-sie-niveles/', seguimiento_sie_niveles_json, name='seguimiento_sie_niveles_json'),
    path('prueba/', dashboard_prueba, name='prueba'),
    path('prueba_superv/', dashboard_prueba_superv, name='prueba_superv'),
    path('prueba_func/', dashboard_prueba_func, name='prueba_func'),
    path('prueba_reg/', dashboard_prueba_regional, name='prueba_regional'),
    path('prueba_fluidez/', dashboard_prueba_fluidez, name='prueba_fluidez'),
]