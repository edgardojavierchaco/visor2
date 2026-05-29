from django.core.mail import send_mail
from django.urls import reverse
from django.conf import settings


def enviar_email_dispositivo(
    request,
    user,
    dispositivo
):

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
en 30 minutos.

Visor Educativo Chaco
"""

    send_mail(
        asunto,
        mensaje,
        settings.DEFAULT_FROM_EMAIL,
        [user.correo],
        fail_silently=False
    )