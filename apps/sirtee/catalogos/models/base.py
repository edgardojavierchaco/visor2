from django.db import models

from apps.sirtee.catalogos.managers import CatalogoManager


class BaseCatalogo(models.Model):
    """
    Clase base para todos los catálogos técnicos.

    Será heredada por:
        SistemaConstructivo
        AreaAfectada
        Criticidad
        Riesgo
        etc.
    """

    codigo = models.CharField(
        max_length=40,
        unique=True,
    )

    nombre = models.CharField(
        max_length=200,
    )

    descripcion = models.TextField(
        blank=True,
    )

    orden = models.PositiveIntegerField(
        default=0,
    )

    activo = models.BooleanField(
        default=True,
    )

    objects = CatalogoManager()

    class Meta:

        abstract = True

        ordering = [
            "orden",
            "nombre",
        ]

    def __str__(self):

        return self.nombre