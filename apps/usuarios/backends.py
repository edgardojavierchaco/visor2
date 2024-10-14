from django.contrib.auth.backends import BaseBackend
from .models import UsuariosVisualizador
import hashlib

class CustomAuthBackend(BaseBackend):
    """
    Backend de autenticación personalizado para el modelo UsuariosVisualizador.

    Este backend permite la autenticación de usuarios utilizando el modelo
    UsuariosVisualizador y comparando la contraseña cifrada con la proporcionada.

    Métodos:
        authenticate: Autentica a un usuario con nombre de usuario y contraseña.
        get_user: Recupera un usuario basado en su ID.
        check_password: Verifica si la contraseña proporcionada coincide con la almacenada.
    """
    
    def authenticate(self, request, username=None, password=None):
        """
        Autentica a un usuario utilizando su nombre de usuario y contraseña.

        Parámetros:
            request: La solicitud HTTP en curso.
            username: Nombre de usuario del usuario a autenticar.
            password: Contraseña proporcionada para la autenticación.

        Retorna:
            El objeto UsuarioVisualizador si la autenticación es exitosa, de lo contrario None.
        """
        
        try:
            user = UsuariosVisualizador.objects.get(username=username)
            if password is not None and self.check_password(user, password):
                return user
        except UsuariosVisualizador.DoesNotExist:
            return None

    def get_user(self, user_id):
        """
        Recupera un usuario basado en su ID.

        Parámetros:
            user_id: El ID del usuario a recuperar.

        Retorna:
            El objeto UsuarioVisualizador correspondiente al ID, o None si no existe.
        """
        
        try:
            return UsuariosVisualizador.objects.get(pk=user_id)
        except UsuariosVisualizador.DoesNotExist:
            return None
    
    def check_password(self, user, password):
        """
        Verifica si la contraseña proporcionada coincide con la almacenada.

        Parámetros:
            user: El objeto UsuarioVisualizador para el cual se verifica la contraseña.
            password: La contraseña proporcionada por el usuario.

        Retorna:
            True si las contraseñas coinciden, de lo contrario False.
        """
        
        # Cifra la contraseña proporcionada utilizando SHA256 en hexadecimal
        hashed_password = hashlib.sha256(password.encode()).hexdigest()
        # Compara la contraseña cifrada con la contraseña almacenada en el usuario
        return hashed_password == user.password
