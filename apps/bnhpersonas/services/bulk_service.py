from apps.bnhpersonas.middleware import get_current_user
from .pipeline import Pipeline
from .steps.audit_step import AuditStep
from .steps.normalize_step import NormalizeStep


class BulkService:

    PIPELINE = Pipeline([
        AuditStep,
        NormalizeStep,
    ])

    @staticmethod
    def safe_bulk_create(model_class, objects):

        user = get_current_user()

        prepared = []

        for obj in objects:
            obj = BulkService.PIPELINE.run(obj, user)
            prepared.append(obj)

        return model_class.objects.bulk_create(prepared)