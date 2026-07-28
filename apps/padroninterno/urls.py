from django.urls import path
# IMPORTACIONES CORREGIDAS
from . import views_inicio
from . import views_establecimientos  
from . import views_localizaciones
from . import views_ofertaslocales
from . import views_responsables
from . import views_fecha

app_name = 'padroninterno'

# Rutas publicas del modulo Padron Interno.
# Cada grupo delega en su archivo de vistas correspondiente.
urlpatterns = [
    # Inicio
    path('', views_inicio.inicio_view, name='inicio'),

    # Establecimientos: pantalla principal, datos asincronicos, totales, filtros y detalle.
    path('establecimiento/', views_establecimientos.listar_establecimientos, name='establecimientos'),
    path('establecimiento', views_establecimientos.listar_establecimientos), 
    path('establecimiento/datos/', views_establecimientos.establecimientos_datos_json, name='establecimientos_datos'),
    path('establecimiento/total/', views_establecimientos.establecimientos_total_json, name='establecimientos_total'),
    path('establecimiento/filtros/', views_establecimientos.establecimientos_filtros_json, name='establecimientos_filtros'),
    path('establecimiento/<int:id_establecimiento>/', views_establecimientos.detalle_establecimiento_json, name='detalle_establecimiento_json'),

    # Localizaciones: listado, endpoints JSON para la grilla y detalle individual.
    path('localizacion/', views_localizaciones.listar_localizaciones, name='localizaciones'),
    path('localizacion/datos/', views_localizaciones.localizaciones_datos_json, name='localizaciones_datos'),
    path('localizacion/total/', views_localizaciones.localizaciones_total_json, name='localizaciones_total'),
    path('localizacion/filtros/', views_localizaciones.localizaciones_filtros_json, name='localizaciones_filtros'),
    path('localizacion/<int:id_localizacion>/', views_localizaciones.detalle_localizacion_json, name='detalle_localizacion_json'),
    
    # Ofertas Locales: listado, exportacion y detalles de oferta/titulo.
    path('ofertalocal/', views_ofertaslocales.listar_ofertas_locales, name='ofertaslocales'),
    path('ofertalocal/datos/', views_ofertaslocales.ofertas_locales_datos_json, name='ofertaslocales_datos'),
    path('ofertalocal/total/', views_ofertaslocales.ofertas_locales_total_json, name='ofertaslocales_total'),
    path('ofertalocal/<int:id_oferta>/', views_ofertaslocales.detalle_oferta_local_json, name='detalle_oferta_local_json'),
    path('titulo/<int:id_titulo>/', views_ofertaslocales.detalle_titulo_json, name='detalle_titulo_json'),
    path("fecha-padron/estado/", views_fecha.estado_fecha_padron, name="estado_fecha_padron"),
    path("actualizar-fecha-padron/", views_fecha.actualizar_fecha_padron, name="actualizar_fecha_padron"),
    path("actualizar-fecha-padron/progreso/<uuid:job_id>/", views_fecha.progreso_actualizar_fecha_padron, name="progreso_actualizar_fecha_padron"),
    
]

# Responsables se agrega al final para mantener separado este bloque de rutas.
if views_responsables is not None:
    urlpatterns.append(path('responsable/', views_responsables.listar_responsables, name='responsables'))
    urlpatterns.append(path('responsable', views_responsables.listar_responsables))
    urlpatterns.append(path('responsable/datos/', views_responsables.responsables_datos_json, name='responsables_datos'))
    urlpatterns.append(path('responsable/total/', views_responsables.responsables_total_json, name='responsables_total'))
    urlpatterns.append(path('responsable/filtros/', views_responsables.responsables_filtros_json, name='responsables_filtros'))
    urlpatterns.append(path('responsable/<int:id_responsable>/', views_responsables.detalle_responsable_json, name='detalle_responsable_json'))
