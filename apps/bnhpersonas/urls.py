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
)

app_name='bnhpersonas'

urlpatterns = [
    # =========================
    # AJAX / UTILIDADES
    # =========================
    path('filtrar-ceic/', filtrar_ceic, name='filtrar_ceic'),
    path('filtrar-localidades/', filtrar_localidades, name='filtrar_localidades'),
    path('buscar-codigos-area/', buscar_codigos_area, name='buscar_codigos_area'),

    # =========================
    # PERSONA CORE
    # =========================
    path('carga-personal/', carga_personal, name='carga_personal'),

    path(
        "personas/<int:pk>/carga-personal/",
        carga_personal,
        name="carga_personal_edit"
    ),

    path('buscar-persona/', buscar_persona, name='buscar_persona'),

    # =========================
    # LISTADO / DETALLE
    # =========================
    path(
        'personas/',
        PersonasListView.as_view(),
        name='personas_list'
    ),

    path(
        'personas/<int:pk>/detalle/',
        PersonaDetailView.as_view(),
        name='personas_detail'
    ),
]