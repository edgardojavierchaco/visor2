from django.urls import path
from .views import tu_vista

app_name='lectocomprension'

urlpatterns = [    
    path('resultados/', tu_vista, name='resultados'),    
]