from datetime import date, timedelta

from django.contrib.auth.decorators import login_required
from django.db import connections
from django.http import JsonResponse
from django.shortcuts import render
from django.urls import reverse

from apps.consultasge.models_padron import CapaUnicaOfertas
from .access import get_access_scope


DB_ALIAS = "sge_nacion"
TABLA_ASISTENCIA = "sge.aip_asistencia_explotacion"
TABLA_ALERTA_SEMANAL = "sge.aip_alerta_asistencia_alumno_semana"
TABLA_CALIDAD = "sge.aip_calidad_registro_mes"


def _int_param(request, nombre, default=None):
    valor = request.GET.get(nombre)
    if valor in (None, "", "null", "undefined"):
        return default
    try:
        return int(valor)
    except (TypeError, ValueError):
        return default


def _text_param(request, nombre):
    valor = request.GET.get(nombre)
    if valor in (None, "", "null", "undefined"):
        return None
    return valor.strip()


def _rango_mes(anio, mes):
    desde = date(anio, mes, 1)
    if mes == 12:
        hasta = date(anio + 1, 1, 1)
    else:
        hasta = date(anio, mes + 1, 1)
    return desde, hasta


def _filtros_request(request):
    hoy = date.today()

    iso = hoy.isocalendar()

    return {
        "anio": _int_param(request, "anio", hoy.year),
        "mes": _int_param(request, "mes", hoy.month),
        "anio_semana": _int_param(request, "anio_semana", iso.year),
        "semana": _int_param(request, "semana", iso.week),
        "region": _text_param(request, "region"),
        "departamento": _text_param(request, "departamento"),
        "localidad": _text_param(request, "localidad"),
        "nivel": _text_param(request, "nivel"),
        "oferta": _text_param(request, "oferta"),
        "ambito": _text_param(request, "ambito"),
        "cueanexo": _text_param(request, "cueanexo"),
        "grado": _text_param(request, "grado"),
        "seccion": _text_param(request, "seccion"),
        "turno": _text_param(request, "turno"),
        "alerta": _text_param(request, "alerta"),
    }


def _cueanexos_por_region(region):
    """
    Regional Educativa obtenida desde la base default mediante
    CapaUnicaOfertas.region_loc.
    """
    if not region:
        return []

    valores = (
        CapaUnicaOfertas.objects
        .using("default")
        .filter(region_loc=region)
        .exclude(cueanexo__isnull=True)
        .values_list("cueanexo", flat=True)
        .distinct()
    )

    return [
        str(cue).strip()
        for cue in valores
        if cue is not None and str(cue).strip()
    ]


def _build_where(filtros, request=None):
    """
    WHERE para la tabla analítica de SGE-NACION.

    La Regional no se busca en sge.aip_asistencia_explotacion.
    Se traduce a CUEANEXO usando CapaUnicaOfertas en la base default.
    """
    desde, hasta = _rango_mes(
        filtros["anio"],
        filtros["mes"],
    )

    condiciones = [
        "fecha_asistencia >= %s",
        "fecha_asistencia < %s",
    ]
    params = [desde, hasta]

    if request is not None:
        _apply_scope_to_conditions(request, condiciones, params)

    region = filtros.get("region")

    if region:
        cues = _cueanexos_por_region(region)

        if cues:
            condiciones.append("cueanexo = ANY(%s)")
            params.append(cues)
        else:
            condiciones.append("1 = 0")

    campos = [
        "departamento",
        "localidad",
        "nivel",
        "oferta",
        "ambito",
        "cueanexo",
        "grado",
        "seccion",
        "turno",
    ]

    for campo in campos:
        valor = filtros.get(campo)

        if valor:
            condiciones.append(f"{campo} = %s")
            params.append(valor)

    return " AND ".join(condiciones), params


def _dictfetchall(cursor):
    columnas = [col[0] for col in cursor.description]
    return [dict(zip(columnas, row)) for row in cursor.fetchall()]



def _pagination_request(request):
    """Paginación uniforme de todos los listados: 10 registros por página."""
    page = max(_int_param(request, "page", 1) or 1, 1)
    page_size = 10
    return page, page_size, (page - 1) * page_size


def _pagination_meta(page, page_size, total):
    pages = (total + page_size - 1) // page_size if total else 0
    return {
        "page": page,
        "page_size": page_size,
        "total": total,
        "pages": pages,
        "has_previous": page > 1,
        "has_next": page < pages,
        "previous_page": page - 1 if page > 1 else None,
        "next_page": page + 1 if page < pages else None,
    }


def _scope_condition(request, alias=None):
    scope = get_access_scope(request.user)
    prefix = f"{alias}." if alias else ""
    if scope.full_access:
        return None, [], scope
    if scope.cueanexos:
        return f"{prefix}cueanexo = ANY(%s)", [scope.cueanexos], scope
    return "1 = 0", [], scope


def _apply_scope_to_conditions(request, condiciones, params, alias=None):
    condicion, valores, scope = _scope_condition(request, alias=alias)
    if condicion:
        condiciones.append(condicion)
        params.extend(valores)
    return scope


def _url_volver_por_rol(user):
    """
    Director vuelve a /director/.
    El resto de los perfiles habilitados vuelve a archivos:portada_gestor.
    """
    scope = get_access_scope(user)
    role_name = (scope.role_name or "").strip().upper()

    if role_name == "DIRECTOR":
        return "/director/"

    return reverse("archivos:portada_gestor")

@login_required
def dashboard(request):
    hoy = date.today()
    iso_hoy = hoy.isocalendar()

    anio_actual = hoy.year
    mes_actual = hoy.month
    anio_semana_actual = iso_hoy.year
    semana_actual = iso_hoy.week
    semana_desde = date.fromisocalendar(anio_semana_actual, semana_actual, 1)
    semana_hasta = semana_desde + timedelta(days=6)

    try:
        with connections[DB_ALIAS].cursor() as cursor:
            cursor.execute(
                f"""
                SELECT
                    EXTRACT(YEAR FROM MAX(fecha_asistencia))::integer,
                    EXTRACT(MONTH FROM MAX(fecha_asistencia))::integer
                FROM {TABLA_ASISTENCIA}
                """
            )
            row = cursor.fetchone()
            if row and row[0]:
                anio_actual, mes_actual = row

            cursor.execute(
                f"""
                SELECT anio_iso, semana_iso, fecha_desde, fecha_hasta
                FROM {TABLA_ALERTA_SEMANAL}
                ORDER BY fecha_desde DESC
                LIMIT 1
                """
            )
            row = cursor.fetchone()
            if row:
                anio_semana_actual, semana_actual, semana_desde, semana_hasta = row
    except Exception:
        pass

    return render(
        request,
        "asistencia_dashboard/dashboard.html",
        {
            "anio_actual": anio_actual,
            "mes_actual": mes_actual,
            "anio_semana_actual": anio_semana_actual,
            "semana_actual": semana_actual,
            "semana_desde": semana_desde,
            "semana_hasta": semana_hasta,
            "perfil_acceso": get_access_scope(request.user).role_name,
            "url_volver": _url_volver_por_rol(request.user),
        },
    )


@login_required
def api_filtros(request):
    filtros = _filtros_request(request)

    desde, hasta = _rango_mes(
        filtros["anio"],
        filtros["mes"],
    )

    resultado = {}

    # Regionales desde PADRÓN / base default
    scope = get_access_scope(request.user)
    regiones_qs = (
        CapaUnicaOfertas.objects
        .using("default")
        .exclude(region_loc__isnull=True)
        .exclude(region_loc="")
    )
    if not scope.full_access:
        regiones_qs = regiones_qs.filter(cueanexo__in=scope.cueanexos)
    resultado["region"] = list(
        regiones_qs.values_list("region_loc", flat=True)
        .distinct()
        .order_by("region_loc")
    )

    # Resto desde SGE-NACION
    campos = {
        "departamento": "departamento",
        "localidad": "localidad",
        "nivel": "nivel",
        "oferta": "oferta",
        "ambito": "ambito",
        "grado": "grado",
        "turno": "turno",
    }

    with connections[DB_ALIAS].cursor() as cursor:
        for clave, campo in campos.items():
            condiciones = [
                "fecha_asistencia >= %s",
                "fecha_asistencia < %s",
                f"{campo} IS NOT NULL",
                f"BTRIM({campo}::text) <> ''",
            ]
            params = [desde, hasta]
            _apply_scope_to_conditions(request, condiciones, params)
            cursor.execute(
                f"""
                SELECT DISTINCT {campo}
                FROM {TABLA_ASISTENCIA}
                WHERE {" AND ".join(condiciones)}
                ORDER BY {campo}
                """,
                params,
            )

            resultado[clave] = [
                row[0]
                for row in cursor.fetchall()
            ]

    return JsonResponse(resultado)


@login_required
def api_semanas(request):
    anio = _int_param(request, "anio", date.today().isocalendar().year)

    with connections[DB_ALIAS].cursor() as cursor:
        cursor.execute(
            f"""
            SELECT DISTINCT semana_iso, fecha_desde, fecha_hasta
            FROM {TABLA_ALERTA_SEMANAL}
            WHERE anio_iso = %s
            ORDER BY semana_iso DESC
            """,
            [anio],
        )
        filas = cursor.fetchall()

    return JsonResponse({
        "data": [
            {
                "semana": row[0],
                "fecha_desde": row[1].isoformat(),
                "fecha_hasta": row[2].isoformat(),
                "texto": f"Semana {row[0]} · {row[1].strftime('%d/%m')} al {row[2].strftime('%d/%m/%Y')}",
            }
            for row in filas
        ]
    })


@login_required
def api_resumen(request):
    filtros = _filtros_request(request)
    where, params = _build_where(filtros, request)

    sql = f"""
        SELECT
            COUNT(DISTINCT cueanexo) AS establecimientos,
            COUNT(DISTINCT id_seccion) AS secciones,
            COUNT(DISTINCT fecha_asistencia) AS dias_con_registro,

            COALESCE(SUM(total_alumnos), 0) AS alumno_dias,
            COALESCE(SUM(presentes), 0) AS presentes,
            COALESCE(SUM(ausentes), 0) AS ausentes,
            COALESCE(SUM(ausentes_justificados), 0) AS ausentes_justificados,
            COALESCE(SUM(otras_faltas), 0) AS otras_faltas,

            ROUND(
                100.0 * SUM(COALESCE(presentes, 0))
                / NULLIF(
                    SUM(
                        COALESCE(presentes, 0)
                        + COALESCE(ausentes, 0)
                        + COALESCE(ausentes_justificados, 0)
                    ),
                    0
                ),
                2
            ) AS porcentaje_asistencia,

            ROUND(
                100.0 * SUM(
                    COALESCE(ausentes, 0)
                    + COALESCE(ausentes_justificados, 0)
                )
                / NULLIF(
                    SUM(
                        COALESCE(presentes, 0)
                        + COALESCE(ausentes, 0)
                        + COALESCE(ausentes_justificados, 0)
                    ),
                    0
                ),
                2
            ) AS porcentaje_ausentismo

        FROM {TABLA_ASISTENCIA}
        WHERE {where}
    """

    with connections[DB_ALIAS].cursor() as cursor:
        cursor.execute(sql, params)

        columnas = [
            col[0]
            for col in cursor.description
        ]

        row = cursor.fetchone()

    return JsonResponse(
        dict(
            zip(columnas, row)
        )
    )


@login_required
def api_evolucion(request):
    filtros = _filtros_request(request)
    where, params = _build_where(filtros, request)

    sql = f"""
        SELECT
            fecha_asistencia,
            SUM(total_alumnos) AS total_alumnos,
            SUM(presentes) AS presentes,
            SUM(ausentes) AS ausentes,
            SUM(ausentes_justificados) AS ausentes_justificados,

            ROUND(
                100.0 * SUM(COALESCE(presentes, 0))
                / NULLIF(
                    SUM(
                        COALESCE(presentes, 0)
                        + COALESCE(ausentes, 0)
                        + COALESCE(ausentes_justificados, 0)
                    ),
                    0
                ),
                2
            ) AS porcentaje_asistencia,

            ROUND(
                100.0 * SUM(
                    COALESCE(ausentes, 0)
                    + COALESCE(ausentes_justificados, 0)
                )
                / NULLIF(
                    SUM(
                        COALESCE(presentes, 0)
                        + COALESCE(ausentes, 0)
                        + COALESCE(ausentes_justificados, 0)
                    ),
                    0
                ),
                2
            ) AS porcentaje_ausentismo

        FROM {TABLA_ASISTENCIA}
        WHERE {where}
        GROUP BY fecha_asistencia
        ORDER BY fecha_asistencia
    """

    with connections[DB_ALIAS].cursor() as cursor:
        cursor.execute(sql, params)
        datos = _dictfetchall(cursor)

    for fila in datos:
        if fila["fecha_asistencia"]:
            fila["fecha_asistencia"] = (
                fila["fecha_asistencia"]
                .strftime("%Y-%m-%d")
            )

    return JsonResponse({"data": datos})


@login_required
def api_niveles(request):
    filtros = _filtros_request(request)
    where, params = _build_where(filtros, request)

    sql = f"""
        SELECT
            COALESCE(nivel, 'Sin nivel') AS nivel,
            SUM(total_alumnos) AS alumno_dias,
            SUM(presentes) AS presentes,
            SUM(ausentes) AS ausentes,

            ROUND(
                100.0 * SUM(COALESCE(presentes, 0))
                / NULLIF(
                    SUM(
                        COALESCE(presentes, 0)
                        + COALESCE(ausentes, 0)
                        + COALESCE(ausentes_justificados, 0)
                    ),
                    0
                ),
                2
            ) AS porcentaje_asistencia

        FROM {TABLA_ASISTENCIA}
        WHERE {where}
        GROUP BY nivel
        ORDER BY porcentaje_asistencia DESC NULLS LAST
    """

    with connections[DB_ALIAS].cursor() as cursor:
        cursor.execute(sql, params)
        datos = _dictfetchall(cursor)

    return JsonResponse({"data": datos})


@login_required
def api_ranking(request):
    """Ranking de establecimientos con mayor ausentismo, paginado."""
    filtros = _filtros_request(request)
    where, params = _build_where(filtros, request)
    page, page_size, offset = _pagination_request(request)

    base_sql = f"""
        SELECT
            cueanexo,
            MAX(escuela) AS escuela,
            MAX(departamento) AS departamento,
            MAX(localidad) AS localidad,
            COUNT(DISTINCT fecha_asistencia) AS dias_registrados,
            SUM(total_alumnos) AS alumno_dias,
            SUM(presentes) AS presentes,
            SUM(ausentes) AS ausentes,
            ROUND(
                100.0 * SUM(COALESCE(presentes, 0))
                / NULLIF(
                    SUM(
                        COALESCE(presentes, 0)
                        + COALESCE(ausentes, 0)
                        + COALESCE(ausentes_justificados, 0)
                    ),
                    0
                ),
                2
            ) AS porcentaje_asistencia,
            ROUND(
                100.0 * SUM(
                    COALESCE(ausentes, 0)
                    + COALESCE(ausentes_justificados, 0)
                )
                / NULLIF(
                    SUM(
                        COALESCE(presentes, 0)
                        + COALESCE(ausentes, 0)
                        + COALESCE(ausentes_justificados, 0)
                    ),
                    0
                ),
                2
            ) AS porcentaje_ausentismo
        FROM {TABLA_ASISTENCIA}
        WHERE {where}
        GROUP BY cueanexo
        HAVING SUM(total_alumnos) > 0
    """

    with connections[DB_ALIAS].cursor() as cursor:
        cursor.execute(f"SELECT COUNT(*) FROM ({base_sql}) q", params)
        total = cursor.fetchone()[0]

        cursor.execute(
            base_sql +
            " ORDER BY porcentaje_ausentismo DESC NULLS LAST, escuela LIMIT %s OFFSET %s",
            params + [page_size, offset],
        )
        datos = _dictfetchall(cursor)

    return JsonResponse({
        "data": datos,
        "pagination": _pagination_meta(page, page_size, total),
    })


@login_required
def api_secciones(request):
    filtros = _filtros_request(request)
    if not filtros.get("cueanexo"):
        return JsonResponse({"data": [], "requiere_cue": True, "pagination": _pagination_meta(1, 10, 0)})

    where, params = _build_where(filtros, request)
    page, page_size, offset = _pagination_request(request)
    base_sql = f"""
        SELECT
            cueanexo,
            MAX(escuela) AS escuela,
            nivel,
            grado,
            seccion,
            turno,
            COUNT(DISTINCT fecha_asistencia) AS dias_registrados,
            SUM(total_alumnos) AS alumno_dias,
            SUM(presentes) AS presentes,
            SUM(ausentes) AS ausentes,
            SUM(ausentes_justificados) AS ausentes_justificados,
            SUM(otras_faltas) AS otras_faltas,
            ROUND(
                100.0 * SUM(COALESCE(presentes,0)) /
                NULLIF(SUM(COALESCE(presentes,0)+COALESCE(ausentes,0)+COALESCE(ausentes_justificados,0)),0),
                2
            ) AS porcentaje_asistencia
        FROM {TABLA_ASISTENCIA}
        WHERE {where}
        GROUP BY cueanexo, nivel, grado, seccion, turno
    """
    with connections[DB_ALIAS].cursor() as cursor:
        cursor.execute(f"SELECT COUNT(*) FROM ({base_sql}) q", params)
        total = cursor.fetchone()[0]
        cursor.execute(base_sql + " ORDER BY nivel, grado, seccion, turno LIMIT %s OFFSET %s", params + [page_size, offset])
        datos = _dictfetchall(cursor)
    return JsonResponse({"data": datos, "pagination": _pagination_meta(page, page_size, total)})

@login_required
def api_establecimientos(request):
    q = request.GET.get("q", "").strip()

    anio = _int_param(
        request,
        "anio",
        date.today().year,
    )

    mes = _int_param(
        request,
        "mes",
        date.today().month,
    )

    region = _text_param(
        request,
        "region",
    )

    desde, hasta = _rango_mes(
        anio,
        mes,
    )

    condiciones = [
        "fecha_asistencia >= %s",
        "fecha_asistencia < %s",
    ]

    params = [
        desde,
        hasta,
    ]

    if region:
        cues = _cueanexos_por_region(region)

        if cues:
            condiciones.append("cueanexo = ANY(%s)")
            params.append(cues)
        else:
            condiciones.append("1 = 0")

    if q:
        condiciones.append(
            "(cueanexo ILIKE %s OR escuela ILIKE %s)"
        )

        termino = f"%{q}%"

        params.extend([
            termino,
            termino,
        ])

    sql = f"""
        SELECT
            cueanexo,
            MAX(escuela) AS escuela

        FROM {TABLA_ASISTENCIA}

        WHERE {" AND ".join(condiciones)}

        GROUP BY cueanexo

        ORDER BY escuela

        LIMIT 10
    """

    with connections[DB_ALIAS].cursor() as cursor:
        cursor.execute(sql, params)
        filas = cursor.fetchall()

    return JsonResponse(
        {
            "results": [
                {
                    "id": cue,
                    "text": f"{cue} · {escuela}",
                }
                for cue, escuela in filas
            ]
        }
    )


@login_required
def api_alertas(request):
    """Seguimiento institucional prioritario, paginado."""
    filtros = _filtros_request(request)
    where, params = _build_where(filtros, request)
    page, page_size, offset = _pagination_request(request)

    cte_sql = f"""
        WITH establecimientos AS
        (
            SELECT
                cueanexo,
                MAX(escuela) AS escuela,
                MAX(departamento) AS departamento,
                MAX(localidad) AS localidad,
                COUNT(DISTINCT fecha_asistencia) AS dias_registrados,
                COUNT(DISTINCT id_seccion) AS secciones,
                SUM(presentes) AS presentes,
                SUM(ausentes) AS ausentes,
                SUM(ausentes_justificados) AS ausentes_justificados,
                SUM(
                    COALESCE(presentes, 0)
                    + COALESCE(ausentes, 0)
                    + COALESCE(ausentes_justificados, 0)
                ) AS base_asistencia
            FROM {TABLA_ASISTENCIA}
            WHERE {where}
            GROUP BY cueanexo
        ),
        indicadores AS
        (
            SELECT
                *,
                ROUND(
                    100.0 * presentes / NULLIF(base_asistencia, 0),
                    2
                ) AS porcentaje_asistencia
            FROM establecimientos
        ),
        alertas AS
        (
            SELECT
                *,
                CASE
                    WHEN porcentaje_asistencia IS NULL THEN 'SIN DATOS'
                    WHEN porcentaje_asistencia < 70 THEN 'CRITICO'
                    WHEN porcentaje_asistencia < 80 THEN 'ALTO'
                    WHEN porcentaje_asistencia < 90 THEN 'ATENCION'
                    ELSE 'NORMAL'
                END AS nivel_alerta
            FROM indicadores
        )
    """

    nivel_solicitado = filtros.get("alerta")
    filtro_alerta_sql = ""
    filtro_alerta_params = []
    if nivel_solicitado:
        filtro_alerta_sql = " WHERE nivel_alerta = %s "
        filtro_alerta_params = [nivel_solicitado]

    select_cols = """
        SELECT
            cueanexo,
            escuela,
            departamento,
            localidad,
            dias_registrados,
            secciones,
            presentes,
            ausentes,
            ausentes_justificados,
            porcentaje_asistencia,
            nivel_alerta
        FROM alertas
    """

    with connections[DB_ALIAS].cursor() as cursor:
        # Resumen global por nivel, independiente de la página mostrada.
        cursor.execute(
            cte_sql +
            " SELECT nivel_alerta, COUNT(*) FROM alertas GROUP BY nivel_alerta",
            params,
        )
        resumen = {
            "NORMAL": 0,
            "ATENCION": 0,
            "ALTO": 0,
            "CRITICO": 0,
            "SIN DATOS": 0,
        }
        for nivel, cantidad in cursor.fetchall():
            if nivel in resumen:
                resumen[nivel] = cantidad

        cursor.execute(
            cte_sql +
            " SELECT COUNT(*) FROM alertas " +
            filtro_alerta_sql,
            params + filtro_alerta_params,
        )
        total = cursor.fetchone()[0]

        cursor.execute(
            cte_sql +
            select_cols +
            filtro_alerta_sql +
            " ORDER BY CASE nivel_alerta "
            " WHEN 'CRITICO' THEN 1 "
            " WHEN 'ALTO' THEN 2 "
            " WHEN 'ATENCION' THEN 3 "
            " WHEN 'NORMAL' THEN 4 ELSE 5 END, "
            " porcentaje_asistencia ASC NULLS LAST, escuela "
            " LIMIT %s OFFSET %s",
            params + filtro_alerta_params + [page_size, offset],
        )
        datos = _dictfetchall(cursor)

    return JsonResponse({
        "resumen": resumen,
        "data": datos,
        "pagination": _pagination_meta(page, page_size, total),
    })


@login_required
def api_mensual(request):
    """Consulta mensual no nominal, paginada y restringida por perfil."""
    filtros = _filtros_request(request)
    where, params = _build_where(filtros, request)
    page, page_size, offset = _pagination_request(request)

    if filtros.get("cueanexo"):
        base_sql = f"""
            SELECT
                cueanexo,
                MAX(escuela) AS escuela,
                nivel,
                grado,
                seccion,
                turno,
                COUNT(DISTINCT fecha_asistencia) AS dias_registrados,
                SUM(total_alumnos) AS alumno_dias,
                SUM(presentes) AS presentes,
                SUM(ausentes) AS ausentes,
                SUM(ausentes_justificados) AS ausentes_justificados,
                SUM(otras_faltas) AS otras_faltas,
                ROUND(
                    100.0 * SUM(COALESCE(presentes,0)) /
                    NULLIF(SUM(
                        COALESCE(presentes,0) +
                        COALESCE(ausentes,0) +
                        COALESCE(ausentes_justificados,0)
                    ),0), 2
                ) AS porcentaje_asistencia
            FROM {TABLA_ASISTENCIA}
            WHERE {where}
            GROUP BY cueanexo, nivel, grado, seccion, turno
        """
        order_sql = " ORDER BY nivel, grado, seccion, turno "
        nivel = "seccion"
    else:
        base_sql = f"""
            SELECT
                cueanexo,
                MAX(escuela) AS escuela,
                MAX(departamento) AS departamento,
                MAX(localidad) AS localidad,
                COUNT(DISTINCT fecha_asistencia) AS dias_registrados,
                SUM(total_alumnos) AS alumno_dias,
                SUM(presentes) AS presentes,
                SUM(ausentes) AS ausentes,
                SUM(ausentes_justificados) AS ausentes_justificados,
                SUM(otras_faltas) AS otras_faltas,
                ROUND(
                    100.0 * SUM(COALESCE(presentes,0)) /
                    NULLIF(SUM(
                        COALESCE(presentes,0) +
                        COALESCE(ausentes,0) +
                        COALESCE(ausentes_justificados,0)
                    ),0), 2
                ) AS porcentaje_asistencia
            FROM {TABLA_ASISTENCIA}
            WHERE {where}
            GROUP BY cueanexo
        """
        order_sql = " ORDER BY escuela "
        nivel = "establecimiento"

    with connections[DB_ALIAS].cursor() as cursor:
        cursor.execute(f"SELECT COUNT(*) FROM ({base_sql}) q", params)
        total = cursor.fetchone()[0]
        cursor.execute(base_sql + order_sql + " LIMIT %s OFFSET %s", params + [page_size, offset])
        datos = _dictfetchall(cursor)

    return JsonResponse({
        "data": datos,
        "nivel": nivel,
        "pagination": _pagination_meta(page, page_size, total),
    })


@login_required
def api_calidad_registro(request):
    """Calidad de registración mensual, paginada y restringida por perfil."""
    filtros = _filtros_request(request)
    page, page_size, offset = _pagination_request(request)

    condiciones = ["anio = %s", "mes = %s"]
    params = [filtros["anio"], filtros["mes"]]
    _apply_scope_to_conditions(request, condiciones, params)

    region = filtros.get("region")
    if region:
        cues = _cueanexos_por_region(region)
        if cues:
            condiciones.append("cueanexo = ANY(%s)")
            params.append(cues)
        else:
            condiciones.append("1 = 0")

    for campo in ("departamento", "localidad", "nivel", "cueanexo"):
        valor = filtros.get(campo)
        if valor:
            condiciones.append(f"{campo} = %s")
            params.append(valor)

    where = " AND ".join(condiciones)

    base_sql = f"""
        SELECT
            cueanexo,
            MAX(escuela) AS escuela,
            MAX(departamento) AS departamento,
            MAX(localidad) AS localidad,
            COUNT(DISTINCT id_seccion) AS cantidad_secciones,

            MAX(dias_habiles_calendario) AS dias_habiles_calendario,
            SUM(dias_excepcion) AS jornadas_excepcion,
            SUM(dias_evento_excluyente) AS jornadas_evento_excluyente,
            SUM(dias_esperados) AS jornadas_esperadas,
            SUM(dias_registrados) AS jornadas_registradas,
            SUM(dias_sin_registro) AS jornadas_sin_registro,
            ROUND(
                100.0 * SUM(dias_registrados) /
                NULLIF(SUM(dias_esperados), 0),
                2
            ) AS porcentaje_cumplimiento,
            CASE
                WHEN SUM(dias_esperados) = 0 THEN 'SIN_DIAS_ESPERADOS'
                WHEN SUM(dias_registrados) = 0 THEN 'SIN_CARGA'
                WHEN SUM(dias_sin_registro) > 0 THEN 'PARCIAL'
                ELSE 'COMPLETO'
            END AS estado_registro
        FROM {TABLA_CALIDAD}
        WHERE {where}
        GROUP BY cueanexo
    """

    try:
        with connections[DB_ALIAS].cursor() as cursor:
            cursor.execute(f"SELECT COUNT(*) FROM ({base_sql}) q", params)
            total = cursor.fetchone()[0]

            cursor.execute(
                f"""
                SELECT estado_registro, COUNT(*)
                FROM ({base_sql}) q
                GROUP BY estado_registro
                """,
                params,
            )
            resumen = {
                "COMPLETO": 0,
                "PARCIAL": 0,
                "SIN_CARGA": 0,
                "SIN_DIAS_ESPERADOS": 0,
            }
            for estado, cantidad in cursor.fetchall():
                if estado in resumen:
                    resumen[estado] = cantidad

            cursor.execute(
                base_sql +
                " ORDER BY jornadas_sin_registro DESC, escuela LIMIT %s OFFSET %s",
                params + [page_size, offset],
            )
            datos = _dictfetchall(cursor)

            if total == 0:
                cursor.execute(
                    f"SELECT COUNT(*) FROM {TABLA_CALIDAD} WHERE anio=%s AND mes=%s",
                    [filtros["anio"], filtros["mes"]],
                )
                procesados_mes = cursor.fetchone()[0]
            else:
                procesados_mes = total

    except Exception as exc:
        return JsonResponse({
            "data": [],
            "resumen": {
                "COMPLETO": 0,
                "PARCIAL": 0,
                "SIN_CARGA": 0,
                "SIN_DIAS_ESPERADOS": 0,
            },
            "procesado": False,
            "message": f"No fue posible consultar la calidad de registración: {exc}",
            "pagination": _pagination_meta(page, page_size, 0),
        }, status=500)

    procesado = procesados_mes > 0
    message = None if procesado else (
        f"No hay calidad de registración procesada para {filtros['mes']:02d}/{filtros['anio']}. "
        f"Ejecute CALL sge.refrescar_calidad_registro_mes({filtros['anio']}, {filtros['mes']});"
    )

    return JsonResponse({
        "data": datos,
        "resumen": resumen,
        "procesado": procesado,
        "message": message,
        "pagination": _pagination_meta(page, page_size, total),
    })

@login_required
def api_alertas_alumnos(request):
    filtros = _filtros_request(request)
    page, page_size, offset = _pagination_request(request)
    if not filtros.get("cueanexo"):
        return JsonResponse({
            "data": [],
            "resumen": {"NORMAL": 0, "ATENCION": 0, "ALTO": 0, "CRITICO": 0, "SIN DATOS": 0},
            "requiere_cue": True,
            "pagination": _pagination_meta(page, page_size, 0),
        })

    condiciones = ["anio_iso = %s", "semana_iso = %s", "cueanexo = %s"]
    params = [filtros["anio_semana"], filtros["semana"], filtros["cueanexo"]]
    _apply_scope_to_conditions(request, condiciones, params)

    for campo in ("nivel", "grado", "seccion", "turno"):
        valor = filtros.get(campo)
        if valor:
            condiciones.append(f"{campo} = %s")
            params.append(valor)
    if filtros.get("alerta"):
        condiciones.append("nivel_alerta_final = %s")
        params.append(filtros["alerta"])

    where = " AND ".join(condiciones)
    select_sql = f"""
        SELECT
            cueanexo, escuela, id_alumno, id_persona, nombre_apellido,
            nivel, grado, seccion, turno, fecha_desde, fecha_hasta,
            dias_esperados_semana, dias_registrados, dias_sin_registro_semana,
            porcentaje_cumplimiento_registro,
            unidades_calificables, inasistencias_equivalentes,
            dias_ausencia_completa, fecha_ultima_presencia,
            fecha_ultima_ausencia_completa, ultima_fecha_registrada,
            racha_actual_ausencias, racha_maxima_ausencias,
            porcentaje_asistencia, nivel_porcentaje,
            nivel_continuidad, nivel_alerta_final
        FROM {TABLA_ALERTA_SEMANAL}
        WHERE {where}
    """
    order_sql = """
        ORDER BY
            CASE nivel_alerta_final
                WHEN 'CRITICO' THEN 1 WHEN 'ALTO' THEN 2
                WHEN 'ATENCION' THEN 3 WHEN 'NORMAL' THEN 4 ELSE 5
            END,
            racha_actual_ausencias DESC,
            racha_maxima_ausencias DESC,
            porcentaje_asistencia ASC NULLS LAST,
            nombre_apellido
    """

    with connections[DB_ALIAS].cursor() as cursor:
        cursor.execute(f"SELECT COUNT(*) FROM ({select_sql}) q", params)
        total = cursor.fetchone()[0]
        cursor.execute(
            f"SELECT nivel_alerta_final, COUNT(*) FROM {TABLA_ALERTA_SEMANAL} WHERE {where} GROUP BY nivel_alerta_final",
            params,
        )
        resumen = {"NORMAL": 0, "ATENCION": 0, "ALTO": 0, "CRITICO": 0, "SIN DATOS": 0}
        for nivel, cantidad in cursor.fetchall():
            if nivel in resumen:
                resumen[nivel] = cantidad
        cursor.execute(select_sql + order_sql + " LIMIT %s OFFSET %s", params + [page_size, offset])
        datos = _dictfetchall(cursor)

    for fila in datos:
        for campo_fecha in (
            "fecha_desde", "fecha_hasta", "fecha_ultima_presencia",
            "fecha_ultima_ausencia_completa", "ultima_fecha_registrada",
        ):
            if fila.get(campo_fecha):
                fila[campo_fecha] = fila[campo_fecha].isoformat()

    return JsonResponse({
        "data": datos,
        "resumen": resumen,
        "requiere_cue": False,
        "pagination": _pagination_meta(page, page_size, total),
    })

