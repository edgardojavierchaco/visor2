from django.urls import path
from .views import mostrar_registros

app_name='accesos'

urlpatterns = [
    path('registros/', mostrar_registros, name='registros'),    
]
