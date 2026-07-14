# apps/especial/urls.py
from django.urls import path
from django.views.generic import RedirectView
from . import (
    views_alumnos,
    views_docentes, # Nuevo import
    views_carga_cueanexo,
    views_carga_seccion,
    views_ciclo,
    views_inscripcion_seccion,
    views_localizaciones,
)

app_name = "especial"

urlpatterns = [
    # Entrada del módulo
    path(
        "",
        RedirectView.as_view(
            pattern_name="especial:visualizacion_localizaciones",
            permanent=False,
        ),
        name="inicio",
    ),
    path(
        "visualizacion/",
        RedirectView.as_view(
            pattern_name="especial:visualizacion_localizaciones",
            permanent=False,
        ),
        name="visualizacion_inicio",
    ),
    path(
        "visualizacion/localizaciones/",
        views_localizaciones.visualizacion_localizaciones,
        name="visualizacion_localizaciones",
    ),
    # Alumnos
    path(
        "alumnos/",
        views_alumnos.alumnos,
        name="alumnos",
    ),
    # Docentes (Nuevo)
    path(
        "docentes/",
        views_docentes.docentes,
        name="docentes",
    ),
    # CUE-Anexo
    path(
        "carga/cueanexo/",
        views_carga_cueanexo.carga_cueanexo,
        name="carga_cueanexo",
    ),
    # Secciones (Grupos)
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
    # Inscripción de alumnos a secciones
    path(
        "carga/secciones/<int:seccion_id>/inscripciones/",
        views_inscripcion_seccion.inscripcion_seccion,
        name="inscripcion_seccion",
    ),
    # Ciclos
    path(
        "carga/ciclos/",
        views_ciclo.administrar_ciclos,
        name="administrar_ciclos",
    ),
]