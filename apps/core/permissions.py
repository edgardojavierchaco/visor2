from functools import wraps
from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required


def role_required(*roles):
    """
    Decorador que permite acceder solo a usuarios
    que pertenezcan a alguno de los grupos indicados.
    """

    def decorator(view_func):

        @wraps(view_func)
        @login_required
        def _wrapped_view(request, *args, **kwargs):

            user_groups = set(
                request.user.groups.values_list("name", flat=True)
            )

            if user_groups.intersection(roles):
                return view_func(request, *args, **kwargs)

            return redirect("dashboard:portada")

        return _wrapped_view

    return decorator