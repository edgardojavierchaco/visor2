# services/pipeline.py
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import logging
import traceback
import time


logger = logging.getLogger(__name__)


# =========================================================
# PIPELINE EXCEPTIONS
# =========================================================
class PipelineError(Exception):

    def __init__(
        self,
        step,
        original_exception,
        context=None,
    ):

        self.step = step
        self.original_exception = original_exception
        self.context = context or {}

        super().__init__(
            f"[{step}] {str(original_exception)}"
        )


# =========================================================
# PIPELINE CONTEXT
# =========================================================
@dataclass
class PipelineContext:

    user: Optional[Any] = None

    request: Optional[Any] = None

    source: Optional[str] = None

    metadata: Dict[str, Any] = field(default_factory=dict)

    errors: List[Dict[str, Any]] = field(default_factory=list)

    stats: Dict[str, Any] = field(default_factory=dict)


# =========================================================
# BASE STEP
# =========================================================
class BaseStep:

    name = "BaseStep"

    stop_on_error = True

    @classmethod
    def apply(cls, obj, context: PipelineContext):
        return obj

    @classmethod
    def before(cls, obj, context):
        pass

    @classmethod
    def after(cls, obj, context):
        pass

    @classmethod
    def on_error(cls, obj, error, context):
        pass


# =========================================================
# PIPELINE
# =========================================================
class Pipeline:

    def __init__(
        self,
        *steps,
        fail_fast=True,
        log_steps=True,
    ):

        self.steps = steps

        self.fail_fast = fail_fast

        self.log_steps = log_steps

    # =====================================================
    # RUN SINGLE OBJECT
    # =====================================================
    def run(
        self,
        obj,
        context: Optional[PipelineContext] = None,
    ):

        context = context or PipelineContext()

        current = obj

        for step in self.steps:

            started = time.perf_counter()

            try:

                if self.log_steps:

                    logger.info(
                        f"[PIPELINE] START {step.__name__}"
                    )

                step.before(current, context)

                current = step.apply(current, context)

                if current is None:

                    raise ValueError(
                        f"{step.__name__} retornó None"
                    )

                step.after(current, context)

                elapsed = round(
                    time.perf_counter() - started,
                    4
                )

                context.stats[step.__name__] = {
                    "status": "success",
                    "time": elapsed,
                }

                if self.log_steps:

                    logger.info(
                        f"[PIPELINE] OK {step.__name__} ({elapsed}s)"
                    )

            except Exception as e:

                tb = traceback.format_exc()

                error_data = {
                    "step": step.__name__,
                    "error": str(e),
                    "traceback": tb,
                }

                context.errors.append(error_data)

                context.stats[step.__name__] = {
                    "status": "error",
                    "error": str(e),
                }

                logger.exception(
                    f"[PIPELINE] ERROR {step.__name__}"
                )

                step.on_error(current, e, context)

                if self.fail_fast or step.stop_on_error:

                    raise PipelineError(
                        step=step.__name__,
                        original_exception=e,
                        context=error_data,
                    ) from e

        return current

    # =====================================================
    # RUN MANY
    # =====================================================
    def run_many(
        self,
        objects,
        context: Optional[PipelineContext] = None,
    ):

        context = context or PipelineContext()

        processed = []

        for index, obj in enumerate(objects):

            try:

                result = self.run(obj, context)

                processed.append(result)

            except Exception as e:

                logger.exception(
                    f"[PIPELINE] OBJECT ERROR index={index}"
                )

                context.errors.append({
                    "index": index,
                    "error": str(e),
                })

                if self.fail_fast:
                    raise

        return processed