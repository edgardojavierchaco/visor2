"""Herramientas de concurrencia para BNH Personas.

Objetivos:
- serializar altas concurrentes por CUIL sin bloquear toda la tabla;
- limitar esperas de locks en PostgreSQL;
- reintentar únicamente errores transitorios conocidos;
- mantener las transacciones cortas y determinísticas.
"""
from __future__ import annotations

import hashlib
import time
from functools import wraps

from django.db import OperationalError, connection


TRANSIENT_PG_CODES = {"40P01", "40001", "55P03"}  # deadlock, serialization, lock timeout


def _pgcode(exc: BaseException) -> str | None:
    cause = getattr(exc, "__cause__", None)
    return getattr(cause, "pgcode", None) or getattr(cause, "sqlstate", None)


def retry_transient_db(max_attempts: int = 3, delays=(0.05, 0.15, 0.30)):
    """Reintenta sólo fallas transitorias de PostgreSQL.

    Debe envolver externamente a ``transaction.atomic`` para que cada intento
    se ejecute en una transacción nueva.
    """

    def decorator(func):
        @wraps(func)
        def wrapped(*args, **kwargs):
            last_exc = None
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except OperationalError as exc:
                    last_exc = exc
                    if _pgcode(exc) not in TRANSIENT_PG_CODES or attempt >= max_attempts - 1:
                        raise
                    time.sleep(delays[min(attempt, len(delays) - 1)])
            raise last_exc  # pragma: no cover

        return wrapped

    return decorator


def configure_transaction(lock_timeout_ms: int = 5000):
    """Aplica un timeout de lock sólo a la transacción actual en PostgreSQL."""
    if connection.vendor != "postgresql":
        return
    with connection.cursor() as cursor:
        cursor.execute("SET LOCAL lock_timeout = %s", [f"{int(lock_timeout_ms)}ms"])


def advisory_xact_lock(namespace: str, value: str):
    """Lock transaccional de 64 bits estable para una clave lógica.

    PostgreSQL libera automáticamente este lock al COMMIT/ROLLBACK.
    En otros motores es un no-op para permitir tests simples.
    """
    if connection.vendor != "postgresql":
        return

    payload = f"{namespace}:{value}".encode("utf-8")
    digest = hashlib.blake2b(payload, digest_size=8).digest()
    key = int.from_bytes(digest, byteorder="big", signed=True)
    with connection.cursor() as cursor:
        cursor.execute("SELECT pg_advisory_xact_lock(%s)", [key])
