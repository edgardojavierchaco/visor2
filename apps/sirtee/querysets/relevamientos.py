from django.db import models


class RelevamientoQuerySet(models.QuerySet):

    def activos(self):
        return self.filter(deleted_at__isnull=True)

    def con_escuela(self):
        return self.select_related("escuela")

    def por_estado(self, estado):
        return self.filter(estado=estado)

    def por_tipo(self, tipo):
        return self.filter(tipo_relevamiento=tipo)

    def por_escuela(self, cueanexo):
        return self.filter(escuela__cueanexo=cueanexo)

    def criticos(self):
        return self.filter(hallazgo__criticidad="CRITICA").distinct()

    def con_hallazgos(self):
        return self.prefetch_related("hallazgo_set")

    def recientes(self):
        return self.order_by("-fecha")