from django.contrib.auth.backends import BaseBackend
from .models import UsuariosVisualizador
import hashlib

class CustomAuthBackend(BaseBackend):
    def authenticate(self, request, username=None, password=None):
        try:
            user = UsuariosVisualizador.objects.get(username=username)
            if password is not None and self.check_password(user, password):
                return user
        except UsuariosVisualizador.DoesNotExist:
            return None

    def get_user(self, user_id):
        try:
            return UsuariosVisualizador.objects.get(pk=user_id)
        except UsuariosVisualizador.DoesNotExist:
            return None
    
    def check_password(self, user, password):
        # Cifra la contraseña proporcionada utilizando SHA256 en hexadecimal
        hashed_password = hashlib.sha256(password.encode()).hexdigest()
        # Compara la contraseña cifrada con la contraseña almacenada en el usuario
        return hashed_password == user.password
