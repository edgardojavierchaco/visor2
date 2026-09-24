from datetime import datetime

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django_celery_beat.models import CrontabSchedule, PeriodicTask


TASK_NAME = "Actualización diaria Asistencia SGE"
TASK_PATH = "asistencia.actualizar_asistencia_diaria"


class Command(BaseCommand):
    help = (
        "Crea o actualiza la tarea periódica nocturna de asistencia "
        "en django-celery-beat."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--hora",
            default="02:30",
            help="Hora diaria en formato HH:MM. Default: 02:30.",
        )

        parser.add_argument(
            "--deshabilitar",
            action="store_true",
            help="Deshabilita la tarea periódica existente.",
        )

    def handle(self, *args, **options):
        hora = options["hora"]

        try:
            dt = datetime.strptime(
                hora,
                "%H:%M",
            )
        except ValueError as exc:
            raise CommandError(
                "La hora debe tener formato HH:MM, por ejemplo 02:30."
            ) from exc

        timezone_name = getattr(
            settings,
            "TIME_ZONE",
            "America/Argentina/Buenos_Aires",
        )

        crontab_kwargs = {
            "minute": str(dt.minute),
            "hour": str(dt.hour),
            "day_of_week": "*",
            "day_of_month": "*",
            "month_of_year": "*",
        }

        # Versiones actuales de django-celery-beat disponen de timezone.
        # El fallback mantiene compatibilidad con versiones más antiguas.
        try:
            schedule, _ = CrontabSchedule.objects.get_or_create(
                timezone=timezone_name,
                **crontab_kwargs,
            )
        except Exception:
            schedule, _ = CrontabSchedule.objects.get_or_create(
                **crontab_kwargs,
            )

        task, created = PeriodicTask.objects.update_or_create(
            name=TASK_NAME,
            defaults={
                "task": TASK_PATH,
                "crontab": schedule,
                "interval": None,
                "solar": None,
                "clocked": None,
                "enabled": not options["deshabilitar"],
                "description": (
                    "Actualiza asistencia institucional, nominal, matrícula, "
                    "calidad de registración y alertas semanales."
                ),
            },
        )

        if options["deshabilitar"]:
            self.stdout.write(
                self.style.WARNING(
                    f"Tarea '{TASK_NAME}' deshabilitada."
                )
            )
            return

        accion = "creada" if created else "actualizada"

        self.stdout.write(
            self.style.SUCCESS(
                f"Tarea {accion}: {TASK_NAME}"
            )
        )

        self.stdout.write(
            f"Horario diario: {hora}"
        )

        self.stdout.write(
            f"Zona horaria: {timezone_name}"
        )
