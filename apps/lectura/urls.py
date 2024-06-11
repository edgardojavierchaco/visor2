from django.urls import path
from .views import mostrar_grafico

app_name='lectura'

urlpatterns = [    
    path('mostrar_grafico/', mostrar_grafico, name='mostrar_grafico'),    
]