from django.urls import path
from .views_dash import (
    DashboardSeguimientoSIE2025View,
    seguimiento_sie_json,
    seguimiento_sie_niveles_json
)
from .views import SeguimientoSIE2025ListView, dashboard_prueba

app_name = 'indicsie'

urlpatterns = [
    path('seguimiento/', SeguimientoSIE2025ListView.as_view(), name='seguimiento'),
    path('dashboard/', DashboardSeguimientoSIE2025View.as_view(), name='dashboard_seguimiento_sie'),
    path('api/seguimiento-sie/', seguimiento_sie_json, name='seguimiento_sie_json'),
    path('api/seguimiento-sie-niveles/', seguimiento_sie_niveles_json, name='seguimiento_sie_niveles_json'),
    path('prueba/', dashboard_prueba, name='prueba'),

]