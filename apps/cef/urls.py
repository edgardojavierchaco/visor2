from django.urls import path

from . import views_alumnos
from . import views_configuracion
from . import views_establecimientos
from . import views_inicio
from . import views_localizaciones
from . import views_responsables
from . import views_router


app_name = "cef"


urlpatterns = [
    path("alumnos/", views_alumnos.alumnos_inicio, name="alumnos"),
    path(
        "establecimiento/",
        views_establecimientos.establecimiento_director,
        name="establecimiento",
    ),
    path(
        "api/validar-cuil/",
        views_alumnos.api_validar_cuil_alumno,
        name="api_validar_cuil",
    ),
    path(
        "api/seleccionar-cef-carga/",
        views_alumnos.api_seleccionar_cef_carga,
        name="api_seleccionar_cef_carga",
    ),
    path(
        "seleccionar/<str:cueanexo>/",
        views_router.seleccionar_servicio_por_acronimo,
        name="seleccionar_servicio",
    ),
    path(
        "visualizacion/",
        views_inicio.visualizacion_inicio,
        name="visualizacion_inicio",
    ),
    path(
        "visualizacion/establecimientos/",
        views_establecimientos.visualizacion_establecimientos,
        name="visualizacion_establecimientos",
    ),
    path(
        "visualizacion/localizaciones/",
        views_localizaciones.visualizacion_localizaciones,
        name="visualizacion_localizaciones",
    ),
    path(
        "visualizacion/responsables/",
        views_responsables.visualizacion_responsables,
        name="visualizacion_responsables",
    ),
    path(
        "configuracion/",
        views_configuracion.configuracion_inicio,
        name="configuracion_inicio",
    ),
]
