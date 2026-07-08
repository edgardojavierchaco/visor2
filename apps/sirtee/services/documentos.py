from apps.sirtee.models.documentos import Documento


class DocumentoService:

    @staticmethod
    def subir_documento(data, archivo, user):
        return Documento.objects.create(
            tipo=data["tipo"],
            titulo=data["titulo"],
            archivo=archivo,
            relevamiento=data.get("relevamiento"),
            hallazgo=data.get("hallazgo"),
            intervencion=data.get("intervencion"),
        )

    @staticmethod
    def vincular_a_hallazgo(documento, hallazgo):
        documento.hallazgo = hallazgo
        documento.save()
        return documento

    @staticmethod
    def vincular_a_intervencion(documento, intervencion):
        documento.intervencion = intervencion
        documento.save()
        return documento

    @staticmethod
    def listar_por_entidad(entidad, obj_id):
        if entidad == "hallazgo":
            return Documento.objects.filter(hallazgo_id=obj_id)

        if entidad == "intervencion":
            return Documento.objects.filter(intervencion_id=obj_id)

        if entidad == "relevamiento":
            return Documento.objects.filter(relevamiento_id=obj_id)

        return Documento.objects.none()