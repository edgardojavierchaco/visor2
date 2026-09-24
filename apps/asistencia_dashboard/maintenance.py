from __future__ import annotations

from datetime import date
from typing import Any

from django.db import connections


DB_ALIAS = "sge_nacion"

# Clave fija para pg_advisory_lock.
# Sólo importa que sea estable y exclusiva para este proceso.
ADVISORY_LOCK_ID = 72620260923


def obtener_mes_anterior(anio: int, mes: int) -> tuple[int, int]:
    if mes == 1:
        return anio - 1, 12

    return anio, mes - 1


def _tomar_lock(cursor) -> bool:
    cursor.execute(
        "SELECT pg_try_advisory_lock(%s)",
        [ADVISORY_LOCK_ID],
    )
    return bool(cursor.fetchone()[0])


def _liberar_lock(cursor) -> None:
    cursor.execute(
        "SELECT pg_advisory_unlock(%s)",
        [ADVISORY_LOCK_ID],
    )


def actualizar_asistencia(
    *,
    incluir_mes_anterior: bool = True,
) -> dict[str, Any]:
    """
    Actualiza todas las capas analíticas de asistencia.

    Por defecto reprocesa:
      1. mes anterior
      2. mes actual

    Cada período ejecuta:
        sge.refrescar_asistencia_integral_mes(anio, mes)

    El procedimiento integral actualiza:
      - sge.aip_asistencia_explotacion
      - sge.aip_asistencia_alumno
      - sge.aip_matricula_seccion_mes
      - sge.aip_calidad_registro_mes
      - sge.aip_alerta_asistencia_alumno_semana

    Finalmente ejecuta ANALYZE.

    Se usa PostgreSQL advisory lock para impedir dos ejecuciones
    simultáneas, incluso si una proviene de Celery y otra de manage.py.
    """
    hoy = date.today()

    periodos: list[tuple[int, int]] = []

    if incluir_mes_anterior:
        periodos.append(
            obtener_mes_anterior(
                hoy.year,
                hoy.month,
            )
        )

    periodos.append(
        (
            hoy.year,
            hoy.month,
        )
    )

    # Quitar duplicados conservando orden.
    periodos = list(dict.fromkeys(periodos))

    with connections[DB_ALIAS].cursor() as cursor:
        if not _tomar_lock(cursor):
            return {
                "estado": "OMITIDO",
                "motivo": (
                    "Ya existe una actualización de asistencia en ejecución."
                ),
                "periodos": [],
            }

        try:
            procesados = []

            for anio, mes in periodos:
                cursor.execute(
                    """
                    CALL sge.refrescar_asistencia_integral_mes(
                        %s,
                        %s
                    )
                    """,
                    [
                        anio,
                        mes,
                    ],
                )

                procesados.append(
                    {
                        "anio": anio,
                        "mes": mes,
                    }
                )

            cursor.execute(
                """
                ANALYZE sge.aip_asistencia_explotacion;
                ANALYZE sge.aip_asistencia_alumno;
                ANALYZE sge.aip_matricula_seccion_mes;
                ANALYZE sge.aip_calidad_registro_mes;
                ANALYZE sge.aip_alerta_asistencia_alumno_semana;
                """
            )

            return {
                "estado": "OK",
                "periodos": procesados,
            }

        finally:
            _liberar_lock(cursor)
