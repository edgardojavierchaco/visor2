from django.db import models
from django.conf import settings


class AuditLog(models.Model):

    ACTION_CHOICES = (
        ("CREATE", "CREATE"),
        ("UPDATE", "UPDATE"),
        ("DELETE", "DELETE"),
        ("TOGGLE", "TOGGLE"),
        ("VIEW", "VIEW"),
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    action = models.CharField(max_length=20, choices=ACTION_CHOICES)

    model_name = models.CharField(max_length=100)

    object_id = models.CharField(max_length=50)

    timestamp = models.DateTimeField(auto_now_add=True)

    ip_address = models.GenericIPAddressField(null=True, blank=True)

    before = models.JSONField(null=True, blank=True)

    after = models.JSONField(null=True, blank=True)

    extra = models.JSONField(null=True, blank=True)

    class Meta:
        db_table = "audit_log"
        indexes = [
            models.Index(fields=["model_name", "object_id"]),
            models.Index(fields=["user", "timestamp"]),
        ]