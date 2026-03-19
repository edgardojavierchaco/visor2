from django.shortcuts import redirect
from django.conf import settings
from functools import wraps
from .services import get_user_data, get_redirect_url


def acceso_required(roles=None, categorias=None, redirigir=True):
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):

            data = get_user_data(request.user)
            rol = data["rol"]
            categoria = data["categoria"]

            # 🚫 no logueado o sin perfil
            if not rol:
                return redirect('login')

            # 🚫 no cumple rol
            if roles and rol not in roles:
                if redirigir:
                    url = get_redirect_url(request.user)
                    return redirect(url) if url else redirect(settings.LOGIN_REDIRECT_URL)
                return redirect(settings.LOGIN_REDIRECT_URL)

            # 🚫 no cumple categoría
            if categorias and categoria not in categorias:
                if redirigir:
                    url = get_redirect_url(request.user)
                    return redirect(url) if url else redirect(settings.LOGIN_REDIRECT_URL)
                return redirect(settings.LOGIN_REDIRECT_URL)

            return view_func(request, *args, **kwargs)

        return wrapper
    return decorator


# 🔹 Compatibilidad con tu código actual

def rol_required(*roles_permitidos):
    return acceso_required(roles=list(roles_permitidos))


def categoria_required(*categorias):
    return acceso_required(categorias=list(categorias))