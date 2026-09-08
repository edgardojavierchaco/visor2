# services/bulk_service.py
from django.db import transaction
from .pipeline import Pipeline, PipelineContext
from .steps.audit_step import AuditStep
from .steps.normalize_step import NormalizeStep
from .steps.permission_step import PermissionStep
from .steps.validation_step import ValidationStep


class BulkService:

    PIPELINE = Pipeline(
        AuditStep,
        NormalizeStep,
        PermissionStep,
        ValidationStep,
        fail_fast=True,
        log_steps=True,
    )

    @staticmethod
    @transaction.atomic
    def safe_bulk_create(model, objects, user=None):

        context = PipelineContext(user=user)

        prepared = BulkService.PIPELINE.run_many(objects, context)

        return model.objects.bulk_create(prepared)