from django.db import models

from apps.usuarios.models import UsuariosVisualizador
from apps.supervisa2.models import Region, SituacionRevista, NivelModalidad

from apps.supervisa2.models.validators import validate_phone, validate_email_strict


# =========================================================
# RESPONSABLE REGIONAL
# =========================================================
class ResponsableRegional(models.Model):

    usuario = models.OneToOneField(
        UsuariosVisualizador,
        on_delete=models.PROTECT,
        related_name="responsable_regional"
    )

    regiones = models.ManyToManyField(Region, blank=True)

    puede_crear_supervisores = models.BooleanField(default=True)

    puede_modificar_supervisores = models.BooleanField(default=True)

    puede_eliminar_supervisores = models.BooleanField(default=False)

    activo = models.BooleanField(default=True)

    class Meta:
        db_table = "supervisor_registro_responsable_regional"
        verbose_name = "Responsable Regional"
        verbose_name_plural = "Responsables Regionales"
        indexes = [models.Index(fields=["activo"])]

    def __str__(self):
        return f"({self.usuario.username}) {self.usuario.apellido} {self.usuario.nombres}"


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

    activo = models.BooleanField(default=True)

    fecha_alta = models.DateTimeField(auto_now_add=True)

    fecha_modificacion = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "supervisor_registro_supervisor"
        verbose_name = "Supervisor"
        verbose_name_plural = "Supervisores"
        indexes = [
            models.Index(fields=["activo", "fecha_alta"]),
        ]

    def __str__(self):
        return f"{self.usuario.apellido}, {self.usuario.nombres}"


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

    fecha_hasta = models.DateField(blank=True, null=True)

    activo = models.BooleanField(default=True)

    class Meta:
        db_table = "supervisor_registro_supervisor_situacion"
        indexes = [
            models.Index(fields=["supervisor", "activo"]),
            models.Index(fields=["situacion_revista", "activo"]),
        ]

    def __str__(self):
        return f"{self.supervisor} - {self.situacion_revista}"


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
    # Null para operaciones hechas por Administrador/Funcionario cuando
    # no existe un ResponsableRegional asociado.

    responsable_alta = models.ForeignKey(
        ResponsableRegional,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="altas_supervisores"
    )

    fecha_alta = models.DateTimeField(auto_now_add=True)

    activo = models.BooleanField(default=True)

    class Meta:
        db_table = "supervisor_registro_supervisor_regional"
        unique_together = ("supervisor", "region")    
        indexes = [
            models.Index(fields=["supervisor", "region"]),
            models.Index(fields=["region", "activo"]),
            models.Index(fields=["supervisor", "activo"]),
        ]

    def __str__(self):
        return f"{self.supervisor} - {self.region}"


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
        db_table = "supervisor_registro_supervisor_regional_nivel"
        unique_together = ("supervisor_regional", "nivel")
        indexes = [
            models.Index(fields=["supervisor_regional", "activo"]),
            models.Index(fields=["nivel", "activo"]),
        ]

    def __str__(self):
        return f"{self.supervisor_regional} - {self.nivel}"


# =========================================================
# OFERTAS POR REGIONAL
# =========================================================
class SupervisorRegionalOferta(models.Model):
    supervisor_regional = models.ForeignKey(
        SupervisorRegional,
        on_delete=models.CASCADE,
        related_name="ofertas",
    )
    cueanexo = models.CharField(max_length=9)
    nom_est = models.CharField(max_length=255)
    oferta = models.CharField(max_length=255)
    acronimo = models.CharField(max_length=100, blank=True, null=True)
    fecha_alta = models.DateTimeField(auto_now_add=True)
    activo = models.BooleanField(default=True)

    class Meta:
        db_table = "supervisor_registro_supervisor_regional_oferta"
        unique_together = ("supervisor_regional", "cueanexo", "oferta")
        indexes = [
            models.Index(fields=["supervisor_regional", "activo"]),
            models.Index(fields=["cueanexo"]),
        ]

    def __str__(self):
        return f"{self.cueanexo} - {self.oferta}"