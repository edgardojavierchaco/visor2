from datetime import datetime, timedelta
from django.contrib.contenttypes.models import ContentType

from apps.sirtee.models.auditoria import AuditoriaBase
from apps.sirtee.services.diff import DiffService
from apps.sirtee.services.snapshot import SnapshotService


class AuditReporter:
    """
    Generador de reportes de auditoría para SIRTEE.

    Convierte la trazabilidad del sistema en reportes
    legibles, exportables y analizables.
    """

    def __init__(self):
        self.diff_service = DiffService()
        self.snapshot_service = SnapshotService()

    # --------------------------------------
    # REPORTE GENERAL POR OBJETO
    # --------------------------------------

    def report_for_instance(self, instance):
        """
        Genera reporte completo de auditoría de un objeto.
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

        return {
            "entity": str(instance),
            "model": instance.__class__.__name__,
            "total_events": audits.count(),
            "events": [
                self._format_audit(a) for a in audits
            ],
            "current_snapshot": self.snapshot_service.get_current_snapshot(instance),
        }

    # --------------------------------------
    # REPORTE POR RANGO DE FECHAS
    # --------------------------------------

    def report_by_date_range(self, model, start_date, end_date):
        """
        Reporte de actividad en un rango de fechas.
        """

        content_type = ContentType.objects.get_for_model(model)

        audits = (
            AuditoriaBase.objects
            .filter(
                content_type=content_type,
                timestamp__gte=start_date,
                timestamp__lte=end_date
            )
            .order_by("-timestamp")
        )

        return {
            "model": model.__name__,
            "start_date": start_date,
            "end_date": end_date,
            "total_events": audits.count(),
            "events": [self._format_audit(a) for a in audits],
        }

    # --------------------------------------
    # ACTIVIDAD RECIENTE
    # --------------------------------------

    def recent_activity(self, days=7):
        """
        Actividad reciente global del sistema.
        """

        since = datetime.now() - timedelta(days=days)

        audits = (
            AuditoriaBase.objects
            .filter(timestamp__gte=since)
            .order_by("-timestamp")
        )

        return {
            "period_days": days,
            "total_events": audits.count(),
            "events": [self._format_audit(a) for a in audits],
        }

    # --------------------------------------
    # FORMATEO DE AUDITORÍA
    # --------------------------------------

    def _format_audit(self, audit):
        """
        Convierte auditoría en estructura legible.
        """

        snapshot = None

        try:
            snapshot = audit.snapshot.data
        except Exception:
            snapshot = None

        return {
            "id": audit.id,
            "action": audit.accion,
            "user": str(audit.usuario) if audit.usuario else None,
            "object": audit.objeto_str,
            "timestamp": audit.timestamp,
            "ip": audit.ip_address,
            "user_agent": audit.user_agent,
            "snapshot": snapshot,
        }

    # --------------------------------------
    # RESUMEN EJECUTIVO
    # --------------------------------------

    def executive_summary(self, instance):
        """
        Genera resumen ejecutivo tipo dashboard.
        """

        content_type = ContentType.objects.get_for_model(instance.__class__)

        audits = AuditoriaBase.objects.filter(
            content_type=content_type,
            object_id=str(instance.pk)
        )

        actions = audits.values_list("accion", flat=True)

        return {
            "entity": str(instance),
            "total_events": audits.count(),
            "creates": list(actions).count("CREATE"),
            "updates": list(actions).count("UPDATE"),
            "deletes": list(actions).count("DELETE"),
            "last_change": audits.order_by("-timestamp").first().timestamp if audits.exists() else None,
        }