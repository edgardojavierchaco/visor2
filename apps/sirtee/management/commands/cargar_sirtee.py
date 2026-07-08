from django.core.management.base import BaseCommand

from apps.sirtee.catalogos.seeds import (
    cargar_catalogos_10_2a,
    cargar_empresas,
)


class Command(BaseCommand):

    help = "Carga datos iniciales SIRTEE"


    def handle(self, *args, **options):

        cargar_catalogos_10_2a()

        cargar_empresas()

        self.stdout.write(
            self.style.SUCCESS(
                "Carga SIRTEE finalizada."
            )
        )