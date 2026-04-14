from django.contrib.auth.backends import BaseBackend
from django.contrib.auth.hashers import check_password, make_password
from .models import UsuariosVisualizador
import hashlib


class CustomAuthBackend(BaseBackend):
    """
    Backend de autenticación personalizado para el modelo UsuariosVisualizador.
    """

    def authenticate(self, request, username=None, password=None):
        """
        Autentica a un usuario utilizando su nombre de usuario y contraseña.
        """

        # 🔐 Validación básica
        if not username or not password:
            return None

        # ⚡ Evita excepciones innecesarias
        user = UsuariosVisualizador.objects.filter(username=username).first()

        # 🔐 Validación de contraseña (segura + legacy)
        if user and self.check_password(user, password):
            return user

        return None

    def get_user(self, user_id):
        """
        Recupera un usuario basado en su ID.
        """
        return UsuariosVisualizador.objects.filter(pk=user_id).first()

    def check_password(self, user, password):
        """
        Verifica la contraseña:
        - Usa Django si ya está migrada
        - Soporta SHA256 antiguo
        - Migra automáticamente a hash seguro
        """

        # ✅ Caso moderno (Django hash seguro)
        if user.password.startswith('pbkdf2_'):
            return check_password(password, user.password)

        # 🔄 Caso legacy (SHA256)
        hashed = hashlib.sha256(password.encode()).hexdigest()

        if hashed == user.password:
            # 🔥 Migración automática a Django hash
            user.password = make_password(password)
            user.save(update_fields=['password'])
            return True

        return False