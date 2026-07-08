from django.db import models


class HallazgoQuerySet(models.QuerySet):

    def activos(self):
        return self.filter(deleted_at__isnull=True)

    def criticos(self):
        return self.filter(criticidad="CRITICA")

    def abiertos(self):
        return self.filter(estado="ABIERTO")

    def en_analisis(self):
        return self.filter(estado="EN_ANALISIS")

    def por_categoria(self, categoria):
        return self.filter(categoria=categoria)

    def por_escuela(self, cueanexo):
        return self.filter(relevamiento__escuela__cueanexo=cueanexo)


class HallazgoManager(models.Manager):

    def get_queryset(self):
        return HallazgoQuerySet(self.model, using=self._db)

    def activos(self):
        return self.get_queryset().activos()

    def criticos(self):
        return self.get_queryset().criticos()

    def abiertos(self):
        return self.get_queryset().abiertos()

    def en_analisis(self):
        return self.get_queryset().en_analisis()

    def por_escuela(self, cueanexo):
        return self.get_queryset().por_escuela(cueanexo)