from django.urls import path
from .views import filtrar_ceic, carga_personal, buscar_persona, filtrar_localidades

app_name='bnhpersonas'

urlpatterns = [
    path('filtrar-ceic/', filtrar_ceic, name='filtrar_ceic'),
    path('carga-personal/', carga_personal, name='carga_personal'),
    path('buscar-persona/', buscar_persona, name='buscar_persona'),
    path("filtrar-localidades/", filtrar_localidades, name="filtrar_localidades")
]