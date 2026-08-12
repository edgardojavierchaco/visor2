# apps/especial/urls.py
from django.urls import path
from . import (
    views_alumnos,
    views_docentes, # Nuevo import
    views_carga_cueanexo,
    views_carga_seccion,
    views_ciclo,
    views_contexto,
    views_inscripcion_seccion,
    views_localizaciones,
)

app_name = "especial"

urlpatterns = [
    # Entrada del módulo
    path(
        "",
        views_contexto.inicio,
        name="inicio",
    ),
    path(
        "visualizacion/",
        views_contexto.visualizacion_inicio,
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
    path(
        "alumnos/matricula-compartida/cueanexos/",
        views_alumnos.buscar_cueanexos_matricula_compartida,
        name="buscar_cueanexos_matricula_compartida",
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
    path(
        "carga/secciones/<int:seccion_id>/gestionar/",
        views_carga_seccion.gestionar_seccion,
        name="gestionar_seccion",
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
    path(
    "carga/secciones/<int:seccion_id>/docentes/<int:docente_id>/editar/",
    views_docentes.editar_docente_seccion, # Asegúrate de importar la función
    name="editar_docente_seccion",
    ),
    path(
        "carga/secciones/<int:seccion_id>/inscripciones/<int:inscripcion_id>/editar/",
        views_inscripcion_seccion.editar_inscripcion_seccion,
        name="editar_inscripcion_seccion",
    ),
]
