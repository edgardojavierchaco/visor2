from django.db import models
from apps.sirtee.querysets.base import SirteeQuerySet


class SirteeManager(models.Manager):
    """
    Manager base para todo SIRTEE.
    Centraliza acceso, soft delete y auditoría.
    """

    def get_queryset(self):
        return SirteeQuerySet(self.model, using=self._db)

    # -------------------------
    # PROXYS DE QUERYSET
    # -------------------------

    def activos(self):
        return self.get_queryset().activos()

    def eliminados(self):
        return self.get_queryset().eliminados()

    def recientes(self, limite=50):
        return self.get_queryset().recientes(limite)

    def actualizados_recientemente(self):
        return self.get_queryset().actualizados_recientemente()

    def con_auditoria(self):
        return self.get_queryset().con_auditoria()

    # -------------------------
    # OPERACIONES MASIVAS
    # -------------------------

    def borrar_logico(self):
        return self.get_queryset().borrar_logico()

    def restaurar(self):
        return self.get_queryset().restaurar()

    def borrar_fisico(self):
        return self.get_queryset().borrar_fisico()