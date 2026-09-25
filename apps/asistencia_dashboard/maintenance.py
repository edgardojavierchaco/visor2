from __future__ import annotations

from datetime import date
from typing import Any

from django.db import connections


DB_ALIAS = "sge_nacion"
ADVISORY_LOCK_ID = 72620260923


def obtener_mes_anterior(anio: int, mes: int) -> tuple[int, int]:
    return (anio - 1, 12) if mes == 1 else (anio, mes - 1)


def _tomar_lock(cursor) -> bool:
    cursor.execute("SELECT pg_try_advisory_lock(%s)", [ADVISORY_LOCK_ID])
    return bool(cursor.fetchone()[0])


def _liberar_lock(cursor) -> None:
    cursor.execute("SELECT pg_advisory_unlock(%s)", [ADVISORY_LOCK_ID])


def actualizar_asistencia(*, incluir_mes_anterior: bool = False) -> dict[str, Any]:
    """Refresco integral. Diario: mes actual. Reproceso: mes anterior + actual."""
    hoy = date.today()
    periodos: list[tuple[int, int]] = []
    if incluir_mes_anterior:
        periodos.append(obtener_mes_anterior(hoy.year, hoy.month))
    periodos.append((hoy.year, hoy.month))
    periodos = list(dict.fromkeys(periodos))

    with connections[DB_ALIAS].cursor() as cursor:
        if not _tomar_lock(cursor):
            return {
                "estado": "OMITIDO",
                "motivo": "Ya existe una actualización de asistencia en ejecución.",
                "periodos": [],
            }
        try:
            procesados = []
            for anio, mes in periodos:
                cursor.execute("CALL sge.refrescar_asistencia_integral_mes(%s,%s)", [anio, mes])
                procesados.append({"anio": anio, "mes": mes})
            return {"estado": "OK", "periodos": procesados}
        finally:
            _liberar_lock(cursor)
