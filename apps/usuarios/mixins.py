from django.contrib.auth.mixins import UserPassesTestMixin
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect
from django.conf import settings

class AdminRequiredMixin(UserPassesTestMixin):
    """
    Mezcla que requiere que el usuario sea parte de un grupo específico para acceder a una vista.

    Este mixin extiende UserPassesTestMixin y verifica si el usuario autenticado pertenece
    al grupo "Administrador". Si no tiene permiso, se lanzará una excepción de permiso denegado.

    Métodos:
        test_func: Verifica si el usuario pertenece a un grupo permitido.
        handle_no_permission: Maneja el caso en que el usuario no tiene permisos.
    """
    
    def test_func(self):
        """
        Verifica si el usuario autenticado pertenece al grupo permitido.

        Retorna:
            bool: True si el usuario pertenece al grupo 'Administrador', False en caso contrario.
        """
        
        allowed_groups = ['Administrador']
        user = self.request.user
        if user.is_authenticated:
            return user.groups.filter(name__in=allowed_groups).exists()
        return False
    
    def handle_no_permission(self):
        """
        Maneja el caso en que el usuario no tiene permisos para acceder a la vista.

        Lanza:
            PermissionDenied: Si el usuario no pertenece a ninguno de los grupos permitidos.
        """
        
        # Si el usuario no pertenece a ninguno de los grupos permitidos, lanza una excepción de permiso denegado
        raise PermissionDenied("No tiene permisos para acceder a esta página")


class RolRequiredMixin:
    roles_permitidos = []

    def dispatch(self, request, *args, **kwargs):

        user = request.user

        if not user.is_authenticated or not user.is_staff:
            return redirect('login')

        if not hasattr(user, 'perfil') or not user.perfil.rol:
            return redirect(settings.LOGIN_REDIRECT_URL)

        rol = user.perfil.rol.nombre

        if self.roles_permitidos and rol not in self.roles_permitidos:
            return redirect(settings.LOGIN_REDIRECT_URL)

        return super().dispatch(request, *args, **kwargs)


class CategoriaRequiredMixin:
    categorias_permitidas = []

    def dispatch(self, request, *args, **kwargs):

        user = request.user

        if not user.is_authenticated or not user.is_staff:
            return redirect('login')

        if not hasattr(user, 'perfil') or not user.perfil.rol:
            return redirect(settings.LOGIN_REDIRECT_URL)

        categoria = user.perfil.rol.categoria_acceso

        if self.categorias_permitidas and categoria not in self.categorias_permitidas:
            return redirect(settings.LOGIN_REDIRECT_URL)

        return super().dispatch(request, *args, **kwargs)