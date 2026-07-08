# services/pipeline.py
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import time
import logging
import traceback

logger = logging.getLogger(__name__)


class PipelineError(Exception):
    pass


@dataclass
class PipelineContext:
    user: Any = None
    source: str = None
    errors: List = field(default_factory=list)
    stats: Dict = field(default_factory=dict)


class BaseStep:
    name = "BaseStep"

    @classmethod
    def apply(cls, obj, context):
        return obj


class Pipeline:

    def __init__(self, *steps, fail_fast=True, log_steps=True):
        self.steps = steps
        self.fail_fast = fail_fast
        self.log_steps = log_steps

    def run(self, obj, context=None):

        context = context or PipelineContext()
        current = obj

        for step in self.steps:

            start = time.perf_counter()

            try:
                step.before(current, context)
                current = step.apply(current, context)
                step.after(current, context)

                if current is None:
                    raise ValueError("Step retornó None")

            except Exception as e:

                tb = traceback.format_exc()

                context.errors.append({
                    "step": step.__name__,
                    "error": str(e),
                    "trace": tb
                })

                logger.exception(f"ERROR {step.__name__}")

                if self.fail_fast:
                    raise PipelineError(str(e))

            finally:
                elapsed = time.perf_counter() - start
                context.stats[step.__name__] = elapsed

        return current

    def run_many(self, objects, context=None):

        context = context or PipelineContext()
        results = []

        for obj in objects:
            results.append(self.run(obj, context))

        return results