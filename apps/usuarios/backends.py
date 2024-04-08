from django.contrib.auth.backends import BaseBackend
import hashlib
from apps.usuarios.models import UsuariosVisualizador

class UsuariosVisualizadorBackend(BaseBackend):
    def authenticate(self, request, username=None, password=None):
        try:
            user = UsuariosVisualizador.objects.get(username=username)
        except UsuariosVisualizador.DoesNotExist:
            return None
        
        # Hashea la contraseña proporcionada utilizando SHA256
        hashed_password = hashlib.sha256(password.encode()).hexdigest()
        
        # Verifica si la contraseña hasheada coincide con la contraseña almacenada en la base de datos
        if hashed_password == user.password:
            return user
        else:
            return None

    def get_user(self, user_id):
        try:
            return UsuariosVisualizador.objects.get(pk=user_id)
        except UsuariosVisualizador.DoesNotExist:
            return None
