from datetime import datetime

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django_celery_beat.models import CrontabSchedule, PeriodicTask


DAILY_NAME = "Actualización diaria Asistencia SGE"
DAILY_TASK = "asistencia.actualizar_asistencia_diaria"
WEEKLY_NAME = "Reproceso semanal Asistencia SGE"
WEEKLY_TASK = "asistencia.reprocesar_asistencia_semanal"


class Command(BaseCommand):
    help = "Configura mantenimiento diario y reproceso semanal de asistencia."

    def add_arguments(self, parser):
        parser.add_argument("--hora", default="02:30", help="Hora diaria HH:MM. Default 02:30")
        parser.add_argument("--hora-semanal", default="03:30", help="Hora dominical HH:MM. Default 03:30")
        parser.add_argument("--sin-semanal", action="store_true", help="No crear reproceso semanal")
        parser.add_argument("--deshabilitar", action="store_true")

    def _hora(self, valor):
        try:
            return datetime.strptime(valor, "%H:%M")
        except ValueError as exc:
            raise CommandError(f"Hora inválida: {valor}. Use HH:MM") from exc

    def _crontab(self, hora, day_of_week="*"):
        tz = getattr(settings, "TIME_ZONE", "America/Argentina/Buenos_Aires")
        kw = {
            "minute": str(hora.minute),
            "hour": str(hora.hour),
            "day_of_week": day_of_week,
            "day_of_month": "*",
            "month_of_year": "*",
        }
        try:
            return CrontabSchedule.objects.get_or_create(timezone=tz, **kw)[0]
        except Exception:
            return CrontabSchedule.objects.get_or_create(**kw)[0]

    def handle(self, *args, **options):
        diaria = self._hora(options["hora"])
        schedule = self._crontab(diaria)
        PeriodicTask.objects.update_or_create(
            name=DAILY_NAME,
            defaults={
                "task": DAILY_TASK,
                "crontab": schedule,
                "interval": None,
                "solar": None,
                "clocked": None,
                "enabled": not options["deshabilitar"],
                "description": "Refresco diario del mes actual sin bloquear lecturas del dashboard.",
            },
        )

        if not options["sin_semanal"]:
            semanal = self._hora(options["hora_semanal"])
            schedule_week = self._crontab(semanal, day_of_week="sun")
            PeriodicTask.objects.update_or_create(
                name=WEEKLY_NAME,
                defaults={
                    "task": WEEKLY_TASK,
                    "crontab": schedule_week,
                    "interval": None,
                    "solar": None,
                    "clocked": None,
                    "enabled": not options["deshabilitar"],
                    "description": "Domingo: reprocesa mes anterior y actual para absorber regularizaciones.",
                },
            )

        estado = "deshabilitadas" if options["deshabilitar"] else "configuradas"
        self.stdout.write(self.style.SUCCESS(f"Tareas {estado}. Diario {options['hora']}"))
        if not options["sin_semanal"]:
            self.stdout.write(f"Reproceso semanal: domingo {options['hora_semanal']}")
