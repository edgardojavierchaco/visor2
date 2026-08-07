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
    cueanexos = {
        normalizar_cueanexo(value)
        for value in permisos["escuelas_visualizacion"].values_list(
            "cueanexo", flat=True
        ).distinct()
    }
    cueanexos.discard("")
    permisos["cueanexos_visualizacion"] = frozenset(cueanexos)
    permisos["cueanexos_cargables"] = frozenset(cueanexos)
    return permisos


def get_permisos_especial_request(request):
    """Resuelve permisos una sola vez y los conserva únicamente en el request."""
    permisos = getattr(request, "_especial_permisos_usuario", None)
    if permisos is None:
        permisos = _resolver_permisos_especial(request.user)
        request._especial_permisos_usuario = permisos
    return permisos


def especial_required(view_func):
    """
    Protege las vistas activas del módulo 'especial'.

    - Usuario no autenticado: redirección al login.
    - Usuario autenticado sin rol autorizado: respuesta 403.
    - Usuario autorizado: ejecución normal de la vista.
    """

    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not get_permisos_especial_request(request)["puede_ver"]:
            raise PermissionDenied(
                "No tenés permisos para acceder al módulo 'especial'."
            )

        return view_func(request, *args, **kwargs)

    return login_required(_wrapped_view)
