# apps/especial/urls.py
from django.urls import path
from django.views.generic import RedirectView

from . import (
    views_alumnos,
    views_carga_cueanexo,
    views_carga_seccion,
    views_ciclo,
    views_inscripcion_seccion,
    views_localizaciones,
)


app_name = "especial"


urlpatterns = [
    # Entrada del módulo: redirige a la pantalla activa de localizaciones.
    path(
        "",
        RedirectView.as_view(
            pattern_name="especial:visualizacion_localizaciones",
            permanent=False,
        ),
        name="inicio",
    ),
    # Compatibilidad con enlaces históricos a /visualizacion/.
    path(
        "visualizacion/",
        RedirectView.as_view(
            pattern_name="especial:visualizacion_localizaciones",
            permanent=False,
        ),
        name="visualizacion_inicio",
    ),
    # Pantalla principal con tabla, filtros, selector de escuelas y exportación Excel.
    path(
        "visualizacion/localizaciones/",
        views_localizaciones.visualizacion_localizaciones,
        name="visualizacion_localizaciones",
    ),
    # Búsqueda y gestión de alumnos.
    path(
        "alumnos/",
        views_alumnos.alumnos,
        name="alumnos",
    ),
    # Datos del CUE-Anexo seleccionado.
    path(
        "carga/cueanexo/",
        views_carga_cueanexo.carga_cueanexo,
        name="carga_cueanexo",
    ),
    # Gestión de secciones de Educación Especial.
    path(
        "carga/secciones/",
        views_carga_seccion.carga_seccion,
        name="carga_seccion",
    ),
    path(
        "carga/secciones/nueva/",
        views_carga_seccion.carga_seccion_form,
        name="carga_seccion_nueva",
    ),
    path(
        "carga/secciones/<int:seccion_id>/",
        views_carga_seccion.carga_seccion_form,
        name="carga_seccion_editar",
    ),
    # Inscripción de alumnos a secciones.
    path(
        "carga/secciones/<int:seccion_id>/inscripciones/",
        views_inscripcion_seccion.inscripcion_seccion,
        name="inscripcion_seccion",
    ),
    # Administración de ciclos lectivos (solo administradores).
    path(
        "carga/ciclos/",
        views_ciclo.administrar_ciclos,
        name="administrar_ciclos",
    ),
]