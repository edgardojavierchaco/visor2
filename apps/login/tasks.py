from datetime import timedelta

from celery import shared_task
from django.utils import timezone

from .models import DispositivoUsuario
from .email_dispositivo import (
    enviar_email_dispositivo
)

from django.db.models import Q


@shared_task
def reenviar_dispositivos_pendientes():

    limite = (
        timezone.now() -
        timedelta(hours=6)
    )

    pendientes = (
        DispositivoUsuario.objects.filter(
            confirmado=False,
            email_enviado=False
        )
        .filter(
            Q(fecha_ultimo_intento__lt=limite) |
            Q(fecha_ultimo_intento__isnull=True)
        )
    )

    total = 0

    class FakeRequest:

        def build_absolute_uri(
            self,
            url
        ):
            return (
                'https://visoreducativochaco.com.ar'
                + url
            )

    for dispositivo in pendientes:

        enviado = (
            enviar_email_dispositivo(
                FakeRequest(),
                dispositivo.usuario,
                dispositivo
            )
        )

        if enviado:
            total += 1

    return total