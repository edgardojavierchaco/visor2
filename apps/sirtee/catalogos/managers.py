from django.db import models


class CatalogoQuerySet(models.QuerySet):

    def activos(self):
        return self.filter(activo=True)

    def inactivos(self):
        return self.filter(activo=False)

    def ordenados(self):
        return self.order_by("orden", "nombre")


class CatalogoManager(models.Manager):

    def get_queryset(self):
        return CatalogoQuerySet(self.model, using=self._db)

    def activos(self):
        return self.get_queryset().activos()

    def ordenados(self):
        return self.get_queryset().ordenados()