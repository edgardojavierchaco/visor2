import logging
import re

from django.conf import settings
from django.core.mail import send_mail
from django.urls import reverse
from django.utils import timezone

logger = logging.getLogger(__name__)


def correo_invalido(correo):

    if not correo:
        return True

    correo = correo.strip()

    if '/' in correo:
        return True

    if ';' in correo:
        return True

    if ',' in correo:
        return True

    if correo.count('@') != 1:
        return True

    patron = r'^[^@\s]+@[^@\s]+\.[^@\s]+$'

    return not re.match(
        patron,
        correo
    )


def enviar_email_dispositivo(
    request,
    user,
    dispositivo
):

    try:

        # ==========================
        # VALIDAR CORREO
        # ==========================
        if correo_invalido(user.correo):

            dispositivo.bloqueado = True
            dispositivo.ultimo_error_envio = (
                f'Correo inválido: {user.correo}'
            )

            dispositivo.save(
                update_fields=[
                    'bloqueado',
                    'ultimo_error_envio'
                ]
            )

            logger.error(
                f'CORREO INVALIDO: '
                f'{user.username} - {user.correo}'
            )

            return False

        # ==========================
        # ARMAR URL
        # ==========================
        url = request.build_absolute_uri(
            reverse(
                'logueo:confirmar_dispositivo',
                args=[dispositivo.token]
            )
        )

        asunto = (
            'Nuevo dispositivo detectado'
        )

        mensaje = f"""
Hola {user.username}

Detectamos un ingreso desde un nuevo dispositivo
en Visor Educativo Chaco.

IP:
{dispositivo.ip}

Para autorizar este equipo hacé click
en el siguiente enlace:

{url}

El enlace expira en 48 horas.

Visor Educativo Chaco
"""

        # ==========================
        # ENVIAR MAIL
        # ==========================
        send_mail(
            asunto,
            mensaje,
            settings.DEFAULT_FROM_EMAIL,
            [user.correo.strip()],
            fail_silently=False
        )

        # ==========================
        # ÉXITO
        # ==========================
        dispositivo.email_enviado = True
        dispositivo.ultimo_error_envio = None
        dispositivo.fecha_envio_email = timezone.now()
        dispositivo.fecha_ultimo_intento = timezone.now()

        dispositivo.save(
            update_fields=[
                'email_enviado',
                'ultimo_error_envio',
                'fecha_envio_email',
                'fecha_ultimo_intento'
            ]
        )

        logger.info(
            f'Correo enviado correctamente a '
            f'{user.correo}'
        )

        return True

    except Exception as e:

        logger.error(
            f'Error enviando correo a '
            f'{user.correo}: {str(e)}'
        )

        dispositivo.email_enviado = False
        dispositivo.intentos_envio += 1
        dispositivo.ultimo_error_envio = str(e)
        dispositivo.fecha_ultimo_intento = timezone.now()

        if dispositivo.intentos_envio >= 5:

            dispositivo.bloqueado = True

            logger.error(
                f'DISPOSITIVO BLOQUEADO '
                f'POR EXCESO DE ERRORES: '
                f'{user.correo}'
            )

        dispositivo.save(
            update_fields=[
                'email_enviado',
                'intentos_envio',
                'ultimo_error_envio',
                'fecha_ultimo_intento',
                'bloqueado'
            ]
        )

        return False