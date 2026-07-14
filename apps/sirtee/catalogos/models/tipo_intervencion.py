from apps.sirtee.catalogos.models.base import BaseCatalogo


class TipoIntervencion(BaseCatalogo):
    """
    Tipo técnico de intervención.
    """

    class Meta:

        db_table = "sirtee_cat_tipo_intervencion"

        verbose_name = "Tipo de intervención"

        verbose_name_plural = "Tipos de intervención"

        ordering = [
            "orden",
            "nombre",
        ]