from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import JsonResponse

from .models import (
    usuario_puede_ver_visualizacion_pof,
    usuario_tiene_acceso_completo_pof,
)


def pof_required(view_func):
    """
    Protege las vistas HTML administrativas del módulo POF.

    - Usuario no autenticado: redirección al login.
    - Usuario autenticado sin acceso completo: 403.
    - Usuario con acceso completo: ejecución normal.
    """

    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not usuario_tiene_acceso_completo_pof(request.user):
            raise PermissionDenied(
                "No tenés permisos para acceder al módulo POF."
            )

        return view_func(request, *args, **kwargs)

    return login_required(_wrapped_view)


def pof_api_required(view_func):
    """
    Protege endpoints JSON administrativos del módulo POF.

    - Usuario no autenticado: JSON 401.
    - Usuario autenticado sin acceso completo: JSON 403.
    - Usuario con acceso completo: ejecución normal.
    """

    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        user = getattr(request, "user", None)

        if not user or not getattr(user, "is_authenticated", False):
            return JsonResponse(
                {
                    "ok": False,
                    "mensaje": "Debe iniciar sesión para acceder al módulo POF.",
                },
                status=401,
            )

        if not usuario_tiene_acceso_completo_pof(user):
            return JsonResponse(
                {
                    "ok": False,
                    "mensaje": "No tenés permisos para acceder al módulo POF.",
                },
                status=403,
            )

        return view_func(request, *args, **kwargs)

    return _wrapped_view


def pof_visualizacion_required(view_func):
    """Protege vistas HTML disponibles para cualquier rol del visualizador."""

    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not usuario_puede_ver_visualizacion_pof(request.user):
            raise PermissionDenied(
                "No tenés permisos para acceder al visualizador POF."
            )

        return view_func(request, *args, **kwargs)

    return login_required(_wrapped_view)


def pof_visualizacion_api_required(view_func):
    """Protege endpoints JSON/Excel disponibles para roles del visualizador."""

    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        user = getattr(request, "user", None)

        if not user or not getattr(user, "is_authenticated", False):
            return JsonResponse(
                {
                    "ok": False,
                    "mensaje": "Debe iniciar sesión para acceder al módulo POF.",
                },
                status=401,
            )

        if not usuario_puede_ver_visualizacion_pof(user):
            return JsonResponse(
                {
                    "ok": False,
                    "mensaje": "No tenés permisos para acceder al visualizador POF.",
                },
                status=403,
            )

        return view_func(request, *args, **kwargs)

    return _wrapped_view
