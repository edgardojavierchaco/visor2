from django.db import models
from django.core.exceptions import ValidationError

import os

from apps.sirtee.models.mixins import (
    AuditoriaMixin,
    SoftDeleteMixin,
)

from apps.sirtee.utils.upload import upload_hallazgo

from apps.usuarios.models import UsuariosVisualizador



class EvidenciaHallazgo(
    AuditoriaMixin,
    SoftDeleteMixin,
    models.Model
):


    class TipoArchivo(models.TextChoices):

        IMAGEN = (
            "IMAGEN",
            "Imagen"
        )

        DOCUMENTO = (
            "DOCUMENTO",
            "Documento"
        )

        VIDEO = (
            "VIDEO",
            "Video"
        )

        OTRO = (
            "OTRO",
            "Otro"
        )


    # ======================================================
    # RELACIÓN
    # ======================================================

    hallazgo = models.ForeignKey(

        "sirtee.Hallazgo",

        on_delete=models.CASCADE,

        related_name="evidencias",
    )



    usuario = models.ForeignKey(

        UsuariosVisualizador,

        on_delete=models.PROTECT,

        null=True,

        blank=True,

        related_name="evidencias_hallazgos"
    )



    # ======================================================
    # ARCHIVO
    # ======================================================


    archivo = models.FileField(

        upload_to=upload_hallazgo
    )



    tipo_archivo = models.CharField(

        max_length=20,

        choices=TipoArchivo.choices,

        default=TipoArchivo.OTRO
    )



    descripcion = models.CharField(

        max_length=255,

        blank=True
    )



    principal = models.BooleanField(

        default=False,

        help_text=
        "Evidencia principal del hallazgo"
    )



    fecha_carga = models.DateTimeField(

        auto_now_add=True
    )



    # ======================================================
    # META
    # ======================================================


    class Meta:

        db_table = (
            "sirtee_hallazgo_evidencias"
        )

        verbose_name = (
            "Evidencia de hallazgo"
        )

        verbose_name_plural = (
            "Evidencias de hallazgos"
        )

        ordering = [
            "-fecha_carga"
        ]



    # ======================================================
    # STR
    # ======================================================


    def __str__(self):

        return (
            f"Evidencia {self.id} "
            f"- Hallazgo {self.hallazgo_id}"
        )



    # ======================================================
    # VALIDACIONES
    # ======================================================


    def clean(self):

        if not self.archivo:
            return


        extension = (
            self.extension
        )


        permitidas = [

            ".jpg",
            ".jpeg",
            ".png",
            ".webp",
            ".pdf",
            ".doc",
            ".docx",
            ".xls",
            ".xlsx",

        ]


        if extension not in permitidas:

            raise ValidationError(
                "Tipo de archivo no permitido."
            )



    # ======================================================
    # PROPIEDADES
    # ======================================================


    @property
    def nombre_archivo(self):

        return os.path.basename(
            self.archivo.name
        )



    @property
    def extension(self):

        return os.path.splitext(
            self.archivo.name
        )[1].lower()



    @property
    def es_imagen(self):

        return (
            self.tipo_archivo
            ==
            self.TipoArchivo.IMAGEN
        )



    @property
    def es_documento(self):

        return (
            self.tipo_archivo
            ==
            self.TipoArchivo.DOCUMENTO
        )



    @property
    def url(self):

        if self.archivo:

            return self.archivo.url

        return ""



    # ======================================================
    # HELPERS
    # ======================================================


    def marcar_principal(self):

        EvidenciaHallazgo.objects.filter(
            hallazgo=self.hallazgo
        ).update(
            principal=False
        )


        self.principal=True

        self.save()
    
    
    # ======================================================
    # MÉTODOS AUXILIARES
    # ======================================================


    def tipo_detectado(self):

        extension = self.extension


        imagenes = [

            ".jpg",
            ".jpeg",
            ".png",
            ".webp"

        ]


        documentos = [

            ".pdf",
            ".doc",
            ".docx",
            ".xls",
            ".xlsx"

        ]


        if extension in imagenes:

            return self.TipoArchivo.IMAGEN



        if extension in documentos:

            return self.TipoArchivo.DOCUMENTO



        return self.TipoArchivo.OTRO