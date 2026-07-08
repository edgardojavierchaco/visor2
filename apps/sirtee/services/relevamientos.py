from apps.sirtee.models.relevamientos import Relevamiento
from apps.sirtee.models.hallazgos import Hallazgo


class RelevamientoService:

    @staticmethod
    def crear_relevamiento(data, user):
        obj = Relevamiento.objects.create(
            escuela=data["escuela"],
            fecha=data.get("fecha"),
            estado="ABIERTO",
            tipo_relevamiento=data.get("tipo_relevamiento"),
            observaciones=data.get("observaciones"),
            usuario_creador=str(user)
        )
        return obj

    @staticmethod
    def marcar_en_proceso(relevamiento):
        relevamiento.estado = "EN_PROCESO"
        relevamiento.save()
        return relevamiento

    @staticmethod
    def cerrar_relevamiento(relevamiento):
        """
        Solo se cierra si no hay hallazgos críticos abiertos.
        """
        criticos = Hallazgo.objects.filter(
            relevamiento=relevamiento,
            criticidad="CRITICA",
            estado__in=["ABIERTO", "EN_ANALISIS"]
        )

        if criticos.exists():
            raise Exception("No se puede cerrar: existen hallazgos críticos activos")

        relevamiento.estado = "FINALIZADO"
        relevamiento.save()
        return relevamiento