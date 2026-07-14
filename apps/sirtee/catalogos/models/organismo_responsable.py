from apps.sirtee.catalogos.models.base import BaseCatalogo


class OrganismoResponsable(BaseCatalogo):
    """
    Organismo responsable de ejecutar la intervención.
    """

    class Meta:

        db_table = "sirtee_cat_organismo_responsable"

        verbose_name = "Organismo responsable"

        verbose_name_plural = "Organismos responsables"

        ordering = [
            "nombre",
        ]