from celery import shared_task

from .maintenance import actualizar_asistencia


@shared_task(
    bind=True,
    name="asistencia.actualizar_asistencia_diaria",
    acks_late=True,
)
def actualizar_asistencia_diaria(self):
    """
    Tarea nocturna programada por django-celery-beat.
    Reprocesa mes anterior y mes actual.
    """
    return actualizar_asistencia(
        incluir_mes_anterior=True,
    )
