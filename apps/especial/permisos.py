"""
Control de acceso para las vistas activas del módulo 'especial'.
"""

from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied

from .models import usuario_puede_ver_especial


def especial_required(view_func):
    """
    Protege las vistas activas del módulo 'especial'.

    - Usuario no autenticado: redirección al login.
    - Usuario autenticado sin rol autorizado: respuesta 403.
    - Usuario autorizado: ejecución normal de la vista.
    """

    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not usuario_puede_ver_especial(request.user):
            raise PermissionDenied(
                "No tenés permisos para acceder al módulo 'especial'."
            )

        return view_func(request, *args, **kwargs)

    return login_required(_wrapped_view)
