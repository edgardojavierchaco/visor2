from datetime import timedelta
import uuid

from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone
from django.db.models import Q

from .models import DispositivoUsuario
from .email_dispositivo import (
    enviar_email_dispositivo
)


@shared_task
def reenviar_dispositivos_pendientes():

    limite = (
        timezone.now() -
        timedelta(hours=6)
    )

    pendientes = (
        DispositivoUsuario.objects.filter(
            confirmado=False,
            email_enviado=False,
            bloqueado=False,
            intentos_envio__lt=5
        )
        .filter(
            Q(fecha_ultimo_intento__lt=limite) |
            Q(fecha_ultimo_intento__isnull=True)
        )
        .order_by('creado')[:50]
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

        # ==========================
        # RENOVAR TOKEN Y VENCIMIENTO
        # ==========================
        dispositivo.token = uuid.uuid4()

        dispositivo.expira = (
            timezone.now() +
            timedelta(hours=48)
        )

        dispositivo.save(
            update_fields=[
                'token',
                'expira'
            ]
        )

        enviado = enviar_email_dispositivo(
            FakeRequest(),
            dispositivo.usuario,
            dispositivo
        )

        if enviado:
            total += 1

    return total

@shared_task
def alerta_dispositivos_problematicos():

    problemas = (
        DispositivoUsuario.objects.filter(
            bloqueado=True
        )
        .select_related('usuario')
    )

    if not problemas.exists():
        return 0

    mensaje = []

    for d in problemas:

        mensaje.append(
            f"""
Usuario: {d.usuario.username}
Correo: {d.usuario.correo}
Intentos: {d.intentos_envio}
Error: {d.ultimo_error_envio}
"""
        )

    try:

        send_mail(
            subject='Alerta dispositivos bloqueados',
            message='\n'.join(mensaje),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[
                'meccyt.planeamiento@chaco.gob.ar'
            ],
            fail_silently=False
        )

        return problemas.count()

    except Exception as e:

        print(
            f'Error enviando alerta: {e}'
        )

        return 0