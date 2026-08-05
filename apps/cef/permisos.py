"""
Control de acceso para las vistas activas del módulo CEF.
"""

from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.core.exceptions import PermissionDenied

from .models import (
    get_cueanexos_cargables_usuario,
    obtener_permisos_usuario_cef,
)
from .performance import perf_begin, perf_capture_queries, perf_finish


PERMISOS_CEF_CACHE_VERSION = "v1"
PERMISOS_CEF_CACHE_TTL = 60


def _permisos_cef_cache_key(user):
    user_id = getattr(user, "pk", None)
    if user_id is None:
        return ""

    return f"cef:permisos:{PERMISOS_CEF_CACHE_VERSION}:user:{user_id}"


def _resolver_permisos_cef(user):
    permisos = obtener_permisos_usuario_cef(user)

    # El rol Administrador ya es la autorizacion equivalente para todos los
    # CEF. Los demas roles autorizados conservan la lista puntual de CUE.
    if permisos["puede_ver"] and not permisos["es_admin"]:
        permisos["cueanexos_cargables"] = get_cueanexos_cargables_usuario(
            user,
            permisos=permisos,
        )
    else:
        permisos["cueanexos_cargables"] = []

    return permisos


def get_permisos_cef_request(request):
    """Reutiliza permisos CEF por request y por usuario durante un TTL corto."""
    permisos = getattr(request, "_cef_permisos_usuario", None)
    if permisos is None:
        cache_key = _permisos_cef_cache_key(request.user)
        sentinel = object()
        permisos = cache.get(cache_key, sentinel) if cache_key else sentinel

        if permisos is sentinel:
            permisos = _resolver_permisos_cef(request.user)
            if cache_key:
                cache.set(cache_key, permisos, PERMISOS_CEF_CACHE_TTL)

        request._cef_permisos_usuario = permisos
    return permisos


def cef_required(view_func):
    """
    Protege las vistas activas del módulo CEF.

    - Usuario no autenticado: redirección al login.
    - Usuario autenticado sin rol autorizado: respuesta 403.
    - Usuario autorizado: ejecución normal de la vista.
    """

    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not perf_begin(request):
            if not get_permisos_cef_request(request)["puede_ver"]:
                raise PermissionDenied(
                    "No tenés permisos para acceder al módulo CEF."
                )
            return view_func(request, *args, **kwargs)

        response = None
        error = None
        try:
            with perf_capture_queries(request):
                if not get_permisos_cef_request(request)["puede_ver"]:
                    raise PermissionDenied(
                        "No tenés permisos para acceder al módulo CEF."
                    )
                response = view_func(request, *args, **kwargs)
        except Exception as exc:
            error = exc
            raise
        finally:
            perf_finish(request, response=response, error=error)

        return response

    return login_required(_wrapped_view)
