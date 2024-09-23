from django.contrib.auth.mixins import UserPassesTestMixin
from django.core.exceptions import PermissionDenied

class AdminRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        allowed_groups = ['Administrador']
        user = self.request.user
        if user.is_authenticated:
            return user.groups.filter(name__in=allowed_groups).exists()
        return False
    
    def handle_no_permission(self):
        # Si el usuario no pertenece a ninguno de los grupos permitidos, lanza una excepción de permiso denegado
        raise PermissionDenied("No tiene permisos para acceder a esta página")