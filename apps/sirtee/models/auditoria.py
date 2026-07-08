from django.db import models
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth import get_user_model


User = get_user_model()


class AuditoriaBase(models.Model):
    """
    Modelo base para auditoría de cualquier entidad del sistema.
    Guarda información común de rastreo.
    """

    # Usuario que ejecuta la acción
    usuario = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="auditorias_realizadas"
    )

    # Tipo de evento: CREATE / UPDATE / DELETE / LOGIN / etc.
    accion = models.CharField(max_length=50)

    # Modelo afectado (Django ContentType)
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )

    # ID del objeto afectado
    object_id = models.CharField(max_length=255, db_index=True)

    # Representación legible del objeto
    objeto_str = models.TextField(blank=True, null=True)

    # IP del usuario
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    # User agent (navegador/dispositivo)
    user_agent = models.TextField(null=True, blank=True)

    # Fecha del evento
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = "Auditoría"
        verbose_name_plural = "Auditorías"
        ordering = ["-timestamp"]

    def __str__(self):
        return f"{self.accion} - {self.objeto_str or self.object_id}"


class CambioDetalle(models.Model):
    """
    Guarda el detalle de cambios campo por campo.
    """

    auditoria = models.ForeignKey(
        AuditoriaBase,
        on_delete=models.CASCADE,
        related_name="cambios"
    )

    campo = models.CharField(max_length=100)

    valor_anterior = models.TextField(null=True, blank=True)
    valor_nuevo = models.TextField(null=True, blank=True)

    class Meta:
        verbose_name = "Cambio"
        verbose_name_plural = "Cambios"

    def __str__(self):
        return f"{self.campo}: {self.valor_anterior} → {self.valor_nuevo}"


class SnapshotObjeto(models.Model):
    """
    Guarda una foto completa del objeto en JSON.
    Útil para reconstrucción histórica.
    """

    auditoria = models.OneToOneField(
        AuditoriaBase,
        on_delete=models.CASCADE,
        related_name="snapshot"
    )

    data = models.JSONField()

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Snapshot"
        verbose_name_plural = "Snapshots"

    def __str__(self):
        return f"Snapshot {self.auditoria_id}"