from django.contrib.contenttypes.models import ContentType
from django.utils import timezone

from apps.sirtee.models.auditoria import AuditoriaBase, SnapshotObjeto


class SnapshotService:
    """
    Servicio de reconstrucción de estado histórico.

    Permite:
    - Obtener snapshot actual o histórico
    - Reconstruir estado de un objeto desde auditoría
    - Navegar versiones en el tiempo
    """

    # --------------------------------------
    # OBTENER SNAPSHOT ACTUAL
    # --------------------------------------

    def get_current_snapshot(self, instance):
        """
        Devuelve el snapshot más reciente del objeto.
        """

        content_type = ContentType.objects.get_for_model(instance.__class__)

        audit = (
            AuditoriaBase.objects
            .filter(
                content_type=content_type,
                object_id=str(instance.pk)
            )
            .order_by("-timestamp")
            .first()
        )

        if not audit:
            return None

        return self._extract_snapshot(audit)

    # --------------------------------------
    # SNAPSHOT POR ID DE AUDITORÍA
    # --------------------------------------

    def get_snapshot_by_audit(self, audit_id):
        """
        Devuelve snapshot exacto desde AuditoriaBase.
        """

        try:
            audit = AuditoriaBase.objects.get(id=audit_id)
            return self._extract_snapshot(audit)
        except AuditoriaBase.DoesNotExist:
            return None

    # --------------------------------------
    # SNAPSHOT EN TIEMPO (HISTÓRICO)
    # --------------------------------------

    def get_snapshot_at_time(self, instance, at_time):
        """
        Devuelve el estado del objeto en un momento específico.
        """

        content_type = ContentType.objects.get_for_model(instance.__class__)

        audit = (
            AuditoriaBase.objects
            .filter(
                content_type=content_type,
                object_id=str(instance.pk),
                timestamp__lte=at_time
            )
            .order_by("-timestamp")
            .first()
        )

        if not audit:
            return None

        return self._extract_snapshot(audit)

    # --------------------------------------
    # RECONSTRUCCIÓN COMPLETA
    # --------------------------------------

    def reconstruct(self, instance):
        """
        Reconstruye el estado actual desde snapshot.
        (útil para debugging o validación)
        """

        snapshot = self.get_current_snapshot(instance)

        if not snapshot:
            return None

        return snapshot

    # --------------------------------------
    # EXTRACCIÓN SEGURA
    # --------------------------------------

    def _extract_snapshot(self, audit):
        """
        Extrae snapshot desde relación AuditoriaBase → SnapshotObjeto.
        """

        try:
            return audit.snapshot.data
        except SnapshotObjeto.DoesNotExist:
            return None

    # --------------------------------------
    # LISTADO DE VERSIONES
    # --------------------------------------

    def list_versions(self, instance):
        """
        Devuelve historial completo de snapshots.
        """

        content_type = ContentType.objects.get_for_model(instance.__class__)

        audits = (
            AuditoriaBase.objects
            .filter(
                content_type=content_type,
                object_id=str(instance.pk)
            )
            .order_by("-timestamp")
        )

        return [
            {
                "audit_id": a.id,
                "accion": a.accion,
                "timestamp": a.timestamp,
                "snapshot": self._extract_snapshot(a),
            }
            for a in audits
        ]