from apps.sirtee.catalogos.models.base import BaseCatalogo


class SistemaConstructivo(BaseCatalogo):
    """
    Sistema o componente constructivo afectado.
    """

    class Meta:

        db_table = "sirtee_cat_sistema_constructivo"

        verbose_name = "Sistema constructivo"

        verbose_name_plural = "Sistemas constructivos"