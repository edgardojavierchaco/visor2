from django.shortcuts import redirect
from django.conf import settings
from functools import wraps
from .services import get_user_context, get_redirect_url


def redirect_user(user):
    """
    Redirección centralizada
    """
    url = get_redirect_url(user)
    return redirect(url or settings.LOGIN_REDIRECT_URL)


def acceso_required(roles=None, categorias=None, redirigir=True):
    def decorator(view_func):

        @wraps(view_func)
        def wrapper(request, *args, **kwargs):

            # 🔐 No autenticado
            if not request.user.is_authenticated:
                return redirect('login')

            ctx = get_user_context(request.user)

            # 🚫 sin rol
            if not ctx.rol:
                return redirect('login')

            # 🚫 no cumple rol
            if roles and not ctx.has_rol(roles):
                return redirect_user(request.user) if redirigir else redirect(settings.LOGIN_REDIRECT_URL)

            # 🚫 no cumple categoría
            if categorias and not ctx.has_categoria(categorias):
                return redirect_user(request.user) if redirigir else redirect(settings.LOGIN_REDIRECT_URL)

            return view_func(request, *args, **kwargs)

        return wrapper
    return decorator


# -----------------------------------
# 🔹 COMPATIBILIDAD
# -----------------------------------

def rol_required(*roles_permitidos):
    return acceso_required(roles=list(roles_permitidos))


def categoria_required(*categorias):
    return acceso_required(categorias=list(categorias))