from django.core.exceptions import ValidationError
from apps.bnhpersonas.services.pipeline import BaseStep


class ValidationStep(BaseStep):

    @classmethod
    def apply(cls, obj, context):

        if hasattr(obj, "full_clean"):
            obj.full_clean()

        return obj