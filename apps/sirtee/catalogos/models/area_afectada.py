from apps.sirtee.catalogos.models.base import BaseCatalogo


class AreaAfectada(BaseCatalogo):
    """
    Área física donde se detectó el hallazgo.
    """

    class Meta:

        db_table = "sirtee_cat_area_afectada"

        verbose_name = "Área afectada"

        verbose_name_plural = "Áreas afectadas"