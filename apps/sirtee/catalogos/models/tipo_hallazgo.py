from apps.sirtee.catalogos.models.base import BaseCatalogo


class TipoHallazgo(BaseCatalogo):
    """
    Tipo técnico del hallazgo.
    """

    class Meta:

        db_table = "sirtee_cat_tipo_hallazgo"

        verbose_name = "Tipo de hallazgo"

        verbose_name_plural = "Tipos de hallazgo"