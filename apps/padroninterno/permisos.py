from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import JsonResponse

from .models import usuario_es_admin_padron, usuario_puede_ver_padron_interno


# Punto unico de control para proteger las vistas del modulo.
# Mantiene la validacion de login y rol fuera de cada vista individual.
def padron_interno_admin_o_gestor_required(view_func):
    """
    Decorador propio de padroninterno.
    - Usuario no logueado: redirige al login.
    - Usuario logueado sin rol válido: 403.
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        # Si el usuario existe pero no tiene un rol permitido, Django responde 403.
        if not usuario_puede_ver_padron_interno(request.user):
            raise PermissionDenied('No tenés permisos para acceder a Datos Padrón Interno.')
        # Con permisos correctos, se continua con la vista original.
        return view_func(request, *args, **kwargs)

    # login_required maneja el caso de usuario anonimo y redirecciona al login.
    return login_required(_wrapped_view)


# Decorador para endpoints JSON que solo puede modificar un Administrador.
# Devuelve 403 en JSON para mantener el contrato de los llamados AJAX.
def padron_interno_admin_required_json(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        # El usuario debe estar logueado y ademas tener rol Administrador.
        if not usuario_es_admin_padron(request.user):
            return JsonResponse({"status": "error", "message": "No autorizado."}, status=403)
        return view_func(request, *args, **kwargs)

    return login_required(_wrapped_view)


# Decorador JSON para endpoints consultables por cualquier rol habilitado del modulo.
def padron_interno_required_json(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not usuario_puede_ver_padron_interno(request.user):
            return JsonResponse({"status": "error", "message": "No autorizado."}, status=403)
        return view_func(request, *args, **kwargs)

    return login_required(_wrapped_view)
