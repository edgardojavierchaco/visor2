from apps.sirtee.catalogos.models.base import BaseCatalogo


class Riesgo(BaseCatalogo):
    """
    Riesgo asociado al hallazgo.
    """

    class Meta:

        db_table = "sirtee_cat_riesgo"

        verbose_name = "Riesgo"

        verbose_name_plural = "Riesgos"