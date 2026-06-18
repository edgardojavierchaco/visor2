from django.db import models

from apps.usuarios.models import UsuariosVisualizador
from apps.supervisa2.models import (
    Region,
    SituacionRevista,
    NivelModalidad
)

from apps.supervisa2.models.validators import (
    validate_phone,
    validate_email_strict
)


# =========================================================
# RESPONSABLE REGIONAL
# =========================================================

class ResponsableRegional(models.Model):

    usuario = models.OneToOneField(
        UsuariosVisualizador,
        on_delete=models.PROTECT
    )

    regiones = models.ManyToManyField(
        Region
    )

    puede_crear_supervisores = models.BooleanField(
        default=True
    )

    puede_modificar_supervisores = models.BooleanField(
        default=True
    )

    puede_eliminar_supervisores = models.BooleanField(
        default=False
    )

    activo = models.BooleanField(
        default=True
    )

    class Meta:
        db_table = "supervisor_registro_responsable_regional"
        verbose_name = "Responsable Regional"
        verbose_name_plural = "Responsables Regionales"

    def __str__(self):
        return (
            f"({self.usuario.username}) "
            f"{self.usuario.apellido} "
            f"{self.usuario.nombres}"
        )


# =========================================================
# SUPERVISOR
# SE CREA UNA SOLA VEZ
# =========================================================

class ABMSupervisores(models.Model):

    usuario = models.OneToOneField(
        UsuariosVisualizador,
        to_field="username",
        db_column="cuil",
        on_delete=models.PROTECT,
        related_name="supervisor"
    )

    telefono = models.CharField(
        max_length=30,
        blank=True,
        null=True,
        validators=[validate_phone]
    )

    email = models.EmailField(
        blank=True,
        null=True,
        validators=[validate_email_strict]
    )

    activo = models.BooleanField(
        default=True
    )

    fecha_alta = models.DateTimeField(
        auto_now_add=True
    )

    fecha_modificacion = models.DateTimeField(
        auto_now=True
    )

    class Meta:
        db_table = "supervisor_registro_supervisor"
        verbose_name = "Supervisor"
        verbose_name_plural = "Supervisores"

    def __str__(self):
        return (
            f"{self.usuario.apellido}, "
            f"{self.usuario.nombres}"
        )


# =========================================================
# SITUACION DE REVISTA
# =========================================================

class SupervisorSituacionRevista(models.Model):

    supervisor = models.ForeignKey(
        ABMSupervisores,
        on_delete=models.CASCADE,
        related_name="situaciones"
    )

    situacion_revista = models.ForeignKey(
        SituacionRevista,
        on_delete=models.PROTECT
    )

    fecha_desde = models.DateField()

    fecha_hasta = models.DateField(
        blank=True,
        null=True
    )

    activo = models.BooleanField(
        default=True
    )

    class Meta:
        db_table = (
            "supervisor_registro_supervisor_situacion"
        )

    def __str__(self):
        return (
            f"{self.supervisor} - "
            f"{self.situacion_revista}"
        )


# =========================================================
# ASIGNACION REGIONAL
# UNA POR CADA REGIONAL
# =========================================================

class SupervisorRegional(models.Model):

    supervisor = models.ForeignKey(
        ABMSupervisores,
        on_delete=models.CASCADE,
        related_name="asignaciones_regionales"
    )

    region = models.ForeignKey(
        Region,
        on_delete=models.PROTECT
    )

    responsable_alta = models.ForeignKey(
        ResponsableRegional,
        on_delete=models.PROTECT
    )

    fecha_alta = models.DateTimeField(
        auto_now_add=True
    )

    activo = models.BooleanField(
        default=True
    )

    class Meta:
        unique_together = (
            "supervisor",
            "region"
        )

        db_table = (
            "supervisor_registro_supervisor_regional"
        )
        
        indexes = [
        models.Index(
            fields=[
                "supervisor",
                "region"
            ]
        )
    ]

    def __str__(self):
        return (
            f"{self.supervisor} - "
            f"{self.region}"
        )


# =========================================================
# NIVELES POR REGIONAL
# =========================================================

class SupervisorRegionalNivel(models.Model):

    supervisor_regional = models.ForeignKey(
        SupervisorRegional,
        on_delete=models.CASCADE,
        related_name="niveles"
    )

    nivel = models.ForeignKey(
        NivelModalidad,
        on_delete=models.PROTECT
    )
    
    activo = models.BooleanField(default=True)

    class Meta:
        unique_together = (
            "supervisor_regional",
            "nivel"
        )

        db_table = (
            "supervisor_registro_supervisor_regional_nivel"
        )

    def __str__(self):
        return (
            f"{self.supervisor_regional} - "
            f"{self.nivel}"
        )


# =========================================================
# OFERTAS POR REGIONAL
# =========================================================

class SupervisorRegionalOferta(models.Model):

    supervisor_regional = models.ForeignKey(
        SupervisorRegional,
        on_delete=models.CASCADE,
        related_name="ofertas"
    )

    cueanexo = models.CharField(
        max_length=9
    )

    nom_est = models.CharField(
        max_length=255
    )

    oferta = models.CharField(
        max_length=255
    )

    acronimo = models.CharField(
        max_length=100,
        blank=True,
        null=True
    )

    fecha_alta = models.DateTimeField(
        auto_now_add=True
    )
    
    activo = models.BooleanField(default=True)

    class Meta:
        unique_together = (
            "supervisor_regional",
            "cueanexo",
            "oferta"
        )

        db_table = (
            "supervisor_registro_supervisor_regional_oferta"
        )

    def __str__(self):
        return (
            f"{self.cueanexo} - "
            f"{self.oferta}"
        )