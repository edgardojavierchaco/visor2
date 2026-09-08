# -*- coding: utf-8 -*-
"""Medición temporal posterior al cache de ciclos CEF."""

import json
import logging
from contextlib import ExitStack, contextmanager
from time import perf_counter
from uuid import uuid4

from django.db import connections
from django.shortcuts import render


logger = logging.getLogger(__name__)
PERF_SESSION_KEY = "cef_perf_after_enabled"
GLOBAL_SQL_MARKERS = (
    "consultasge_consulta",
    "auth_group",
    "usuario_visualizador_groups",
    "usuarios_perfilusuario",
    "usuarios_rol",
)


def _metrics(request):
    return getattr(request, "_cef_perf_after", None)


def perf_begin(request):
    command = request.GET.get("cef_perf")
    enabled = bool(request.session.get(PERF_SESSION_KEY, False))

    if command == "1" and not enabled:
        request.session[PERF_SESSION_KEY] = True
        enabled = True
    elif command == "0" and enabled:
        request.session[PERF_SESSION_KEY] = False
        enabled = False

    if not enabled:
        return False

    request._cef_perf_after = {
        "id": uuid4().hex[:12],
        "path": request.path,
        "started": perf_counter(),
        "phase": "view",
        "durations_ms": {},
        "queries": [],
    }
    return True


@contextmanager
def perf_phase(request, name):
    metrics = _metrics(request)
    if metrics is None:
        yield
        return

    previous = metrics["phase"]
    metrics["phase"] = name
    started = perf_counter()
    try:
        yield
    finally:
        metrics["durations_ms"][name] = round(
            (perf_counter() - started) * 1000,
            3,
        )
        metrics["phase"] = previous


def perf_start_view(request):
    metrics = _metrics(request)
    if metrics is not None:
        metrics["view_started"] = perf_counter()


def perf_render(request, template_name, context):
    metrics = _metrics(request)
    if metrics is not None and "view_started" in metrics:
        metrics["durations_ms"]["view"] = round(
            (perf_counter() - metrics["view_started"]) * 1000,
            3,
        )

    with perf_phase(request, "template"):
        return render(request, template_name, context)


class _QueryTimer:
    def __init__(self, request, alias):
        self.request = request
        self.alias = alias

    def __call__(self, execute, sql, params, many, context):
        started = perf_counter()
        try:
            return execute(sql, params, many, context)
        finally:
            metrics = _metrics(self.request)
            if metrics is not None:
                compact_sql = " ".join(str(sql).split())
                sql_lower = compact_sql.lower()
                metrics["queries"].append(
                    {
                        "alias": self.alias,
                        "phase": metrics["phase"],
                        "ms": round((perf_counter() - started) * 1000, 3),
                        "global": any(
                            marker in sql_lower for marker in GLOBAL_SQL_MARKERS
                        ),
                        "sql": compact_sql[:700],
                    }
                )


@contextmanager
def perf_capture_queries(request):
    if _metrics(request) is None:
        yield
        return

    with ExitStack() as stack:
        for connection in connections.all():
            stack.enter_context(
                connection.execute_wrapper(_QueryTimer(request, connection.alias))
            )
        yield


def _sum_queries(queries):
    return {
        "count": len(queries),
        "sql_ms": round(sum(query["ms"] for query in queries), 3),
    }


def perf_finish(request, response=None, error=None):
    metrics = _metrics(request)
    if metrics is None:
        return

    queries = metrics.pop("queries")
    global_queries = [query for query in queries if query["global"]]
    cef_queries = [query for query in queries if not query["global"]]
    by_phase = {}
    for phase in ("context", "view", "template"):
        by_phase[phase] = _sum_queries(
            [query for query in queries if query["phase"] == phase]
        )

    metrics["total_ms"] = round(
        (perf_counter() - metrics.pop("started")) * 1000,
        3,
    )
    metrics["sql"] = {
        "total": _sum_queries(queries),
        "cef": _sum_queries(cef_queries),
        "global_external": _sum_queries(global_queries),
        "by_phase": by_phase,
        "top_5": sorted(queries, key=lambda query: query["ms"], reverse=True)[:5],
    }
    metrics.pop("phase", None)
    metrics.pop("view_started", None)
    if response is not None:
        metrics["status_code"] = response.status_code
    if error is not None:
        metrics["error"] = error.__class__.__name__

    logger.warning(
        "CEF_PERF_AFTER %s",
        json.dumps(metrics, ensure_ascii=False, separators=(",", ":")),
    )
