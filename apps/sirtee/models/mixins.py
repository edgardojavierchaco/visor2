from django.db import models
from django.contrib.contenttypes.fields import GenericRelation
from apps.sirtee.models.auditoria import AuditoriaBase

class AuditoriaMixin(models.Model):
    """
    Mixin base para agregar auditoría automática a cualquier modelo.
    Agrega trazabilidad completa mediante AuditoriaBase.
    """

    # Relación inversa para consultar auditorías del objeto
    auditorias = GenericRelation(
        AuditoriaBase,
        related_query_name="%(class)s_auditorias"
    )

    class Meta:
        abstract = True

    def get_auditoria_label(self):
        """
        Representación estándar del objeto para auditoría.
        Puede ser sobrescrita en cada modelo.
        """
        return str(self)


class TimestampMixin(models.Model):
    """
    Mixin opcional para control de creación y actualización.
    Útil para correlacionar con auditoría.
    """

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class SoftDeleteMixin(models.Model):
    """
    Soft delete básico compatible con auditoría.
    """

    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        abstract = True

    def delete(self, using=None, keep_parents=False):
        """
        Sobrescribe delete físico → soft delete.
        """
        from django.utils import timezone

        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.save(update_fields=["is_deleted", "deleted_at"])