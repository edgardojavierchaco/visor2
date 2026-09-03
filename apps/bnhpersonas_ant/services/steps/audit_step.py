from apps.bnhpersonas.middleware import get_current_user
from apps.bnhpersonas.services.pipeline import BaseStep


class AuditStep(BaseStep):

    @classmethod
    def apply(cls, obj, context):

        user = context.user or get_current_user()

        if user and user.is_authenticated:

            if not obj.pk:
                obj.usuario_creacion = user

            obj.usuario_modificacion = user

        return obj