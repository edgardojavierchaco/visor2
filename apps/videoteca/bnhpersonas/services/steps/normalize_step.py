from apps.bnhpersonas.services.pipeline import BaseStep


class NormalizeStep(BaseStep):

    @classmethod
    def apply(cls, obj, context):

        if hasattr(obj, "normalize"):
            obj.normalize()

        return obj