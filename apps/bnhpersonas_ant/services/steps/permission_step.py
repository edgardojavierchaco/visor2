from django.core.exceptions import PermissionDenied
from apps.bnhpersonas.domain.access import user_has_cueanexo_access
from apps.bnhpersonas.services.pipeline import BaseStep


class PermissionStep(BaseStep):

    name = "PermissionStep"

    @classmethod
    def apply(cls, obj, context):

        if not hasattr(obj, "cueanexo"):
            return obj

        if not user_has_cueanexo_access(context.user, obj.cueanexo):
            raise PermissionDenied("No tiene permisos sobre este CUEANEXO")

        return obj