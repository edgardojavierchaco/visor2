"""Instrumentacion opt-in de rendimiento para el modulo Especial."""

from contextlib import ExitStack, contextmanager
import json
import logging
from time import perf_counter
from uuid import uuid4

from django.conf import settings
from django.db import connections


logger = logging.getLogger(__name__)

PERF_SESSION_KEY = "especial_perf_after_enabled"
_PERF_REQUEST_ATTR = "_especial_perf_after"


def perf_begin(request):
    """Activa la medicion para el request si DEBUG y la sesion lo permiten."""
    if not settings.DEBUG:
        return False

    session = getattr(request, "session", None)
    option = request.GET.get("especial_perf")
    if session is not None:
        if option == "1":
            session[PERF_SESSION_KEY] = True
        elif option == "0":
            session[PERF_SESSION_KEY] = False
        enabled = bool(session.get(PERF_SESSION_KEY, False))
    else:
        enabled = option == "1"

    if not enabled:
        setattr(request, _PERF_REQUEST_ATTR, None)
        return False

    metrics = {
        "id": uuid4().hex[:12],
        "path": request.path,
        "method": request.method,
        "partial": request.headers.get("X-Especial-Partial") == "1",
        "started_at": perf_counter(),
        "durations_ms": {},
        "phase_stack": [],
        "sql": {
            "count": 0,
            "ms": 0.0,
            "by_alias": {},
            "by_phase": {},
        },
        "query_stack": None,
        "finished": False,
    }
    setattr(request, _PERF_REQUEST_ATTR, metrics)
    return True


def _metrics(request):
    metrics = getattr(request, _PERF_REQUEST_ATTR, None)
    if not isinstance(metrics, dict) or metrics.get("finished"):
        return None
    return metrics


def _record_query(request, alias, elapsed_ms):
    metrics = _metrics(request)
    if metrics is None:
        return

    phase = metrics["phase_stack"][-1] if metrics["phase_stack"] else "unattributed"
    sql_metrics = metrics["sql"]
    sql_metrics["count"] += 1
    sql_metrics["ms"] += elapsed_ms

    for grouping in (sql_metrics["by_alias"], sql_metrics["by_phase"]):
        key = alias if grouping is sql_metrics["by_alias"] else phase
        bucket = grouping.setdefault(key, {"count": 0, "ms": 0.0})
        bucket["count"] += 1
        bucket["ms"] += elapsed_ms


def perf_capture_queries(request):
    """Instala wrappers temporales para todos los aliases de Django."""
    metrics = _metrics(request)
    if metrics is None or metrics["query_stack"] is not None:
        return

    stack = ExitStack()
    metrics["query_stack"] = stack

    for connection in connections.all():
        alias = connection.alias

        def query_wrapper(execute, _sql, _params, _many, _context, *, _alias=alias):
            started = perf_counter()
            try:
                return execute(_sql, _params, _many, _context)
            finally:
                _record_query(request, _alias, (perf_counter() - started) * 1000)

        stack.enter_context(connection.execute_wrapper(query_wrapper))


@contextmanager
def perf_phase(request, name):
    """Mide una fase y restaura correctamente la fase padre al anidar."""
    metrics = _metrics(request)
    if metrics is None:
        yield
        return

    started = perf_counter()
    metrics["phase_stack"].append(name)
    try:
        yield
    finally:
        elapsed_ms = (perf_counter() - started) * 1000
        metrics["durations_ms"][name] = metrics["durations_ms"].get(name, 0.0) + elapsed_ms
        metrics["phase_stack"].pop()


def _response_bytes(response):
    if response is None or getattr(response, "streaming", False):
        return None
    try:
        return len(response.content)
    except (AttributeError, TypeError, ValueError):
        return None


def perf_finish(request, response=None, error=None):
    """Cierra la captura y emite un unico registro seguro por request."""
    metrics = _metrics(request)
    if metrics is None:
        return

    metrics["finished"] = True
    query_stack = metrics["query_stack"]
    if query_stack is not None:
        query_stack.close()

    payload = {
        "id": metrics["id"],
        "path": metrics["path"],
        "method": metrics["method"],
        "partial": metrics["partial"],
        "status_code": getattr(response, "status_code", None),
        "total_ms": (perf_counter() - metrics["started_at"]) * 1000,
        "response_bytes": _response_bytes(response),
        "durations_ms": metrics["durations_ms"],
        "sql": metrics["sql"],
        "error_type": type(error).__name__ if error is not None else None,
    }
    logger.warning(
        "ESPECIAL_PERF_AFTER %s",
        json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True),
    )
