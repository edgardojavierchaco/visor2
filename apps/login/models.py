import uuid
from datetime import timedelta

from django.db import models
from django.utils import timezone
from apps.usuarios.models import UsuariosVisualizador
from .models_session import SesionUsuario


class DispositivoUsuario(models.Model):

    usuario = models.ForeignKey(
        UsuariosVisualizador,
        on_delete=models.CASCADE,
        related_name='dispositivos'
    )

    fingerprint = models.CharField(
        max_length=64
    )

    ip = models.GenericIPAddressField(
        null=True,
        blank=True
    )

    user_agent = models.TextField()

    confirmado = models.BooleanField(
        default=False
    )

    token = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False
    )

    expira = models.DateTimeField(
        null=True,
        blank=True
    )

    creado = models.DateTimeField(
        auto_now_add=True
    )

    ultimo_uso = models.DateTimeField(
        auto_now=True
    )

    def save(self, *args, **kwargs):

        if not self.expira:
            self.expira = (
                timezone.now() +
                timedelta(minutes=30)
            )

        super().save(
            *args,
            **kwargs
        )

    def token_valido(self):
        
        if not self.expira:
            return False

        return (
            timezone.now() <
            self.expira
        )

    def __str__(self):

        return (
            f'{self.usuario.username}'
        )