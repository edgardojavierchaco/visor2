from django.db import models

from apps.sirtee.catalogos.models.base import BaseCatalogo


class Prioridad(BaseCatalogo):
    """
    Prioridad institucional.
    """

    nivel = models.PositiveSmallIntegerField(
        default=1,
    )

    color = models.CharField(
        max_length=20,
        default="secondary",
    )

    class Meta:

        db_table = "sirtee_cat_prioridad"

        verbose_name = "Prioridad"

        verbose_name_plural = "Prioridades"

        ordering = [
            "-nivel",
            "nombre",
        ]