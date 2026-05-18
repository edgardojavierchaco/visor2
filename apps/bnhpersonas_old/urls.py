from django.urls import path
from .views import (
    filtrar_ceic, 
    carga_personal, 
    buscar_persona, 
    filtrar_localidades, 
    buscar_codigos_area
)

from .views_list import (
    PersonasListView,
    PersonaDetailView,
    ActividadUpdateView,
    ActividadDeleteView
)

app_name='bnhpersonas'

urlpatterns = [
    path('filtrar-ceic/', filtrar_ceic, name='filtrar_ceic'),
    path('carga-personal/', carga_personal, name='carga_personal'),
    path('buscar-persona/', buscar_persona, name='buscar_persona'),
    path('filtrar-localidades/', filtrar_localidades, name='filtrar_localidades'),
    path('buscar-codigos-area/', buscar_codigos_area, name='buscar_codigos_area'),
    path(
        'personas/',
        PersonasListView.as_view(),
        name='personas_list'
    ),

    path(
        'personas/<int:pk>/',
        PersonaDetailView.as_view(),
        name='personas_detail'
    ),
    path(
        'actividades/<int:pk>/update/',
        ActividadUpdateView.as_view(),
        name='actividad_update'
    ),

    path(
        'actividades/<int:pk>/delete/',
        ActividadDeleteView.as_view(),
        name='actividad_delete'
    ),
]

