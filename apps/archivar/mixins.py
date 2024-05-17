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
