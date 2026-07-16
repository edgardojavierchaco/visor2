"""Decoradores de autorizacion para las pantallas y endpoints BNH Alumnos."""

from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied

from .models import usuario_puede_ver_bnh_alumnos


def bnh_alumnos_required(view_func):
    """
    Decorador propio de BNH Alumnos.
    - Usuario no logueado: redirige al login.
    - Usuario logueado sin rol valido: 403.

    ``login_required`` resuelve autenticacion. La consulta a
    ``usuario_puede_ver_bnh_alumnos`` resuelve autorizacion funcional por rol,
    y se aplica tanto a la pantalla HTML como a los endpoints JSON.
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not usuario_puede_ver_bnh_alumnos(request.user):
            raise PermissionDenied("No tenes permisos para acceder a BNH Alumnos.")
        return view_func(request, *args, **kwargs)

    return login_required(_wrapped_view)
