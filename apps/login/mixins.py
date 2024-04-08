from django.shortcuts import redirect

class IsSuperuserMixin(object):
    def dispatch(self, request, *args, **kwargs):
        if request.user.is_superuser:
            return super().dispatch(request, *args, **kwargs)
        return redirect('/')  # Aquí deberías redirigir a la página correspondiente en caso de que el usuario no sea un superusuario
