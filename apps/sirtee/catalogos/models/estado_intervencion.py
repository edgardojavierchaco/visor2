from django.db import models

from apps.sirtee.catalogos.models.base import BaseCatalogo


class EstadoIntervencion(BaseCatalogo):
    """
    Estado operativo.
    """

    color = models.CharField(
        max_length=20,
        default="secondary",
    )

    finaliza = models.BooleanField(
        default=False,
    )

    class Meta:

        db_table = "sirtee_cat_estado_intervencion"

        verbose_name = "Estado de intervención"

        verbose_name_plural = "Estados de intervención"

        ordering = [
            "orden",
            "nombre",
        ]