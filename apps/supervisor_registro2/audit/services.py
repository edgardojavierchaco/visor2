import json
from datetime import date, datetime
from django.core.serializers.json import DjangoJSONEncoder
from .models import AuditLog

def safe_json(obj):
    return json.loads(
        json.dumps(obj, cls=DjangoJSONEncoder)
    )
    
def log_change(
    *,
    user,
    action,
    instance,
    before=None,
    after=None,
    request=None,
    extra=None
):

    ip = None

    if request:
        ip = request.META.get("REMOTE_ADDR")

    AuditLog.objects.create(
        user=user if user and user.is_authenticated else None,
        action=action,
        model_name=instance.__class__.__name__,
        object_id=str(instance.pk),
        before=safe_json(before),
        after=safe_json(after),
        ip_address=ip,
        extra=safe_json(extra),
    )