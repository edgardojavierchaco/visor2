from django.urls import path
from .views import mostrar_grafico

app_name='lectocomprension'

urlpatterns = [    
    path('resultados/', mostrar_grafico, name='resultados'),    
]