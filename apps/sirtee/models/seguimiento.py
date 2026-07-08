from django.db import models
from django.core.exceptions import ValidationError

from apps.sirtee.models.mixins import (
    AuditoriaMixin,
    SoftDeleteMixin,
)

from apps.sirtee.managers.base import SirteeManager



class Seguimiento(
    AuditoriaMixin,
    SoftDeleteMixin,
    models.Model,
):

    """
    Registro histórico de evolución
    de relevamientos, hallazgos e intervenciones.

    Permite mantener trazabilidad operativa.
    """



    # ==================================================
    # RELACIONES
    # ==================================================


    relevamiento = models.ForeignKey(
        "sirtee.Relevamiento",
        on_delete=models.CASCADE,
        related_name="seguimientos",
    )


    hallazgo = models.ForeignKey(
        "sirtee.Hallazgo",
        on_delete=models.CASCADE,
        related_name="seguimientos",
        null=True,
        blank=True,
    )


    intervencion = models.ForeignKey(
        "sirtee.Intervencion",
        on_delete=models.CASCADE,
        related_name="seguimientos",
        null=True,
        blank=True,
    )



    # ==================================================
    # ESTADO
    # ==================================================


    estado = models.CharField(
        max_length=30,
    )



    # ==================================================
    # INFORMACIÓN
    # ==================================================


    comentario = models.TextField()



    usuario = models.ForeignKey(
        "usuarios.UsuariosVisualizador",
        on_delete=models.PROTECT,
        related_name="seguimientos",
        null=True,
        blank=True,
    )



    fecha = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
    )



    # ==================================================
    # MANAGER
    # ==================================================


    objects = SirteeManager()



    # ==================================================
    # META
    # ==================================================


    class Meta:

        db_table = "sirtee_seguimientos"

        verbose_name = (
            "Seguimiento"
        )

        verbose_name_plural = (
            "Seguimientos"
        )

        ordering = [
            "-fecha"
        ]



    # ==================================================
    # VALIDACIÓN
    # ==================================================


    def clean(self):


        if not self.hallazgo and not self.intervencion:

            raise ValidationError(
                "El seguimiento debe estar asociado "
                "a un hallazgo o una intervención."
            )



        if self.hallazgo:

            if (
                self.hallazgo.relevamiento_id
                !=
                self.relevamiento_id
            ):

                raise ValidationError(
                    "El hallazgo no pertenece "
                    "al relevamiento seleccionado."
                )



        if self.intervencion:

            if (
                self.intervencion.hallazgo.relevamiento_id
                !=
                self.relevamiento_id
            ):

                raise ValidationError(
                    "La intervención no pertenece "
                    "al relevamiento seleccionado."
                )



    # ==================================================
    # REPRESENTACIÓN
    # ==================================================


    def __str__(self):

        return (
            f"{self.estado} - "
            f"{self.fecha:%d/%m/%Y %H:%M}"
        )