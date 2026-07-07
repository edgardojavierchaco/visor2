from django.urls import path
from django.views.generic import RedirectView

from . import (
    views_alumnos,
    views_carga_cueanexo,
    views_carga_grupo,
    views_ciclo,
    views_inicio,
    views_inscripcion_grupo,
    views_inventario,
    views_localizaciones,
    views_docentes_grupo,
    views_profesores,
)


app_name = "cef"


urlpatterns = [
    # Entrada del modulo: pantalla de inicio operativa.
    path(
        "",
        views_inicio.inicio,
        name="inicio",
    ),
    # Compatibilidad con enlaces historicos a /visualizacion/.
    path(
        "visualizacion/",
        RedirectView.as_view(
            pattern_name="cef:visualizacion_localizaciones",
            permanent=False,
        ),
        name="visualizacion_inicio",
    ),
    # Pantalla principal con tabla, filtros, selector CEF y exportacion Excel.
    path(
        "visualizacion/localizaciones/",
        views_localizaciones.visualizacion_localizaciones,
        name="visualizacion_localizaciones",
    ),
    path(
        "alumnos/",
        views_alumnos.alumnos,
        name="alumnos",
    ),
    path(
        "profesores/",
        views_profesores.profesores,
        name="profesores",
    ),
    path(
        "carga/cueanexo/",
        views_carga_cueanexo.carga_cueanexo,
        name="carga_cueanexo",
    ),
    path(
        "carga/cueanexo/datos/",
        views_carga_cueanexo.editar_datos_cueanexo,
        name="editar_datos_cueanexo",
    ),
    path(
        "carga/grupos/",
        views_carga_grupo.carga_grupo,
        name="carga_grupo",
    ),
    path(
        "carga/grupos/nuevo/",
        views_carga_grupo.carga_grupo_form,
        name="carga_grupo_nuevo",
    ),
    path(
        "carga/grupos/<int:grupo_id>/",
        views_carga_grupo.carga_grupo_form,
        name="carga_grupo_editar",
    ),
    path(
        "carga/grupos/<int:grupo_id>/gestionar/",
        views_carga_grupo.gestionar_grupo,
        name="gestionar_grupo",
    ),
    path(
        "carga/grupos/<int:grupo_id>/inscripciones/",
        views_inscripcion_grupo.inscripcion_grupo,
        name="inscripcion_grupo",
    ),
    path(
        "carga/grupos/<int:grupo_id>/inscripciones/<int:inscripcion_id>/editar/",
        views_inscripcion_grupo.editar_inscripcion_grupo,
        name="editar_inscripcion_grupo",
    ),
    path(
        "carga/grupos/<int:grupo_id>/docentes/",
        views_docentes_grupo.docentes_grupo,
        name="docentes_grupo",
    ),
    path(
        "carga/grupos/<int:grupo_id>/docentes/<int:docente_grupo_id>/editar/",
        views_docentes_grupo.editar_docente_grupo,
        name="editar_docente_grupo",
    ),
    path(
        "carga/inventario/",
        views_inventario.carga_inventario,
        name="carga_inventario",
    ),
    path(
        "carga/inventario/<int:item_id>/",
        views_inventario.carga_inventario,
        name="editar_inventario",
    ),
    path(
        "carga/ciclos/",
        views_ciclo.administrar_ciclos,
        name="administrar_ciclos",
    ),
]
