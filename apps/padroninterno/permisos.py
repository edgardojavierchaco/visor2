from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied

from .models import usuario_puede_ver_padron_interno


def padron_interno_admin_o_gestor_required(view_func):
    """
    Decorador propio de padroninterno.
    - Usuario no logueado: redirige al login.
    - Usuario logueado sin rol válido: 403.
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not usuario_puede_ver_padron_interno(request.user):
            raise PermissionDenied('No tenés permisos para acceder a Datos Padrón Interno.')
        return view_func(request, *args, **kwargs)

    return login_required(_wrapped_view)