from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError

from apps.usuarios.models import UsuariosVisualizador
from .catalogos import NivelModalidad, Region, SituacionRevista
from .validators import validate_phone, validate_email_strict, validate_fechas


from django.db import models
from django.utils import timezone

from apps.usuarios.models import UsuariosVisualizador
from apps.supervisa2.models.catalogos import SituacionRevista, NivelModalidad, Region

from apps.supervisa2.models.validators import (
    validate_phone,
    validate_email_strict,
    validate_fechas
)


class Supervisor2(models.Model):

    # =========================================================
    # 🔄 ESTADOS DEL FLUJO
    # =========================================================
    class EstadoValidacion(models.TextChoices):
        PENDIENTE = "PENDIENTE", "Pendiente"
        EN_REVISION = "EN_REVISION", "En revisión"
        APROBADO = "APROBADO", "Aprobado"
        RECHAZADO = "RECHAZADO", "Rechazado"

    # =========================================================
    # 👤 USUARIO
    # =========================================================
    usuario = models.ForeignKey(
        UsuariosVisualizador,
        to_field="username",
        db_column="cuil",
        on_delete=models.PROTECT,
        related_name="supervisores"
    )

    # =========================================================
    # 📋 DATOS PRINCIPALES
    # =========================================================
    situacion_revista = models.ForeignKey(
        SituacionRevista,
        on_delete=models.PROTECT
    )

    fecha_desde = models.DateField()
    fecha_hasta = models.DateField(blank=True, null=True)

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

    niveles_modalidad = models.ManyToManyField(
        NivelModalidad,
        blank=True
    )

    regiones = models.ManyToManyField(
        Region,
        blank=True
    )

    # =========================================================
    # 🔄 ESTADO DE VALIDACIÓN
    # =========================================================
    estado_validacion = models.CharField(
        max_length=20,
        choices=EstadoValidacion.choices,
        default=EstadoValidacion.PENDIENTE
    )

    validado_por = models.ForeignKey(
        UsuariosVisualizador,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="validaciones_realizadas"
    )

    fecha_validacion = models.DateTimeField(
        null=True,
        blank=True
    )

    # =========================================================
    # 📅 AUDITORÍA
    # =========================================================
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # =========================================================
    # 🔍 VALIDACIÓN GENERAL
    # =========================================================
    def clean(self):
        validate_fechas(self.fecha_desde, self.fecha_hasta)

    # =========================================================
    # 🔄 TRANSICIONES DE ESTADO (FLUJO PRO)
    # =========================================================

    def marcar_pendiente(self):
        self.estado_validacion = self.EstadoValidacion.PENDIENTE
        self.validado_por = None
        self.fecha_validacion = None

    def enviar_revision(self):
        self.estado_validacion = self.EstadoValidacion.EN_REVISION
        self.validado_por = None
        self.fecha_validacion = None

    def aprobar(self, user):
        self.estado_validacion = self.EstadoValidacion.APROBADO
        self.validado_por = user
        self.fecha_validacion = timezone.now()

    def rechazar(self, user):
        self.estado_validacion = self.EstadoValidacion.RECHAZADO
        self.validado_por = user
        self.fecha_validacion = timezone.now()

    def puede_editar(self):
        """
        🔒 regla central de negocio
        """
        return self.estado_validacion in [
            self.EstadoValidacion.PENDIENTE,
            self.EstadoValidacion.RECHAZADO,
        ]

    def esta_bloqueado(self):
        """
        🔒 aprobado o en revisión bloquean edición
        """
        return self.estado_validacion in [
            self.EstadoValidacion.EN_REVISION,
            self.EstadoValidacion.APROBADO,
        ]

    # =========================================================
    # 🧾 META
    # =========================================================
    class Meta:
        db_table = "abm_supervisores"
        ordering = ["usuario"]

        constraints = [
            models.UniqueConstraint(
                fields=["usuario"],
                name="unique_supervisor_por_usuario"
            )
        ]

    # =========================================================
    # 🖨️ REPRESENTACIÓN
    # =========================================================
    def __str__(self):
        return f"{self.usuario.apellido}, {self.usuario.nombres}"
    
    


class RegionalUsuario(models.Model):
    usuario = models.CharField(max_length=11) 

    region_loc = models.CharField(max_length=50)
    
    rol = models.CharField(max_length=50)
    
    categoria = models.CharField(max_length=50)
    
    activo = models.BooleanField(default=True)

    class Meta:
        db_table = "usuarios_regionalusuarios"


class SupervisorRegion(models.Model):
    supervisor = models.ForeignKey(
        Supervisor2,
        on_delete=models.CASCADE,
        db_column="supervisor2_id",
        related_name="supervisor_regiones"
    )

    region_loc = models.CharField(max_length=100)

    class Meta:
        db_table = "amb_supervisores_regiones"