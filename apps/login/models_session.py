from django.db import models
from apps.usuarios.models import UsuariosVisualizador


class SesionUsuario(models.Model):

    usuario = models.ForeignKey(
        UsuariosVisualizador,
        on_delete=models.CASCADE,
        related_name='sesiones'
    )

    session_key = models.CharField(
        max_length=40,
        unique=True
    )

    ip = models.GenericIPAddressField(
        null=True,
        blank=True
    )

    user_agent = models.TextField()

    activa = models.BooleanField(
        default=True
    )

    creada = models.DateTimeField(
        auto_now_add=True
    )

    ultima_actividad = models.DateTimeField(
        auto_now=True
    )

    def __str__(self):
        return (
            f'{self.usuario.username} '
            f'- {self.session_key}'
        )