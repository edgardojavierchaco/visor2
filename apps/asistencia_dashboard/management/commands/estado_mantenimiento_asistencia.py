from django.core.management.base import BaseCommand
from django.db import connections
from django_celery_beat.models import PeriodicTask

from apps.asistencia_dashboard.maintenance import DB_ALIAS, TABLA_CONTROL


TASK_NAMES = ["Actualización diaria Asistencia SGE", "Reproceso semanal Asistencia SGE"]


class Command(BaseCommand):
    help = "Muestra tareas periódicas y el último procesamiento analítico de asistencia."

    def handle(self, *args, **options):
        for nombre in TASK_NAMES:
            self.stdout.write(f"\n{nombre}")
            try:
                task = PeriodicTask.objects.select_related("crontab").get(name=nombre)
            except PeriodicTask.DoesNotExist:
                self.stdout.write(self.style.WARNING("  No configurada."))
                continue
            self.stdout.write(f"  Habilitada: {task.enabled}")
            if task.crontab:
                self.stdout.write(f"  Horario: {str(task.crontab.hour).zfill(2)}:{str(task.crontab.minute).zfill(2)} · día={task.crontab.day_of_week}")
            self.stdout.write(f"  Última ejecución: {task.last_run_at or 'Nunca'}")
            self.stdout.write(f"  Total ejecuciones: {task.total_run_count}")

        self.stdout.write("\nÚltimo procesamiento analítico")
        try:
            with connections[DB_ALIAS].cursor() as cursor:
                cursor.execute("SELECT to_regclass(%s)", [TABLA_CONTROL])
                if cursor.fetchone()[0] is None:
                    self.stdout.write(self.style.WARNING("  Todavía no hay auditoría registrada."))
                    return
                cursor.execute(f"SELECT proceso, anio, mes, fecha_inicio, fecha_fin, estado, fecha_dato_max, mensaje FROM {TABLA_CONTROL} ORDER BY fecha_inicio DESC LIMIT 1")
                row = cursor.fetchone()
            if not row:
                self.stdout.write(self.style.WARNING("  Sin ejecuciones registradas."))
                return
            proceso, anio, mes, inicio, fin, estado, fecha_max, mensaje = row
            self.stdout.write(f"  Proceso: {proceso}")
            self.stdout.write(f"  Período: {mes:02d}/{anio}")
            self.stdout.write(f"  Inicio: {inicio}")
            self.stdout.write(f"  Fin: {fin or 'En ejecución'}")
            self.stdout.write(f"  Estado: {estado}")
            self.stdout.write(f"  Último dato SGE: {fecha_max or 'Sin dato'}")
            if mensaje:
                self.stdout.write(f"  Mensaje: {mensaje}")
        except Exception as exc:
            self.stdout.write(self.style.WARNING(f"  No se pudo consultar auditoría: {exc}"))
