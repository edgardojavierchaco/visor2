from django.urls import path
# IMPORTACIONES CORREGIDAS
from . import views_inicio
from . import views_establecimientos  
from . import views_localizaciones
from . import views_ofertaslocales
from . import views_responsables
from . import views_fecha

app_name = 'padroninterno'

urlpatterns = [
    # Inicio
    path('', views_inicio.inicio_view, name='inicio'),
    path('establecimiento/', views_establecimientos.listar_establecimientos, name='establecimientos'),
    path('establecimiento', views_establecimientos.listar_establecimientos), 
    path('establecimiento/<int:id_establecimiento>/', views_establecimientos.detalle_establecimiento_json, name='detalle_establecimiento_json'),

    # Localizaciones
    path('localizacion/', views_localizaciones.listar_localizaciones, name='localizaciones'),
    path('localizacion/<int:id_localizacion>/', views_localizaciones.detalle_localizacion_json, name='detalle_localizacion_json'),
    
    # Ofertas Locales
    path('ofertalocal/', views_ofertaslocales.listar_ofertas_locales, name='ofertaslocales'),
    path('ofertalocal/<int:id_oferta>/', views_ofertaslocales.detalle_oferta_local_json, name='detalle_oferta_local_json'),
    path('titulo/<int:id_titulo>/', views_ofertaslocales.detalle_titulo_json, name='detalle_titulo_json'),
    path("actualizar-fecha-padron/", views_fecha.actualizar_fecha_padron, name="actualizar_fecha_padron"),
    
]

if views_responsables is not None:
    urlpatterns.append(path('responsable/', views_responsables.listar_responsables, name='responsables'))
    urlpatterns.append(path('responsable', views_responsables.listar_responsables))
    urlpatterns.append(path('responsable/<int:id_responsable>/', views_responsables.detalle_responsable_json, name='detalle_responsable_json'))
