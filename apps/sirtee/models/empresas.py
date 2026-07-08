from django.db import models

from apps.sirtee.models.mixins import (
    AuditoriaMixin,
    SoftDeleteMixin,
)

from apps.sirtee.managers.base import SirteeManager


class Empresa(
    AuditoriaMixin,
    SoftDeleteMixin,
    models.Model,
):
    """
    Empresa contratista, proveedora o ejecutora
    vinculada a intervenciones de infraestructura.
    """

    # =====================================
    # IDENTIFICACIÓN
    # =====================================

    razon_social = models.CharField(
        max_length=255,
        unique=True,
        db_index=True
    )


    nombre_fantasia = models.CharField(
        max_length=255,
        blank=True,
        null=True,
    )


    cuit = models.CharField(
        max_length=13,
        blank=True,
        null=True,
        unique=True,
    )


    # =====================================
    # CLASIFICACIÓN
    # =====================================

    TIPO_CHOICES = [

        (
            "CONSTRUCTORA",
            "Constructora"
        ),

        (
            "SERVICIOS",
            "Servicios"
        ),

        (
            "PROVEEDOR",
            "Proveedor"
        ),

        (
            "OTRA",
            "Otra"
        ),

    ]


    tipo = models.CharField(
        max_length=30,
        choices=TIPO_CHOICES,
        default="CONSTRUCTORA",
    )
    
    # =====================================
    # DATOS ADMINISTRATIVOS
    # =====================================


    registro_empresa = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Registro o matrícula"
    )


    condicion_fiscal = models.CharField(
        max_length=100,
        blank=True,
        null=True,
    )

    # =====================================
    # CONTACTO
    # =====================================


    telefono = models.CharField(
        max_length=50,
        blank=True,
        null=True,
    )


    email = models.EmailField(
        blank=True,
        null=True,
        db_index=True
    )


    domicilio = models.CharField(
        max_length=255,
        blank=True,
        null=True,
    )


    localidad = models.CharField(
        max_length=100,
        blank=True,
        null=True,
    )


    responsable = models.CharField(
        max_length=150,
        blank=True,
        null=True,
        help_text="Persona de contacto"
    )


    # =====================================
    # ESTADO
    # =====================================
    activa = models.BooleanField(
        default=True,
    )


    observaciones = models.TextField(
        blank=True,
        null=True,
    )


    # =====================================
    # MANAGER
    # =====================================


    objects = SirteeManager()



    # =====================================
    # META
    # =====================================


    class Meta:

        db_table = "sirtee_empresas"

        verbose_name = "Empresa"

        verbose_name_plural = "Empresas"

        ordering = [
            "razon_social"
        ]



    # =====================================
    # REPRESENTACIÓN
    # =====================================


    def __str__(self):

        return self.razon_social