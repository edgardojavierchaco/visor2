"""
Control de acceso para las vistas activas del módulo 'especial'.
"""

from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied

from .models import (
    ROLES_AUTORIZADOS_ESPECIAL,
    get_escuelas_especiales_cargables_usuario,
    get_escuelas_especiales_visualizacion_usuario,
    normalizar_cuil_usuario,
    normalizar_cueanexo,
    obtener_rol_usuario_especial,
)
from .performance import perf_begin, perf_capture_queries, perf_finish, perf_phase


def _resolver_permisos_especial(user):
    rol = obtener_rol_usuario_especial(user)
    permisos = {
        "rol": rol,
        "puede_ver": rol in ROLES_AUTORIZADOS_ESPECIAL,
        "es_admin": rol == "Administrador",
        "cuil_usuario": normalizar_cuil_usuario(user),
    }
    permisos["escuelas_visualizacion"] = get_escuelas_especiales_visualizacion_usuario(
        user,
        permisos=permisos,
    )
    permisos["escuelas_cargables"] = get_escuelas_especiales_cargables_usuario(
        user,
        permisos=permisos,
    )
    if permisos["puede_ver"] and not permisos["es_admin"]:
        cueanexos = {
            normalizar_cueanexo(value)
            for value in permisos["escuelas_visualizacion"].values_list(
                "cueanexo", flat=True
            ).distinct()
        }
        cueanexos.discard("")
        cueanexos = frozenset(cueanexos)
    else:
        cueanexos = frozenset()
    permisos["cueanexos_visualizacion"] = cueanexos
    permisos["cueanexos_cargables"] = cueanexos
    return permisos


def cueanexo_autorizado_especial(permisos, cueanexo, scope):
    """Determina el alcance de un CUE sin consultar base de datos ni caché."""
    if scope not in {"visualizacion", "cargables"}:
        raise ValueError(f"Scope de CUE-Anexo no soportado: {scope!r}")

    cueanexo = normalizar_cueanexo(cueanexo)
    if not cueanexo or not permisos.get("puede_ver"):
        return False
    if permisos.get("es_admin"):
        return True
    return cueanexo in permisos.get(f"cueanexos_{scope}", frozenset())


def get_permisos_especial_request(request):
    """Resuelve permisos una sola vez y los conserva únicamente en el request."""
    permisos = getattr(request, "_especial_permisos_usuario", None)
    if permisos is None:
        permisos = _resolver_permisos_especial(request.user)
        request._especial_permisos_usuario = permisos
    return permisos


def _puede_ver_especial_instrumentado(request):
    with perf_phase(request, "permissions"):
        return get_permisos_especial_request(request)["puede_ver"]


def especial_required(view_func):
    """
    Protege las vistas activas del módulo 'especial'.

    - Usuario no autenticado: redirección al login.
    - Usuario autenticado sin rol autorizado: respuesta 403.
    - Usuario autorizado: ejecución normal de la vista.
    """

    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not _puede_ver_especial_instrumentado(request):
            raise PermissionDenied(
                "No tenés permisos para acceder al módulo 'especial'."
            )

        with perf_phase(request, "view"):
            return view_func(request, *args, **kwargs)

    @wraps(view_func)
    def _instrumented_view(request, *args, **kwargs):
        perf_active = perf_begin(request)

        try:
            if perf_active:
                perf_capture_queries(request)
            response = _wrapped_view(request, *args, **kwargs)
        except Exception as error:
            if perf_active:
                perf_finish(request, error=error)
            raise
        else:
            if perf_active:
                perf_finish(request, response=response)
            return response

    return login_required(_instrumented_view)
