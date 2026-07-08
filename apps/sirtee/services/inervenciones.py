from django.utils import timezone
from apps.sirtee.models.intervenciones import Intervencion


class IntervencionService:

    @staticmethod
    def iniciar_intervencion(intervencion):
        intervencion.estado = "EN_EJECUCION"
        intervencion.fecha_inicio = timezone.now()
        intervencion.save()
        return intervencion

    @staticmethod
    def actualizar_avance(intervencion, porcentaje):
        intervencion.porcentaje_avance = porcentaje

        if porcentaje >= 100:
            intervencion.estado = "FINALIZADA"
            intervencion.fecha_fin = timezone.now()

        intervencion.save()
        return intervencion

    @staticmethod
    def registrar_costos(intervencion, costo_real):
        intervencion.costo_real = costo_real
        intervencion.save()
        return intervencion

    @staticmethod
    def bloquear(intervencion):
        intervencion.estado = "BLOQUEADO"
        intervencion.save()
        return intervencion