from django.urls import path
from .views import ver_mapas

app_name = 'mapoteca'

urlpatterns = [
    path('mapas/', ver_mapas, name='mapas'),
]
