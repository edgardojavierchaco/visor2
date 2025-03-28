from django.urls import path
from . import views

app_name='operacha'

urlpatterns = [
    path('cargar/', views.cargar_respuestas, name='cargar')
]
