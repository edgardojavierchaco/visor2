"""Rutas propias de BNH Alumnos para pantalla de carga y endpoints AJAX."""

from django.urls import path

from . import views

app_name = "bnhalumnos"

urlpatterns = [
    # Pantalla principal: renderiza el formulario y carga catálogos compartidos.
    path("alumnos/carga/", views.carga_alumno_view, name="carga_alumno"),
    # Endpoints usados por el frontend para buscar registros existentes por CUIL.
    path("api/alumnos/buscar-cuil/", views.buscar_alumno_por_cuil, name="buscar_alumno_cuil"),
    path("api/tutores/buscar-cuil/", views.buscar_tutor_por_cuil, name="buscar_tutor_cuil"),
    # Persistencia de alumno y relaciones cargadas desde el formulario dinámico.
    # Flujo de guardado:
    # El template resuelve name="guardar_carga_alumno" en data-url-guardar.
    # Luego el fetch() del boton Guardar carga hace POST a esta ruta.
    # Django ejecuta views.guardar_carga_alumno, donde se valida y guarda en BD.
    path("api/alumnos/guardar/", views.guardar_carga_alumno, name="guardar_carga_alumno"),
]
