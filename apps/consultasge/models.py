from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError
from apps.usuarios.models import UsuariosVisualizador
from .models_padron import CapaUnicaOfertas

SLA_HORAS_DEFAULT = 48

TURNOS = {
    "manana": {"inicio": 7, "fin": 13},
    "tarde": {"inicio": 13, "fin": 18},
}

class Categoria(models.Model):
    nombre = models.CharField(max_length=200)
    sla_horas = models.IntegerField(default=48)

    def __str__(self):
        return self.nombre


class Consulta(models.Model):

    class Estado(models.TextChoices):
        PENDIENTE = "pendiente", "Pendiente"
        EN_PROCESO = "en_proceso", "En proceso"
        RESPONDIDA = "respondida", "Respondida"
        CERRADA = "cerrada", "Cerrada"

    usuario = models.ForeignKey(
        "usuarios.UsuariosVisualizador",
        on_delete=models.CASCADE
    )

    cueanexo = models.CharField(max_length=9)
    escuela = models.CharField(max_length=255)
    region = models.CharField(max_length=20)

    asunto = models.CharField(max_length=255)
    mensaje = models.TextField()

    categoria = models.ForeignKey(
        "consultasge.Categoria",
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    estado = models.CharField(
        max_length=20,
        choices=Estado.choices,
        default=Estado.PENDIENTE
    )

    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_limite = models.DateTimeField(null=True, blank=True)
    fecha_respuesta = models.DateTimeField(null=True, blank=True)
    fecha_cierre = models.DateTimeField(null=True, blank=True)

    # -------------------------
    # TRANSICIONES
    # -------------------------

    def pasar_a_en_proceso(self):
        if self.estado != self.Estado.PENDIENTE:
            raise ValidationError("Solo una consulta pendiente puede pasar a en proceso.")
        self.estado = self.Estado.EN_PROCESO
        self.save(update_fields=["estado"])

    def pasar_a_respondida(self):
        if self.estado != self.Estado.EN_PROCESO:
            raise ValidationError("Solo una consulta en proceso puede responderse.")
        self.estado = self.Estado.RESPONDIDA
        self.fecha_respuesta = timezone.now()
        self.save(update_fields=["estado", "fecha_respuesta"])

    def cerrar(self):
        if self.estado != self.Estado.RESPONDIDA:
            raise ValidationError("Solo una consulta respondida puede cerrarse.")
        self.estado = self.Estado.CERRADA
        self.fecha_cierre = timezone.now()
        self.save(update_fields=["estado", "fecha_cierre"])

    # -------------------------
    # SLA
    # -------------------------

    @property
    def vencida(self):
        if not self.fecha_limite:
            return False
        if self.estado in [self.Estado.RESPONDIDA, self.Estado.CERRADA]:
            return False
        return timezone.now() > self.fecha_limite

    class Meta:
        indexes = [
            models.Index(fields=["region", "estado"]),
            models.Index(fields=["fecha_limite"]),
        ]

class Respuesta(models.Model):

    consulta = models.ForeignKey(
        Consulta,
        related_name="respuestas",
        on_delete=models.CASCADE
    )

    usuario = models.ForeignKey(
        UsuariosVisualizador,
        on_delete=models.CASCADE
    )

    mensaje = models.TextField()
    fecha = models.DateTimeField(auto_now_add=True)


class Adjunto(models.Model):

    consulta = models.ForeignKey(
        Consulta,
        related_name="adjuntos",
        on_delete=models.CASCADE
    )

    archivo = models.FileField(upload_to="consultas/")


class Auditoria(models.Model):

    usuario = models.ForeignKey(
        UsuariosVisualizador,
        on_delete=models.SET_NULL,
        null=True
    )

    accion = models.CharField(max_length=255)

    consulta_id = models.IntegerField(null=True)

    fecha = models.DateTimeField(auto_now_add=True)