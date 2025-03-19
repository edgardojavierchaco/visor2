from django.contrib.auth.mixins import UserPassesTestMixin
from django.core.exceptions import PermissionDenied
from django.contrib.auth.models import Group
from django.http import HttpResponseForbidden
from django.shortcuts import redirect

class GroupRequiredMixin(UserPassesTestMixin):
    """
    Mixin que restringe el acceso a las vistas solo a usuarios pertenecientes
    a grupos específicos.

    Este mixin verifica si el usuario autenticado pertenece a los grupos
    'Administrador' o 'Gestor'. Si el usuario no pertenece a estos grupos,
    se deniega el acceso y se lanza una excepción de Permiso Denegado.

    Methods:
        test_func: Verifica si el usuario pertenece a alguno de los grupos permitidos.
        handle_no_permission: Lanza una excepción de Permiso Denegado si el acceso es denegado.
    """
    def test_func(self):
        # Los grupos que tienen acceso a esta vista
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
    def test_func(self):
        """
    Mixin que proporciona acceso solo de lectura a las vistas para usuarios
    pertenecientes a grupos específicos.

    Este mixin permite que los usuarios autenticados que pertenezcan a
    los grupos 'Administrador', 'Gestor', 'Director', 'Supervisor', o 
    'Regional' tengan acceso. Si el usuario no pertenece a ninguno de estos 
    grupos, se deniega el acceso y se lanza una excepción de Permiso Denegado.

    Methods:
        test_func: Verifica si el usuario pertenece a alguno de los grupos permitidos.
        handle_no_permission: Lanza una excepción de Permiso Denegado si el acceso es denegado.
    """
        # Define los grupos que tienen acceso a esta vista
        allowed_groups = ['Administrador', 'Gestor', 'Director','Supervisor','Regional']  
        user = self.request.user
        if user.is_authenticated:
            # Verifica si el usuario pertenece a alguno de los grupos permitidos
            return user.groups.filter(name__in=allowed_groups).exists()
        return False

    def handle_no_permission(self):
        # Si el usuario no pertenece a ninguno de los grupos permitidos, lanza una excepción de permiso denegado
        raise PermissionDenied("No tiene permisios para acceder a esta página")
   

class UsuarioAutorizadoMixin:
    """
    Mixin que permite acceder solo a los usuarios en una lista específica.
    """
    usuarios_autorizados = ['24024606', 'usuario2', 'usuario3']  # Lista de nombres de usuario autorizados

    def dispatch(self, request, *args, **kwargs):
        # Verificar si el usuario actual está en la lista de autorizados
        if request.user.username not in self.usuarios_autorizados:
            return HttpResponseForbidden("No tienes permisos para acceder a esta página.")
        return super().dispatch(request, *args, **kwargs) 