#from django.urls import path
from config.urls import path
from . import views, views2,viewscueradio

app_name='mapas'

urlpatterns=[
    path('filtrado/',views.filtrado,name='filtrado'),
    path('filter/',views.filter_data,name='filter'), # type: ignore
    path('listados/',views.filtrar_tablas_view,name='listados'),
    path('puntos/',views2.mapapuntos,name='puntos'), 
    path('filcueradio/',viewscueradio.filtrado_cueradio,name='filcueradio'),
    path('filter_cueradio/',viewscueradio.filter_cueradio,name='filter_cueradio'), # type: ignore
]
