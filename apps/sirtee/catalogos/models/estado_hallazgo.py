from django.db import models
from apps.sirtee.catalogos.models.base import BaseCatalogo


class EstadoHallazgo(BaseCatalogo):
    """
    Estado operativo del hallazgo.
    """

    color = models.CharField(
        max_length=20,
        default="secondary",
    )

    cerrado = models.BooleanField(
        default=False,
    )

    class Meta:

        db_table = "sirtee_cat_estado_hallazgo"

        verbose_name = "Estado del hallazgo"

        verbose_name_plural = "Estados del hallazgo"