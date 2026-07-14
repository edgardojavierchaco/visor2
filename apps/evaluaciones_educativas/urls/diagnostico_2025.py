from django.urls import path
from ..views import diagnostico_2025 as views_d25

app_name = 'diagnostico_2025'

urlpatterns = [
    path('analisis/', views_d25.analisis_evaluacion, name='analisis_evaluacion'),
]
