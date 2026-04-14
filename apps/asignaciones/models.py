from django.utils import timezone

from django.db import models
from django.core.exceptions import ValidationError


class EscuelaCapaOfertas(models.Model):
    id = models.IntegerField(primary_key=True)
    cueanexo = models.CharField(max_length=9)
    nom_est = models.CharField(max_length=255)
    region_loc = models.CharField(max_length=100)
    oferta = models.CharField(max_length=150)
    localidad = models.CharField(max_length=255)
    departamento = models.CharField(max_length=255)
    sector = models.CharField(max_length=150)
    ambito = models.CharField(max_length=150)
    lat = models.FloatField()
    long = models.FloatField()

    class Meta:
        managed = False
        db_table = 'v_capa_unica_ofertas_ant'
    
    def __str__(self):
        return f"{self.cueanexo} - {self.nom_est} ({self.oferta})"


class AsignacionSupervisorEscuela(models.Model):

    # =========================
    # ESTADOS MINISTERIALES
    # =========================
    BORRADOR = "BORRADOR"
    ENVIADO = "ENVIADO"
    REVISION = "REVISION_REGIONAL"
    OBSERVADO = "OBSERVADO"
    APROBADO = "APROBADO"

    ESTADOS = [
        (BORRADOR, "Borrador"),
        (ENVIADO, "Enviado"),
        (REVISION, "En revisión regional"),
        (OBSERVADO, "Observado"),
        (APROBADO, "Aprobado"),
    ]

    supervisor = models.ForeignKey(
        "supervisa2.Supervisor2",
        on_delete=models.CASCADE
    )
    cueanexo = models.CharField(max_length=9)
    nom_est = models.CharField(max_length=255)
    region_loc = models.CharField(max_length=100)
    oferta = models.CharField(max_length=150, null=True, blank=True)
    localidad = models.CharField(max_length=255)

    fecha_desde = models.DateField(null=True, blank=True)
    fecha_hasta = models.DateField(null=True, blank=True)

    estado = models.CharField(
        max_length=20,
        choices=ESTADOS,
        default=BORRADOR
    )
    observacion = models.TextField(blank=True, null=True)
    activo = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "asignacion_supervisores"
        constraints = [
            models.UniqueConstraint(
                fields=["supervisor", "cueanexo", "oferta"],
                name="uq_supervisor_escuela_oferta"
            )
        ]

    def delete(self, using=None, keep_parents=False):
        self.deleted_at = timezone.now()
        self.save()

    def clean(self):
        if self.estado == self.APROBADO and self.deleted_at:
            raise ValidationError("No se puede modificar aprobado")
        
    def __str__(self):
        return f"{self.cueanexo} - {self.estado}"


class AuditLog(models.Model):
    usuario = models.CharField(max_length=150)
    accion = models.CharField(max_length=255)
    objeto = models.CharField(max_length=255)
    timestamp = models.DateTimeField(auto_now_add=True)
    ip = models.GenericIPAddressField(null=True, blank=True)

    def __str__(self):
        return f"{self.usuario} - {self.accion}"