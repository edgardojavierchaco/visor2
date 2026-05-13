# services/bulk_service.py

from django.db import transaction

from apps.bnhpersonas.services.pipeline import (
    Pipeline,
    PipelineContext,
)

from .steps.audit_step import AuditStep
from .steps.normalize_step import NormalizeStep
from .steps.validation_step import ValidationStep


class BulkService:

    PIPELINE = Pipeline(
        AuditStep,
        NormalizeStep,
        ValidationStep,
        fail_fast=True,
        log_steps=True,
    )

    @staticmethod
    @transaction.atomic
    def safe_bulk_create(
        model_class,
        objects,
        user=None,
        batch_size=1000,
        source="bulk_create",
    ):

        context = PipelineContext(
            user=user,
            source=source,
        )

        prepared = BulkService.PIPELINE.run_many(
            objects,
            context=context,
        )

        created = model_class.objects.bulk_create(
            prepared,
            batch_size=batch_size,
        )

        return {
            "created": created,
            "stats": context.stats,
            "errors": context.errors,
        }