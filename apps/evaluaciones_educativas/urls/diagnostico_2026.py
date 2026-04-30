from django.urls import path
from apps.evaluaciones_educativas.views import diagnostico_2026

app_name = 'diagnostico_2026' 

urlpatterns = [
	path('inicio',diagnostico_2026.inicio, name= 'inicio'),
	
]