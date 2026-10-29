from __future__ import annotations

from datetime import date
from typing import Any

from django.db import connections


DB_ALIAS = "sge_nacion"
ADVISORY_LOCK_ID = 72620260923
TABLA_CONTROL = "sge.aip_control_actualizacion"


def obtener_mes_anterior(anio: int, mes: int) -> tuple[int, int]:
    return (anio - 1, 12) if mes == 1 else (anio, mes - 1)


def _tomar_lock(cursor) -> bool:
    cursor.execute("SELECT pg_try_advisory_lock(%s)", [ADVISORY_LOCK_ID])
    return bool(cursor.fetchone()[0])


def _liberar_lock(cursor) -> None:
    cursor.execute("SELECT pg_advisory_unlock(%s)", [ADVISORY_LOCK_ID])


def _asegurar_tabla_control(cursor) -> None:
    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS {TABLA_CONTROL} (
            id bigserial PRIMARY KEY,
            proceso varchar(100) NOT NULL,
            anio integer,
            mes integer,
            fecha_inicio timestamptz NOT NULL DEFAULT now(),
            fecha_fin timestamptz,
            estado varchar(20) NOT NULL,
            fecha_dato_max date,
            mensaje text
        )
    """)
    cursor.execute(f"CREATE INDEX IF NOT EXISTS idx_aip_control_actualizacion_inicio ON {TABLA_CONTROL} (fecha_inicio DESC)")




def _asegurar_calidad_semanal(cursor) -> None:
    """Instala la capa semanal de calidad y su procedimiento de refresco."""
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sge.aip_calidad_registro_semana AS
        SELECT
            0::integer AS anio_iso,
            0::integer AS semana_iso,
            CURRENT_DATE::date AS semana_desde,
            CURRENT_DATE::date AS semana_hasta,
            c.id_seccion, c.cueanexo, c.escuela, c.departamento, c.localidad, c.nivel,
            0::integer AS dias_habiles_calendario,
            0::integer AS dias_esperados,
            0::integer AS dias_registrados,
            0::integer AS dias_sin_registro,
            ''::text AS estado_registro
        FROM sge.aip_calidad_registro_mes c
        WHERE false
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_aip_calidad_semana_periodo ON sge.aip_calidad_registro_semana (anio_iso, semana_iso)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_aip_calidad_semana_cue ON sge.aip_calidad_registro_semana (cueanexo)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_aip_calidad_semana_seccion ON sge.aip_calidad_registro_semana (id_seccion)")
    cursor.execute("""
        CREATE OR REPLACE PROCEDURE sge.refrescar_calidad_registro_semana_mes(p_anio integer, p_mes integer)
        LANGUAGE plpgsql
        AS $$
        DECLARE
            v_ini date := make_date(p_anio, p_mes, 1);
            v_fin date := (make_date(p_anio, p_mes, 1) + interval '1 month')::date;
            v_sem_ini date;
            v_sem_fin date;
        BEGIN
            v_sem_ini := date_trunc('week', v_ini)::date;
            v_sem_fin := (date_trunc('week', v_fin - 1)::date + 7);

            DELETE FROM sge.aip_calidad_registro_semana
            WHERE semana_desde >= v_sem_ini AND semana_desde < v_sem_fin;

            INSERT INTO sge.aip_calidad_registro_semana (
                anio_iso, semana_iso, semana_desde, semana_hasta,
                id_seccion, cueanexo, escuela, departamento, localidad, nivel,
                dias_habiles_calendario, dias_esperados, dias_registrados,
                dias_sin_registro, estado_registro
            )
            WITH dim AS (
                SELECT DISTINCT ON (id_seccion)
                       id_seccion, cueanexo, escuela, departamento, localidad, nivel
                FROM sge.aip_calidad_registro_mes
                WHERE id_seccion IS NOT NULL
                ORDER BY id_seccion, anio DESC, mes DESC
            ),
            cal AS (
                SELECT cd.id_seccion,
                       date_trunc('week', cd.dia)::date AS semana_desde,
                       COUNT(*) FILTER (WHERE EXTRACT(ISODOW FROM cd.dia) BETWEEN 1 AND 5)::integer AS dias_habiles,
                       COUNT(*) FILTER (WHERE cd.es_esperado)::integer AS dias_esperados
                FROM sge.aip_calendario_seccion_dia cd
                WHERE cd.dia >= v_sem_ini AND cd.dia < v_sem_fin
                GROUP BY cd.id_seccion, date_trunc('week', cd.dia)::date
            ),
            reg AS (
                SELECT a.id_seccion,
                       date_trunc('week', a.fecha_asistencia)::date AS semana_desde,
                       COUNT(DISTINCT a.fecha_asistencia)::integer AS dias_registrados
                FROM sge.aip_asistencia_explotacion a
                WHERE a.fecha_asistencia >= v_sem_ini AND a.fecha_asistencia < v_sem_fin
                  AND EXISTS (
                      SELECT 1
                      FROM sge.aip_calendario_seccion_dia cd
                      WHERE cd.id_seccion = a.id_seccion
                        AND cd.dia = a.fecha_asistencia
                        AND cd.es_esperado
                  )
                GROUP BY a.id_seccion, date_trunc('week', a.fecha_asistencia)::date
            )
            SELECT
                EXTRACT(ISOYEAR FROM cal.semana_desde)::integer,
                EXTRACT(WEEK FROM cal.semana_desde)::integer,
                cal.semana_desde,
                (cal.semana_desde + 6)::date,
                cal.id_seccion, dim.cueanexo, dim.escuela, dim.departamento, dim.localidad, dim.nivel,
                cal.dias_habiles,
                cal.dias_esperados,
                LEAST(COALESCE(reg.dias_registrados, 0), cal.dias_esperados)::integer,
                GREATEST(cal.dias_esperados - COALESCE(reg.dias_registrados, 0), 0)::integer,
                CASE
                    WHEN cal.dias_esperados = 0 THEN 'SIN_DIAS_ESPERADOS'
                    WHEN COALESCE(reg.dias_registrados, 0) = 0 THEN 'SIN_CARGA'
                    WHEN COALESCE(reg.dias_registrados, 0) < cal.dias_esperados THEN 'PARCIAL'
                    ELSE 'COMPLETO'
                END
            FROM cal
            JOIN dim ON dim.id_seccion = cal.id_seccion
            LEFT JOIN reg ON reg.id_seccion = cal.id_seccion AND reg.semana_desde = cal.semana_desde;
        END;
        $$
    """)


def _refrescar_calidad_semanal(cursor, *, anio: int, mes: int) -> None:
    _asegurar_calidad_semanal(cursor)
    cursor.execute("CALL sge.refrescar_calidad_registro_semana_mes(%s,%s)", [anio, mes])


def _fecha_dato_max(cursor):
    cursor.execute("SELECT MAX(fecha_asistencia)::date FROM sge.aip_asistencia_explotacion")
    row = cursor.fetchone()
    return row[0] if row else None


def _registrar_inicio(cursor, *, proceso: str, anio: int, mes: int) -> int:
    _asegurar_tabla_control(cursor)
    cursor.execute(
        f"INSERT INTO {TABLA_CONTROL} (proceso, anio, mes, estado) VALUES (%s,%s,%s,'PROCESANDO') RETURNING id",
        [proceso, anio, mes],
    )
    return int(cursor.fetchone()[0])


def _registrar_fin(cursor, registro_id: int, *, estado: str, mensaje: str | None = None) -> None:
    fecha_max = None
    try:
        fecha_max = _fecha_dato_max(cursor)
    except Exception:
        pass
    cursor.execute(
        f"UPDATE {TABLA_CONTROL} SET fecha_fin=now(), estado=%s, fecha_dato_max=%s, mensaje=%s WHERE id=%s",
        [estado, fecha_max, mensaje, registro_id],
    )


def _refrescar_periodo(cursor, *, anio: int, mes: int, proceso: str) -> dict[str, Any]:
    registro_id = _registrar_inicio(cursor, proceso=proceso, anio=anio, mes=mes)
    try:
        cursor.execute("CALL sge.refrescar_asistencia_integral_mes(%s,%s)", [anio, mes])
        _refrescar_calidad_semanal(cursor, anio=anio, mes=mes)
    except Exception as exc:
        try:
            _registrar_fin(cursor, registro_id, estado="ERROR", mensaje=str(exc)[:4000])
        except Exception:
            pass
        raise
    _registrar_fin(cursor, registro_id, estado="OK")
    return {"anio": anio, "mes": mes, "registro_id": registro_id}


def actualizar_periodo(*, anio: int, mes: int, proceso: str = "ASISTENCIA_SGE_MANUAL") -> dict[str, Any]:
    if not 1 <= mes <= 12:
        raise ValueError("El mes debe estar entre 1 y 12.")
    with connections[DB_ALIAS].cursor() as cursor:
        if not _tomar_lock(cursor):
            return {"estado": "OMITIDO", "motivo": "Ya existe una actualización de asistencia en ejecución.", "periodos": []}
        try:
            periodo = _refrescar_periodo(cursor, anio=anio, mes=mes, proceso=proceso)
            return {"estado": "OK", "periodos": [periodo]}
        finally:
            _liberar_lock(cursor)


def actualizar_asistencia(*, incluir_mes_anterior: bool = False, proceso: str | None = None) -> dict[str, Any]:
    """Refresco integral. Diario: mes actual. Reproceso: mes anterior + actual."""
    hoy = date.today()
    periodos: list[tuple[int, int]] = []
    if incluir_mes_anterior:
        periodos.append(obtener_mes_anterior(hoy.year, hoy.month))
    periodos.append((hoy.year, hoy.month))
    periodos = list(dict.fromkeys(periodos))
    proceso = proceso or ("ASISTENCIA_SGE_SEMANAL" if incluir_mes_anterior else "ASISTENCIA_SGE_DIARIA")

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
                procesados.append(_refrescar_periodo(cursor, anio=anio, mes=mes, proceso=proceso))
            return {"estado": "OK", "periodos": procesados}
        finally:
            _liberar_lock(cursor)
