from django.core.management.base import BaseCommand
from django_celery_beat.models import PeriodicTask


TASK_NAME = "Actualización diaria Asistencia SGE"


class Command(BaseCommand):
    help = "Muestra la configuración de la tarea periódica de asistencia."

    def handle(self, *args, **options):
        try:
            task = PeriodicTask.objects.select_related(
                "crontab"
            ).get(
                name=TASK_NAME
            )
        except PeriodicTask.DoesNotExist:
            self.stdout.write(
                self.style.WARNING(
                    "La tarea periódica todavía no está configurada."
                )
            )
            return

        self.stdout.write(
            f"Nombre: {task.name}"
        )
        self.stdout.write(
            f"Task: {task.task}"
        )
        self.stdout.write(
            f"Habilitada: {task.enabled}"
        )

        if task.crontab:
            self.stdout.write(
                "Horario: "
                f"{task.crontab.hour.zfill(2)}:"
                f"{task.crontab.minute.zfill(2)}"
            )

            timezone_value = getattr(
                task.crontab,
                "timezone",
                None,
            )

            if timezone_value:
                self.stdout.write(
                    f"Zona horaria: {timezone_value}"
                )

        self.stdout.write(
            f"Última ejecución: {task.last_run_at or 'Nunca'}"
        )

        self.stdout.write(
            f"Total ejecuciones: {task.total_run_count}"
        )
