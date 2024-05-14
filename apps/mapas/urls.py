#from django.urls import path
from config.urls import path
from . import views, viewscueradio

app_name='mapas'

urlpatterns=[
    path('filtrado/',views.filtrado,name='filtrado'),
    path('filtrado_list/',views.filtrado_list,name='filtrado_list'),
    path('filter/',views.filter_data,name='filter'), # type: ignore
    path('listados/',views.filtrar_tablas_view,name='listados'),    
    path('filcueradio/',viewscueradio.filtrado_cueradio,name='filcueradio'),
    path('filter_cueradio/',viewscueradio.filter_cueradio,name='filter_cueradio'), # type: ignore
    path('listadomap/',views.filter_listado_map,name='filter_listado_map'),
    path('puntos/',views.filtrado_list,name='puntos'),
]
