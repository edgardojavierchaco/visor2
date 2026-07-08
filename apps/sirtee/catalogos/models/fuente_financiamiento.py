from apps.sirtee.catalogos.models.base import BaseCatalogo


class FuenteFinanciamiento(BaseCatalogo):
    """
    Fuente de financiamiento.
    """

    class Meta:

        db_table = "sirtee_cat_fuente_financiamiento"

        verbose_name = "Fuente de financiamiento"

        verbose_name_plural = "Fuentes de financiamiento"

        ordering = [
            "nombre",
        ]