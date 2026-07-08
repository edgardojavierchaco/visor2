from apps.sirtee.models.hallazgos import Hallazgo


class HallazgoService:

    @staticmethod
    def crear_hallazgo(data, user):
        return Hallazgo.objects.create(
            relevamiento=data["relevamiento"],
            categoria=data.get("categoria"),
            criticidad=data.get("criticidad", "MEDIA"),
            estado="ABIERTO",
            titulo=data["titulo"],
            descripcion=data.get("descripcion"),
            ubicacion=data.get("ubicacion"),
            evidencia=data.get("evidencia"),
            usuario_responsable=str(user)
        )

    @staticmethod
    def marcar_en_analisis(hallazgo):
        hallazgo.estado = "EN_ANALISIS"
        hallazgo.save()
        return hallazgo

    @staticmethod
    def resolver_hallazgo(hallazgo, user):
        hallazgo.estado = "RESUELTO"
        hallazgo.usuario_responsable = str(user)
        hallazgo.save()
        return hallazgo