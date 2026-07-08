from django.db import models
from apps.sirtee.catalogos.models.base import BaseCatalogo


class Criticidad(BaseCatalogo):
    """
    Nivel de criticidad del hallazgo.
    """

    color = models.CharField(
        max_length=20,
        default="secondary",
    )

    nivel = models.PositiveSmallIntegerField(
        default=1,
    )

    class Meta:

        db_table = "sirtee_cat_criticidad"

        verbose_name = "Criticidad"

        verbose_name_plural = "Criticidades"

        ordering = [
            "-nivel",
            "nombre",
        ]