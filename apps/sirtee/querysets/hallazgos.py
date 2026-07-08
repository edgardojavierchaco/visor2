from django.db import models


class HallazgoQuerySet(models.QuerySet):

    def activos(self):
        return self.filter(deleted_at__isnull=True)

    def con_relevamiento(self):
        return self.select_related(
            "relevamiento",
            "relevamiento__escuela"
        )

    def criticos(self):
        return self.filter(criticidad="CRITICA")

    def abiertos(self):
        return self.filter(estado="ABIERTO")

    def en_analisis(self):
        return self.filter(estado="EN_ANALISIS")

    def cerrados(self):
        return self.filter(estado="RESUELTO")

    def por_categoria(self, categoria):
        return self.filter(categoria=categoria)

    def por_escuela(self, cueanexo):
        return self.filter(relevamiento__escuela__cueanexo=cueanexo)

    def con_intervenciones(self):
        return self.prefetch_related("intervencion_set")

    def recientes(self):
        return self.order_by("-id")