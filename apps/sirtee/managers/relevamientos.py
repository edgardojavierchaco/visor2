from django.db import models


class RelevamientoQuerySet(models.QuerySet):

    def activos(self):
        return self.filter(deleted_at__isnull=True)

    def por_estado(self, estado):
        return self.filter(estado=estado)

    def por_escuela(self, cueanexo):
        return self.filter(escuela__cueanexo=cueanexo)

    def criticos(self):
        return self.filter(hallazgo__criticidad="CRITICA").distinct()

    def en_proceso(self):
        return self.filter(estado="EN_PROCESO")


class RelevamientoManager(models.Manager):

    def get_queryset(self):
        return RelevamientoQuerySet(self.model, using=self._db)

    def activos(self):
        return self.get_queryset().activos()

    def criticos(self):
        return self.get_queryset().criticos()

    def por_escuela(self, cueanexo):
        return self.get_queryset().por_escuela(cueanexo)

    def en_proceso(self):
        return self.get_queryset().en_proceso()