from audit.services import log_change
from audit.utils import snapshot


def audit_update(user, instance, before, after, request=None):

    log_change(
        user=user,
        action="UPDATE",
        instance=instance,
        before=before,
        after=after,
        request=request
    )