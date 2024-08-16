from django.urls import path
from .views import (
    SupervisorListView,
    SupervisorCreateView,
    SupervisorUpdateView,
    SupervisorDeleteView,
    EscuelaListView,
    EscuelaCreateView,
    EscuelaUpdateView,
    EscuelasDeleteView,
    DirectorRegionalListView,
    DirectorRegionalCreateView,
    DirectorRegionalUpdateView,
    DirectorRegionalDeleteView,
)

app_name='supervis'

urlpatterns = [
    # URLs para Supervisores
    path('supervisores/', SupervisorListView.as_view(), name='lista_supervisores'),
    path('supervisores/nuevo/', SupervisorCreateView.as_view(), name='crear_supervisor'),
    path('supervisores/editar/', SupervisorUpdateView.as_view(), name='editar_supervisor'),
    path('supervisores/eliminar/', SupervisorDeleteView.as_view(), name='eliminar_supervisor'),

    # URLs para Escuelas
    path('escuelas/', EscuelaListView.as_view(), name='lista_escuelas'),
    path('escuelas/nueva/', EscuelaCreateView.as_view(), name='crear_escuela'),
    path('escuelas/editar/', EscuelaUpdateView.as_view(), name='editar_escuela'),
    path('escuelas/eliminar/', EscuelasDeleteView.as_view(), name='eliminar_escuela'),

    # URLs para Directores Regionales
    path('directores/', DirectorRegionalListView.as_view(), name='lista_directores_regionales'),
    path('directores/nuevo/', DirectorRegionalCreateView.as_view(), name='crear_director_regional'),
    path('directores/editar/', DirectorRegionalUpdateView.as_view(), name='editar_director_regional'),
    path('directores/eliminar/', DirectorRegionalDeleteView.as_view(), name='eliminar_director_regional'),
]

