from django.urls import path
from .views import ver_puntajes

app_name = 'evaluaciones'

urlpatterns = [
    path('ver_puntajes/<int:alumno_id>/', ver_puntajes, name='ver_puntajes'),
]