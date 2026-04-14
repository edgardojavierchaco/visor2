from django.urls import path
from .views import obtener_nombre_cuit_view

app_name='al'

urlpatterns = [
    path("obtener_nombre_cuit/", obtener_nombre_cuit_view, name="obtener_nombre_cuit"),
]
