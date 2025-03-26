from django.urls import path
from . import views

app_name='opechaca'

urlpatterns = [
    # Otras URLs
    path('alumno-autocomplete/', views.alumno_autocomplete, name='alumno_autocomplete'),
    path('respuesta/create/', views.respuesta_create, name='respuesta_create'),
]

