from django.core.management.base import BaseCommand, CommandError

from apps.asistencia_dashboard.maintenance import actualizar_asistencia


class Command(BaseCommand):
    help = (
        "Actualiza las tablas analíticas de asistencia. "
        "Por defecto reprocesa mes anterior y mes actual."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--solo-mes-actual",
            action="store_true",
            help="No reprocesar el mes anterior.",
        )

    def handle(self, *args, **options):
        try:
            resultado = actualizar_asistencia(
                incluir_mes_anterior=not options["solo_mes_actual"],
            )
        except Exception as exc:
            raise CommandError(
                f"Falló la actualización de asistencia: {exc}"
            ) from exc

        estado = resultado.get("estado")

        if estado == "OMITIDO":
            self.stdout.write(
                self.style.WARNING(
                    resultado.get(
                        "motivo",
                        "Actualización omitida.",
                    )
                )
            )
            return

        self.stdout.write(
            self.style.SUCCESS(
                "Actualización finalizada correctamente."
            )
        )

        for periodo in resultado.get("periodos", []):
            self.stdout.write(
                f"  - {periodo['mes']:02d}/{periodo['anio']}"
            )
