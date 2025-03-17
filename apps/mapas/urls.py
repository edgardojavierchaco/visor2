from config.urls import path
from . import views
from . import viewscueradio
from . import views2
from . import viewscolectivos, viewscomiarias,viewscentrossalud
from . views_ai import filter_data, filtrado, extraer_criterios, normalizar_region

app_name='mapas'

urlpatterns=[
    path('filtrado/',views.filtrado,name='filtrado'),
    path('filtrado_list/',views.filtrado_list,name='filtrado_list'),
    path('filter/',views.filter_data,name='filter'),
    path('listados/',views.filtrar_tablas_view,name='listados'),    
    path('filcueradio/',viewscueradio.filtrado_cueradio,name='filcueradio'),
    path('filter_cueradio/',viewscueradio.filter_cueradio,name='filter_cueradio'),    
    path('listadomap/',views.filter_listado_map,name='filter_listado_map'),
    path('puntos/',views.filtrado_list,name='puntos'),
    path('datos_ofertas/', views2.obtener_datos_ofertas, name='datos_ofertas'),
    path('geometria/', viewscueradio.obtener_geometria, name='obtener_geometria'),
    path('get-region-data/', viewscueradio.get_region_data, name='get_region_data'),
    path('geometria2/', viewscueradio.obtener_geometria2, name='obtener_geometrias'),
    path('filter_colectivos/',viewscolectivos.filtrado_cueradiocolectivo, name='filter_colectivos'),
    path('colectivos/',viewscolectivos.filter_cueradiocolectivo, name='colectivos'),
    path('filter_comisarias/',viewscomiarias.filtrado_cueradiocomisarias, name='filter_comisarias'),
    path('comisarias/',viewscomiarias.filter_cueradiocomisarias, name='comisarias'),   
    path('filter_salud/',viewscentrossalud.filtrado_cueradiosalud, name='filter_salud'),
    path('salud/',viewscentrossalud.filter_cueradiosalud, name='salud'), 
    path('filnat/', filtrado, name='filnat'),
    path('ofertas/', filter_data, name='filter_data')
]
    
