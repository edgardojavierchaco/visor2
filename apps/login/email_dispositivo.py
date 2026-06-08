import logging
from django.core.mail import send_mail
from django.urls import reverse
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)


def enviar_email_dispositivo(
    request,
    user,
    dispositivo
):
    try:
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

    Detectamos un ingreso
    desde un nuevo dispositivo en Visor Educativo Chaco.

    IP:
    {dispositivo.ip}

    Para autorizar este equipo hacé click en el siguiente enlace:

    {url}

    El enlace expira
    en  48 horas.

    Visor Educativo Chaco
    """

        send_mail(
            asunto,
            mensaje,
            settings.DEFAULT_FROM_EMAIL,
            [user.correo],
            fail_silently=False
        )
        
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
        
        return True

    except Exception as e:
        logger.error(f"Error enviando correo a:"
            f"{user.correo}: {str(e)}"        
        )
        
        dispositivo.email_enviado = False
        dispositivo.intentos_envio += 1
        dispositivo.ultimo_error_envio = str(e)
        dispositivo.fecha_ultimo_intento = timezone.now()

        dispositivo.save(
            update_fields=[
                'email_enviado',
                'intentos_envio',
                'ultimo_error_envio',
                'fecha_ultimo_intento'
            ]
        )
        
        return False
        