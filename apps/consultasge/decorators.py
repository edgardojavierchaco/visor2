from functools import wraps
from django.shortcuts import redirect
from django.http import HttpResponseForbidden


def rol_requerido(nombre_rol):
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):

            if not request.user.is_authenticated:
                return redirect("login")

            if request.user.nivelacceso_id != nombre_rol:
                return HttpResponseForbidden(
                    "No tiene permisos para acceder a esta sección."
                )

            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator