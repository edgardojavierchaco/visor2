from apps.bnhpersonas.services.pipeline import BaseStep


class ValidationStep(BaseStep):

    name = "ValidationStep"

    @classmethod
    def apply(cls, obj, context):

        obj.full_clean()

        return obj