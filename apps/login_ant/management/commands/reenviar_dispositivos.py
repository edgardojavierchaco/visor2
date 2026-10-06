from django.core.management.base import BaseCommand

from apps.login.models import (
    DispositivoUsuario
)

from apps.login.email_dispositivo import (
    enviar_email_dispositivo
)


class Command(BaseCommand):

    help = (
        'Reenvía correos pendientes '
        'de validación de dispositivos'
    )

    def handle(self, *args, **kwargs):

        pendientes = (
            DispositivoUsuario.objects.filter(
                confirmado=False,
                email_enviado=False
            )
        )

        total = 0

        for dispositivo in pendientes:

            try:

                class FakeRequest:
                    def build_absolute_uri(
                        self,
                        url
                    ):
                        return (
                            'https://visoreducativochaco.com.ar'
                            + url
                        )

                enviado = (
                    enviar_email_dispositivo(
                        FakeRequest(),
                        dispositivo.usuario,
                        dispositivo
                    )
                )

                if enviado:
                    total += 1

            except Exception:
                pass

        self.stdout.write(
            self.style.SUCCESS(
                f'Se reenviaron '
                f'{total} correos.'
            )
        )