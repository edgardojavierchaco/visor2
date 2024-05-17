from django.contrib.auth.mixins import UserPassesTestMixin
from django.core.exceptions import PermissionDenied
from django.contrib.auth.models import Group

class GroupRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        # Define los grupos que tienen acceso a esta vista
        allowed_groups = ['Administrador', 'Gestor']  
        user = self.request.user
        if user.is_authenticated:
            # Verifica si el usuario pertenece a alguno de los grupos permitidos
            return user.groups.filter(name__in=allowed_groups).exists()
        return False

    def handle_no_permission(self):
        # Si el usuario no pertenece a ninguno de los grupos permitidos, lanza una excepción de permiso denegado
        raise PermissionDenied("No tiene permisios para acceder a esta página")

class ReadOnlyAccessMixin(UserPassesTestMixin):
    allowed_groups = ['Director', 'Supervisor', 'Regional']

    def test_func(self):
        user = self.request.user
        if user.is_authenticated:
            # Verificar si el usuario pertenece a alguno de los grupos permitidos
            return user.groups.filter(name__in=self.allowed_groups).exists()
        return False

    def handle_no_permission(self):
        # Si el usuario no pertenece a ninguno de los grupos permitidos, lanza una excepción de permiso denegado
        raise PermissionDenied("No tiene permisos para realizar esta acción")

    def dispatch(self, request, *args, **kwargs):
        # Si el usuario no pertenece a uno de los grupos permitidos, redirigirlo a la página de error 403
        if not self.test_func():
            return self.handle_no_permission()
        return super().dispatch(request, *args, **kwargs)