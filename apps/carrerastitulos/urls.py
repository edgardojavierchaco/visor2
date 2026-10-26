from django.urls import path
from . import views

app_name = 'carrerastitulos'
urlpatterns = [
    path('que-estudiar/', views.public, name='publico'),
    path('observatorio/carreras/', views.observatorio, name='observatorio'),
    path('carreras/api/resultados/', views.api_resultados, name='resultados'),
    path('carreras/api/resumen/', views.api_resumen, name='resumen'),
    path('carreras/api/analisis/', views.api_analisis, name='analisis'),
    path('carreras/api/mapa/', views.api_mapa, name='mapa'),
    path('carreras/api/institucion/<str:cueanexo>/', views.api_institucion, name='institucion'),
    path('carreras/exportar.csv', views.exportar_csv, name='exportar'),
]
