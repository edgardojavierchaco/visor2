from celery import shared_task

from .maintenance import actualizar_asistencia


@shared_task(bind=True, name="asistencia.actualizar_asistencia_diaria", acks_late=True)
def actualizar_asistencia_diaria(self):
    """02:30 diario: sólo mes actual para mantener bajo el costo operativo."""
    return actualizar_asistencia(incluir_mes_anterior=False)


@shared_task(bind=True, name="asistencia.reprocesar_asistencia_semanal", acks_late=True)
def reprocesar_asistencia_semanal(self):
    """Reproceso de regularizaciones: mes anterior + mes actual."""
    return actualizar_asistencia(incluir_mes_anterior=True)
