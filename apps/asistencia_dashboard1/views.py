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
TABLA_NOMINAL = "sge.aip_asistencia_alumno"
TABLA_ALERTA_SEMANAL = "sge.aip_alerta_asistencia_alumno_semana"
TABLA_CALIDAD = "sge.aip_calidad_registro_mes"
TABLA_CALENDARIO_DIA = "sge.aip_calendario_seccion_dia"
TABLA_MATRICULA = "sge.aip_matricula_seccion_mes"


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
    hasta = date(anio + 1, 1, 1) if mes == 12 else date(anio, mes + 1, 1)
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


def _dictfetchall(cursor):
    columnas = [col[0] for col in cursor.description]
    return [dict(zip(columnas, row)) for row in cursor.fetchall()]


def _pagination_request(request):
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


def _relation_exists(nombre):
    try:
        with connections[DB_ALIAS].cursor() as cursor:
            cursor.execute("SELECT to_regclass(%s)", [nombre])
            return cursor.fetchone()[0] is not None
    except Exception:
        return False


def _cueanexos_por_region(region):
    if not region:
        return []
    valores = (
        CapaUnicaOfertas.objects.using("default")
        .filter(region_loc=region)
        .exclude(cueanexo__isnull=True)
        .values_list("cueanexo", flat=True)
        .distinct()
    )
    return [str(c).strip() for c in valores if c is not None and str(c).strip()]


def _cueanexos_territorio(filtros):
    campos = ("region", "departamento", "localidad", "oferta")
    if not any(filtros.get(c) for c in campos):
        return None

    qs = CapaUnicaOfertas.objects.using("default").all()
    if filtros.get("region"):
        qs = qs.filter(region_loc=filtros["region"])
    if filtros.get("departamento"):
        qs = qs.filter(departamento=filtros["departamento"])
    if filtros.get("localidad"):
        qs = qs.filter(localidad=filtros["localidad"])
    if filtros.get("oferta"):
        qs = qs.filter(oferta=filtros["oferta"])

    valores = qs.exclude(cueanexo__isnull=True).values_list("cueanexo", flat=True).distinct()
    return [str(c).strip() for c in valores if c is not None and str(c).strip()]


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


def _build_where(filtros, request=None, alias=None, calendario=False):
    prefix = f"{alias}." if alias else ""
    desde, hasta = _rango_mes(filtros["anio"], filtros["mes"])
    condiciones = [f"{prefix}fecha_asistencia >= %s", f"{prefix}fecha_asistencia < %s"]
    params = [desde, hasta]

    if request is not None:
        _apply_scope_to_conditions(request, condiciones, params, alias=alias)

    region = filtros.get("region")
    if region:
        cues = _cueanexos_por_region(region)
        if cues:
            condiciones.append(f"{prefix}cueanexo = ANY(%s)")
            params.append(cues)
        else:
            condiciones.append("1 = 0")

    for campo in ("departamento", "localidad", "nivel", "oferta", "ambito", "cueanexo", "grado", "seccion", "turno"):
        valor = filtros.get(campo)
        if valor:
            condiciones.append(f"{prefix}{campo} = %s")
            params.append(valor)

    # Sólo se incluyen registros pertenecientes a días realmente esperados
    # para esa sección. Si la tabla aún no fue instalada, se evita al menos
    # contar fines de semana; el SQL correctivo crea/puebla la tabla local.
    if calendario:
        if _relation_exists(TABLA_CALENDARIO_DIA):
            condiciones.append(
                f"EXISTS (SELECT 1 FROM {TABLA_CALENDARIO_DIA} cd "
                f"WHERE cd.id_seccion = {prefix}id_seccion "
                f"AND cd.dia = {prefix}fecha_asistencia AND cd.es_esperado)"
            )
        else:
            condiciones.append(f"EXTRACT(ISODOW FROM {prefix}fecha_asistencia) BETWEEN 1 AND 5")

    return " AND ".join(condiciones), params


def _build_where_calidad(filtros, request, alias=None):
    prefix = f"{alias}." if alias else ""
    condiciones = [f"{prefix}anio = %s", f"{prefix}mes = %s"]
    params = [filtros["anio"], filtros["mes"]]
    _apply_scope_to_conditions(request, condiciones, params, alias=alias)

    cues = _cueanexos_territorio(filtros)
    if cues is not None:
        if cues:
            condiciones.append(f"{prefix}cueanexo = ANY(%s)")
            params.append(cues)
        else:
            condiciones.append("1 = 0")

    for campo in ("departamento", "localidad", "nivel", "cueanexo"):
        valor = filtros.get(campo)
        if valor:
            condiciones.append(f"{prefix}{campo} = %s")
            params.append(valor)

    # oferta y ámbito son opcionales en versiones anteriores de la tabla.
    # La versión SQL incluida los agrega; mientras tanto se resuelven por CUE
    # cuando sea posible y no se fuerza una columna inexistente.
    return " AND ".join(condiciones), params


def _build_where_matricula(filtros, request, anio=None, mes=None, alias=None):
    prefix = f"{alias}." if alias else ""
    anio = anio or filtros["anio"]
    mes = mes or filtros["mes"]
    condiciones = [f"{prefix}anio = %s", f"{prefix}mes = %s"]
    params = [anio, mes]
    _apply_scope_to_conditions(request, condiciones, params, alias=alias)

    cues = _cueanexos_territorio(filtros)
    if cues is not None:
        if cues:
            condiciones.append(f"{prefix}cueanexo = ANY(%s)")
            params.append(cues)
        else:
            condiciones.append("1 = 0")

    for campo in ("nivel", "ambito", "cueanexo", "grado", "seccion", "turno"):
        valor = filtros.get(campo)
        if valor:
            condiciones.append(f"{prefix}{campo} = %s")
            params.append(valor)

    return " AND ".join(condiciones), params


def _build_where_nominal(filtros, request, anio=None, mes=None, alias=None):
    prefix = f"{alias}." if alias else ""
    anio = anio or filtros["anio"]
    mes = mes or filtros["mes"]
    desde, hasta = _rango_mes(anio, mes)
    condiciones = [f"{prefix}fecha_asistencia >= %s", f"{prefix}fecha_asistencia < %s"]
    params = [desde, hasta]
    _apply_scope_to_conditions(request, condiciones, params, alias=alias)

    cues = _cueanexos_territorio(filtros)
    if cues is not None:
        if cues:
            condiciones.append(f"{prefix}cueanexo = ANY(%s)")
            params.append(cues)
        else:
            condiciones.append("1 = 0")

    for campo in ("nivel", "cueanexo", "grado", "seccion", "turno"):
        valor = filtros.get(campo)
        if valor:
            condiciones.append(f"{prefix}{campo} = %s")
            params.append(valor)

    return " AND ".join(condiciones), params


def _build_where_semanal(filtros, request, anio_iso=None, semana_iso=None, alias=None):
    prefix = f"{alias}." if alias else ""
    condiciones = [f"{prefix}anio_iso = %s", f"{prefix}semana_iso = %s"]
    params = [anio_iso or filtros["anio_semana"], semana_iso or filtros["semana"]]
    _apply_scope_to_conditions(request, condiciones, params, alias=alias)

    cues = _cueanexos_territorio(filtros)
    if cues is not None:
        if cues:
            condiciones.append(f"{prefix}cueanexo = ANY(%s)")
            params.append(cues)
        else:
            condiciones.append("1 = 0")

    for campo in ("cueanexo", "nivel", "grado", "seccion", "turno"):
        valor = filtros.get(campo)
        if valor:
            condiciones.append(f"{prefix}{campo} = %s")
            params.append(valor)

    return " AND ".join(condiciones), params


def _matricula_total(filtros, request, anio=None, mes=None):
    # Fuente preferida: matrícula materializada desde inscripciones.
    if _relation_exists(TABLA_MATRICULA):
        where, params = _build_where_matricula(filtros, request, anio=anio, mes=mes)
        try:
            with connections[DB_ALIAS].cursor() as cursor:
                cursor.execute(f"SELECT COALESCE(SUM(matricula),0) FROM {TABLA_MATRICULA} WHERE {where}", params)
                valor = int(cursor.fetchone()[0] or 0)
                if valor > 0:
                    return valor, "INSCRIPCIONES"
        except Exception:
            pass

    # Respaldo: estudiantes únicos observados en la capa nominal local.
    if _relation_exists(TABLA_NOMINAL):
        where, params = _build_where_nominal(filtros, request, anio=anio, mes=mes, alias="n")
        try:
            with connections[DB_ALIAS].cursor() as cursor:
                cursor.execute(f"SELECT COUNT(DISTINCT n.id_alumno) FROM {TABLA_NOMINAL} n WHERE {where}", params)
                return int(cursor.fetchone()[0] or 0), "NOMINAL_OBSERVADA"
        except Exception:
            pass

    return 0, "SIN_DATOS"


def _adjuntar_matricula(datos, filtros, request, detalle=False):
    if not datos:
        return datos

    cues = list(dict.fromkeys(str(f.get("cueanexo")) for f in datos if f.get("cueanexo") is not None))
    mapa = {}
    fuente = "SIN_DATOS"

    if _relation_exists(TABLA_MATRICULA):
        where, params = _build_where_matricula(filtros, request)
        where += " AND cueanexo = ANY(%s)"
        params.append(cues)
        if detalle:
            sql = f"""
                SELECT cueanexo, nivel, grado, seccion, turno, SUM(matricula)::integer
                FROM {TABLA_MATRICULA}
                WHERE {where}
                GROUP BY cueanexo, nivel, grado, seccion, turno
            """
        else:
            sql = f"""
                SELECT cueanexo, SUM(matricula)::integer
                FROM {TABLA_MATRICULA}
                WHERE {where}
                GROUP BY cueanexo
            """
        try:
            with connections[DB_ALIAS].cursor() as cursor:
                cursor.execute(sql, params)
                rows = cursor.fetchall()
            if rows:
                fuente = "INSCRIPCIONES"
                if detalle:
                    mapa = {(str(c), n or "", g or "", s or "", t or ""): m for c, n, g, s, t, m in rows}
                else:
                    mapa = {str(c): m for c, m in rows}
        except Exception:
            mapa = {}

    if not mapa and _relation_exists(TABLA_NOMINAL):
        where, params = _build_where_nominal(filtros, request, alias="n")
        where += " AND n.cueanexo = ANY(%s)"
        params.append(cues)
        if detalle:
            sql = f"""
                SELECT n.cueanexo, n.nivel, n.grado, n.seccion, n.turno,
                       COUNT(DISTINCT n.id_alumno)::integer
                FROM {TABLA_NOMINAL} n
                WHERE {where}
                GROUP BY n.cueanexo, n.nivel, n.grado, n.seccion, n.turno
            """
        else:
            sql = f"""
                SELECT n.cueanexo, COUNT(DISTINCT n.id_alumno)::integer
                FROM {TABLA_NOMINAL} n
                WHERE {where}
                GROUP BY n.cueanexo
            """
        try:
            with connections[DB_ALIAS].cursor() as cursor:
                cursor.execute(sql, params)
                rows = cursor.fetchall()
            fuente = "NOMINAL_OBSERVADA"
            if detalle:
                mapa = {(str(c), n or "", g or "", s or "", t or ""): m for c, n, g, s, t, m in rows}
            else:
                mapa = {str(c): m for c, m in rows}
        except Exception:
            mapa = {}

    for fila in datos:
        if detalle:
            clave = (
                str(fila.get("cueanexo", "")),
                fila.get("nivel") or "",
                fila.get("grado") or "",
                fila.get("seccion") or "",
                fila.get("turno") or "",
            )
        else:
            clave = str(fila.get("cueanexo", ""))
        fila["matricula"] = mapa.get(clave, 0)
        fila["matricula_fuente"] = fuente

    return datos


def _calidad_resumen(filtros, request):
    if not _relation_exists(TABLA_CALIDAD):
        return {
            "dias_habiles": None,
            "dias_registrados": None,
            "jornadas_esperadas": 0,
            "jornadas_registradas": 0,
            "jornadas_sin_registro": 0,
            "secciones_calidad": 0,
            "secciones_completas": 0,
            "porcentaje_cobertura": None,
        }

    where, params = _build_where_calidad(filtros, request)
    try:
        with connections[DB_ALIAS].cursor() as cursor:
            cursor.execute(
                f"""
                SELECT
                    MAX(dias_habiles_calendario) AS dias_habiles,
                    MAX(dias_registrados) AS dias_registrados,
                    COALESCE(SUM(dias_esperados),0) AS jornadas_esperadas,
                    COALESCE(SUM(dias_registrados),0) AS jornadas_registradas,
                    COALESCE(SUM(dias_sin_registro),0) AS jornadas_sin_registro,
                    COUNT(*) AS secciones_calidad,
                    COUNT(*) FILTER (WHERE estado_registro='COMPLETO') AS secciones_completas,
                    ROUND(100.0 * SUM(dias_registrados) / NULLIF(SUM(dias_esperados),0),2) AS porcentaje_cobertura
                FROM {TABLA_CALIDAD}
                WHERE {where}
                """,
                params,
            )
            row = cursor.fetchone()
        return {
            "dias_habiles": row[0],
            "dias_registrados": row[1],
            "jornadas_esperadas": row[2] or 0,
            "jornadas_registradas": row[3] or 0,
            "jornadas_sin_registro": row[4] or 0,
            "secciones_calidad": row[5] or 0,
            "secciones_completas": row[6] or 0,
            "porcentaje_cobertura": row[7],
        }
    except Exception:
        return {
            "dias_habiles": None,
            "dias_registrados": None,
            "jornadas_esperadas": 0,
            "jornadas_registradas": 0,
            "jornadas_sin_registro": 0,
            "secciones_calidad": 0,
            "secciones_completas": 0,
            "porcentaje_cobertura": None,
        }


def _url_volver_por_rol(user):
    role_name = (get_access_scope(user).role_name or "").strip().upper()
    return "/director/" if role_name == "DIRECTOR" else reverse("archivos:portada_gestor")


@login_required
def dashboard(request):
    hoy = date.today()
    iso = hoy.isocalendar()
    anio_actual, mes_actual = hoy.year, hoy.month
    anio_semana_actual, semana_actual = iso.year, iso.week
    semana_desde = date.fromisocalendar(anio_semana_actual, semana_actual, 1)
    semana_hasta = semana_desde + timedelta(days=6)

    try:
        with connections[DB_ALIAS].cursor() as cursor:
            cursor.execute(f"SELECT EXTRACT(YEAR FROM MAX(fecha_asistencia))::integer, EXTRACT(MONTH FROM MAX(fecha_asistencia))::integer FROM {TABLA_ASISTENCIA}")
            row = cursor.fetchone()
            if row and row[0]:
                anio_actual, mes_actual = row
            cursor.execute(f"SELECT anio_iso, semana_iso, fecha_desde, fecha_hasta FROM {TABLA_ALERTA_SEMANAL} ORDER BY fecha_desde DESC LIMIT 1")
            row = cursor.fetchone()
            if row:
                anio_semana_actual, semana_actual, semana_desde, semana_hasta = row
    except Exception:
        pass

    return render(request, "asistencia_dashboard/dashboard.html", {
        "anio_actual": anio_actual,
        "mes_actual": mes_actual,
        "anio_semana_actual": anio_semana_actual,
        "semana_actual": semana_actual,
        "semana_desde": semana_desde,
        "semana_hasta": semana_hasta,
        "perfil_acceso": get_access_scope(request.user).role_name,
        "url_volver": _url_volver_por_rol(request.user),
    })


@login_required
def api_filtros(request):
    filtros = _filtros_request(request)
    desde, hasta = _rango_mes(filtros["anio"], filtros["mes"])
    resultado = {}

    scope = get_access_scope(request.user)
    regiones_qs = CapaUnicaOfertas.objects.using("default").exclude(region_loc__isnull=True).exclude(region_loc="")
    if not scope.full_access:
        regiones_qs = regiones_qs.filter(cueanexo__in=scope.cueanexos)
    resultado["region"] = list(regiones_qs.values_list("region_loc", flat=True).distinct().order_by("region_loc"))

    campos = {"departamento": "departamento", "localidad": "localidad", "nivel": "nivel", "oferta": "oferta", "ambito": "ambito", "grado": "grado", "turno": "turno"}
    with connections[DB_ALIAS].cursor() as cursor:
        for clave, campo in campos.items():
            condiciones = ["fecha_asistencia >= %s", "fecha_asistencia < %s", f"{campo} IS NOT NULL", f"BTRIM({campo}::text) <> ''"]
            params = [desde, hasta]
            _apply_scope_to_conditions(request, condiciones, params)
            cursor.execute(f"SELECT DISTINCT {campo} FROM {TABLA_ASISTENCIA} WHERE {' AND '.join(condiciones)} ORDER BY {campo}", params)
            resultado[clave] = [row[0] for row in cursor.fetchall()]
    return JsonResponse(resultado)


@login_required
def api_semanas(request):
    anio = _int_param(request, "anio", date.today().isocalendar().year)
    condiciones = ["anio_iso = %s"]
    params = [anio]
    _apply_scope_to_conditions(request, condiciones, params)
    with connections[DB_ALIAS].cursor() as cursor:
        cursor.execute(
            f"SELECT semana_iso, MIN(fecha_desde), MAX(fecha_hasta) FROM {TABLA_ALERTA_SEMANAL} WHERE {' AND '.join(condiciones)} GROUP BY semana_iso ORDER BY semana_iso DESC",
            params,
        )
        filas = cursor.fetchall()
    return JsonResponse({"data": [{"semana": r[0], "fecha_desde": r[1].isoformat(), "fecha_hasta": r[2].isoformat(), "texto": f"Semana {r[0]} · {r[1].strftime('%d/%m')} al {r[2].strftime('%d/%m/%Y')}"} for r in filas]})


@login_required
def api_resumen(request):
    filtros = _filtros_request(request)
    where, params = _build_where(filtros, request, alias="a", calendario=True)
    with connections[DB_ALIAS].cursor() as cursor:
        cursor.execute(
            f"""
            SELECT
                COUNT(DISTINCT a.cueanexo) AS establecimientos,
                COUNT(DISTINCT a.id_seccion) AS secciones,
                COUNT(DISTINCT a.fecha_asistencia) AS fechas_efectivas_con_carga,
                COALESCE(SUM(a.total_alumnos),0) AS alumno_jornadas,
                COALESCE(SUM(a.presentes),0) AS presentes,
                COALESCE(SUM(a.ausentes),0) AS ausentes,
                COALESCE(SUM(a.ausentes_justificados),0) AS ausentes_justificados,
                COALESCE(SUM(a.otras_faltas),0) AS otras_faltas,
                ROUND(100.0*SUM(COALESCE(a.presentes,0))/NULLIF(SUM(COALESCE(a.presentes,0)+COALESCE(a.ausentes,0)+COALESCE(a.ausentes_justificados,0)),0),2) AS porcentaje_asistencia,
                ROUND(100.0*SUM(COALESCE(a.ausentes,0)+COALESCE(a.ausentes_justificados,0))/NULLIF(SUM(COALESCE(a.presentes,0)+COALESCE(a.ausentes,0)+COALESCE(a.ausentes_justificados,0)),0),2) AS porcentaje_ausentismo
            FROM {TABLA_ASISTENCIA} a
            WHERE {where}
            """,
            params,
        )
        columnas = [c[0] for c in cursor.description]
        resultado = dict(zip(columnas, cursor.fetchone()))

    matricula, fuente = _matricula_total(filtros, request)
    resultado["matricula"] = matricula
    resultado["matricula_fuente"] = fuente
    calidad = _calidad_resumen(filtros, request)
    resultado.update(calidad)
    # Nunca se muestra el COUNT bruto como "días registrados" si existe calidad.
    if resultado.get("dias_registrados") is None:
        resultado["dias_registrados"] = resultado.get("fechas_efectivas_con_carga")
    return JsonResponse(resultado)


@login_required
def api_evolucion(request):
    filtros = _filtros_request(request)
    where, params = _build_where(filtros, request, alias="a", calendario=True)
    with connections[DB_ALIAS].cursor() as cursor:
        cursor.execute(
            f"""
            SELECT a.fecha_asistencia,
                   SUM(a.total_alumnos) AS alumno_jornadas,
                   SUM(a.presentes) AS presentes,
                   SUM(a.ausentes) AS ausentes,
                   SUM(a.ausentes_justificados) AS ausentes_justificados,
                   ROUND(100.0*SUM(COALESCE(a.presentes,0))/NULLIF(SUM(COALESCE(a.presentes,0)+COALESCE(a.ausentes,0)+COALESCE(a.ausentes_justificados,0)),0),2) AS porcentaje_asistencia,
                   ROUND(100.0*SUM(COALESCE(a.ausentes,0)+COALESCE(a.ausentes_justificados,0))/NULLIF(SUM(COALESCE(a.presentes,0)+COALESCE(a.ausentes,0)+COALESCE(a.ausentes_justificados,0)),0),2) AS porcentaje_ausentismo
            FROM {TABLA_ASISTENCIA} a
            WHERE {where}
            GROUP BY a.fecha_asistencia
            ORDER BY a.fecha_asistencia
            """,
            params,
        )
        datos = _dictfetchall(cursor)
    for fila in datos:
        fila["fecha_asistencia"] = fila["fecha_asistencia"].isoformat()
    return JsonResponse({"data": datos})


@login_required
def api_niveles(request):
    filtros = _filtros_request(request)
    where, params = _build_where(filtros, request, alias="a", calendario=True)
    with connections[DB_ALIAS].cursor() as cursor:
        cursor.execute(
            f"""
            SELECT COALESCE(a.nivel,'Sin nivel') AS nivel,
                   SUM(a.total_alumnos) AS alumno_jornadas,
                   SUM(a.presentes) AS presentes,
                   SUM(a.ausentes) AS ausentes,
                   ROUND(100.0*SUM(COALESCE(a.presentes,0))/NULLIF(SUM(COALESCE(a.presentes,0)+COALESCE(a.ausentes,0)+COALESCE(a.ausentes_justificados,0)),0),2) AS porcentaje_asistencia
            FROM {TABLA_ASISTENCIA} a
            WHERE {where}
            GROUP BY a.nivel
            ORDER BY porcentaje_asistencia DESC NULLS LAST
            """,
            params,
        )
        datos = _dictfetchall(cursor)
    return JsonResponse({"data": datos})


def _ranking_base(filtros, request):
    where, params = _build_where(filtros, request, alias="a", calendario=True)
    return f"""
        SELECT a.cueanexo, MAX(a.escuela) AS escuela,
               MAX(a.departamento) AS departamento, MAX(a.localidad) AS localidad,
               COUNT(DISTINCT a.fecha_asistencia) AS dias_registrados,
               SUM(a.total_alumnos) AS alumno_jornadas,
               SUM(a.presentes) AS presentes, SUM(a.ausentes) AS ausentes,
               SUM(a.ausentes_justificados) AS ausentes_justificados,
               ROUND(100.0*SUM(COALESCE(a.presentes,0))/NULLIF(SUM(COALESCE(a.presentes,0)+COALESCE(a.ausentes,0)+COALESCE(a.ausentes_justificados,0)),0),2) AS porcentaje_asistencia,
               ROUND(100.0*SUM(COALESCE(a.ausentes,0)+COALESCE(a.ausentes_justificados,0))/NULLIF(SUM(COALESCE(a.presentes,0)+COALESCE(a.ausentes,0)+COALESCE(a.ausentes_justificados,0)),0),2) AS porcentaje_ausentismo
        FROM {TABLA_ASISTENCIA} a WHERE {where}
        GROUP BY a.cueanexo
        HAVING SUM(COALESCE(a.total_alumnos,0)) > 0
    """, params


@login_required
def api_ranking(request):
    filtros = _filtros_request(request)
    base_sql, params = _ranking_base(filtros, request)
    page, page_size, offset = _pagination_request(request)
    with connections[DB_ALIAS].cursor() as cursor:
        cursor.execute(f"SELECT COUNT(*) FROM ({base_sql}) q", params)
        total = cursor.fetchone()[0]
        cursor.execute(base_sql + " ORDER BY porcentaje_ausentismo DESC NULLS LAST, escuela LIMIT %s OFFSET %s", params + [page_size, offset])
        datos = _dictfetchall(cursor)
    _adjuntar_matricula(datos, filtros, request)
    return JsonResponse({"data": datos, "pagination": _pagination_meta(page, page_size, total)})


@login_required
def api_alertas(request):
    filtros = _filtros_request(request)
    base_sql, params = _ranking_base(filtros, request)
    page, page_size, offset = _pagination_request(request)
    cte = f"""
        WITH indicadores AS ({base_sql}),
        alertas AS (
            SELECT *, CASE
                WHEN porcentaje_asistencia IS NULL THEN 'SIN DATOS'
                WHEN porcentaje_asistencia < 70 THEN 'CRITICO'
                WHEN porcentaje_asistencia < 80 THEN 'ALTO'
                WHEN porcentaje_asistencia < 90 THEN 'ATENCION'
                ELSE 'NORMAL' END AS nivel_alerta
            FROM indicadores
        )
    """
    nivel = filtros.get("alerta")
    filtro = " WHERE nivel_alerta=%s " if nivel else ""
    extra = [nivel] if nivel else []
    with connections[DB_ALIAS].cursor() as cursor:
        cursor.execute(cte + " SELECT nivel_alerta, COUNT(*) FROM alertas GROUP BY nivel_alerta", params)
        resumen = {"NORMAL": 0, "ATENCION": 0, "ALTO": 0, "CRITICO": 0, "SIN DATOS": 0}
        for n, c in cursor.fetchall():
            if n in resumen:
                resumen[n] = c
        cursor.execute(cte + " SELECT COUNT(*) FROM alertas " + filtro, params + extra)
        total = cursor.fetchone()[0]
        cursor.execute(
            cte + " SELECT * FROM alertas " + filtro +
            " ORDER BY CASE nivel_alerta WHEN 'CRITICO' THEN 1 WHEN 'ALTO' THEN 2 WHEN 'ATENCION' THEN 3 WHEN 'NORMAL' THEN 4 ELSE 5 END, porcentaje_asistencia ASC NULLS LAST, escuela LIMIT %s OFFSET %s",
            params + extra + [page_size, offset],
        )
        datos = _dictfetchall(cursor)
    _adjuntar_matricula(datos, filtros, request)
    return JsonResponse({"resumen": resumen, "data": datos, "pagination": _pagination_meta(page, page_size, total)})


def _consulta_mensual_base(filtros, request, detalle):
    where, params = _build_where(filtros, request, alias="a", calendario=True)
    if detalle:
        base = f"""
            SELECT a.cueanexo, MAX(a.escuela) AS escuela, a.nivel, a.grado, a.seccion, a.turno,
                   COUNT(DISTINCT a.fecha_asistencia) AS dias_registrados,
                   SUM(a.total_alumnos) AS alumno_jornadas,
                   SUM(a.presentes) AS presentes, SUM(a.ausentes) AS ausentes,
                   SUM(a.ausentes_justificados) AS ausentes_justificados, SUM(a.otras_faltas) AS otras_faltas,
                   ROUND(100.0*SUM(COALESCE(a.presentes,0))/NULLIF(SUM(COALESCE(a.presentes,0)+COALESCE(a.ausentes,0)+COALESCE(a.ausentes_justificados,0)),0),2) AS porcentaje_asistencia
            FROM {TABLA_ASISTENCIA} a WHERE {where}
            GROUP BY a.cueanexo, a.nivel, a.grado, a.seccion, a.turno
        """
        return base, params, " ORDER BY nivel, grado, seccion, turno ", "seccion"
    base = f"""
        SELECT a.cueanexo, MAX(a.escuela) AS escuela, MAX(a.departamento) AS departamento, MAX(a.localidad) AS localidad,
               COUNT(DISTINCT a.fecha_asistencia) AS dias_registrados,
               SUM(a.total_alumnos) AS alumno_jornadas,
               SUM(a.presentes) AS presentes, SUM(a.ausentes) AS ausentes,
               SUM(a.ausentes_justificados) AS ausentes_justificados, SUM(a.otras_faltas) AS otras_faltas,
               ROUND(100.0*SUM(COALESCE(a.presentes,0))/NULLIF(SUM(COALESCE(a.presentes,0)+COALESCE(a.ausentes,0)+COALESCE(a.ausentes_justificados,0)),0),2) AS porcentaje_asistencia
        FROM {TABLA_ASISTENCIA} a WHERE {where}
        GROUP BY a.cueanexo
    """
    return base, params, " ORDER BY escuela ", "establecimiento"


@login_required
def api_mensual(request):
    filtros = _filtros_request(request)
    detalle = bool(filtros.get("cueanexo"))
    base, params, order, nivel = _consulta_mensual_base(filtros, request, detalle)
    page, page_size, offset = _pagination_request(request)
    with connections[DB_ALIAS].cursor() as cursor:
        cursor.execute(f"SELECT COUNT(*) FROM ({base}) q", params)
        total = cursor.fetchone()[0]
        cursor.execute(base + order + " LIMIT %s OFFSET %s", params + [page_size, offset])
        datos = _dictfetchall(cursor)
    _adjuntar_matricula(datos, filtros, request, detalle=detalle)
    return JsonResponse({"data": datos, "nivel": nivel, "pagination": _pagination_meta(page, page_size, total)})


@login_required
def api_secciones(request):
    filtros = _filtros_request(request)
    page, page_size, offset = _pagination_request(request)
    if not filtros.get("cueanexo"):
        return JsonResponse({"data": [], "requiere_cue": True, "pagination": _pagination_meta(page, page_size, 0)})
    base, params, order, _ = _consulta_mensual_base(filtros, request, True)
    with connections[DB_ALIAS].cursor() as cursor:
        cursor.execute(f"SELECT COUNT(*) FROM ({base}) q", params)
        total = cursor.fetchone()[0]
        cursor.execute(base + order + " LIMIT %s OFFSET %s", params + [page_size, offset])
        datos = _dictfetchall(cursor)
    _adjuntar_matricula(datos, filtros, request, detalle=True)
    return JsonResponse({"data": datos, "pagination": _pagination_meta(page, page_size, total)})


@login_required
def api_establecimientos(request):
    filtros = _filtros_request(request)
    q = request.GET.get("q", "").strip()
    desde, hasta = _rango_mes(filtros["anio"], filtros["mes"])
    condiciones = ["fecha_asistencia >= %s", "fecha_asistencia < %s"]
    params = [desde, hasta]
    _apply_scope_to_conditions(request, condiciones, params)
    if filtros.get("region"):
        cues = _cueanexos_por_region(filtros["region"])
        if cues:
            condiciones.append("cueanexo = ANY(%s)")
            params.append(cues)
        else:
            condiciones.append("1=0")
    if q:
        condiciones.append("(cueanexo ILIKE %s OR escuela ILIKE %s)")
        params += [f"%{q}%", f"%{q}%"]
    with connections[DB_ALIAS].cursor() as cursor:
        cursor.execute(f"SELECT cueanexo, MAX(escuela) FROM {TABLA_ASISTENCIA} WHERE {' AND '.join(condiciones)} GROUP BY cueanexo ORDER BY MAX(escuela) LIMIT 10", params)
        filas = cursor.fetchall()
    return JsonResponse({"results": [{"id": c, "text": f"{c} · {e}"} for c, e in filas]})


@login_required
def api_calidad_registro(request):
    filtros = _filtros_request(request)
    page, page_size, offset = _pagination_request(request)
    if not _relation_exists(TABLA_CALIDAD):
        return JsonResponse({"data": [], "resumen": {}, "procesado": False, "message": "La tabla de calidad todavía no está instalada.", "pagination": _pagination_meta(page, page_size, 0)})
    where, params = _build_where_calidad(filtros, request)
    base = f"""
        SELECT cueanexo, MAX(escuela) AS escuela, MAX(departamento) AS departamento, MAX(localidad) AS localidad,
               COUNT(DISTINCT id_seccion) AS cantidad_secciones,
               MAX(dias_habiles_calendario) AS dias_habiles_calendario,
               SUM(dias_excepcion) AS jornadas_excepcion,
               SUM(dias_evento_excluyente) AS jornadas_evento_excluyente,
               SUM(dias_esperados) AS jornadas_esperadas,
               SUM(dias_registrados) AS jornadas_registradas,
               SUM(dias_sin_registro) AS jornadas_sin_registro,
               ROUND(100.0*SUM(dias_registrados)/NULLIF(SUM(dias_esperados),0),2) AS porcentaje_cumplimiento,
               CASE WHEN SUM(dias_esperados)=0 THEN 'SIN_DIAS_ESPERADOS'
                    WHEN SUM(dias_registrados)=0 THEN 'SIN_CARGA'
                    WHEN SUM(dias_sin_registro)>0 THEN 'PARCIAL' ELSE 'COMPLETO' END AS estado_registro
        FROM {TABLA_CALIDAD} WHERE {where} GROUP BY cueanexo
    """
    with connections[DB_ALIAS].cursor() as cursor:
        cursor.execute(f"SELECT COUNT(*) FROM ({base}) q", params)
        total = cursor.fetchone()[0]
        cursor.execute(f"SELECT estado_registro, COUNT(*) FROM ({base}) q GROUP BY estado_registro", params)
        resumen = {"COMPLETO": 0, "PARCIAL": 0, "SIN_CARGA": 0, "SIN_DIAS_ESPERADOS": 0}
        for e, c in cursor.fetchall():
            if e in resumen:
                resumen[e] = c
        cursor.execute(base + " ORDER BY jornadas_sin_registro DESC, escuela LIMIT %s OFFSET %s", params + [page_size, offset])
        datos = _dictfetchall(cursor)
    return JsonResponse({"data": datos, "resumen": resumen, "procesado": total > 0, "message": None if total else "No hay calidad procesada para el período.", "pagination": _pagination_meta(page, page_size, total)})


def _nivel_severidad(nivel):
    return {"SIN DATOS": 0, "NORMAL": 1, "ATENCION": 2, "ALTO": 3, "CRITICO": 4}.get(nivel or "SIN DATOS", 0)


def _motivo_alerta(p, c, final):
    if final in (None, "NORMAL", "SIN DATOS"):
        return "Sin alerta"
    sf, sp, sc = _nivel_severidad(final), _nivel_severidad(p), _nivel_severidad(c)
    if sp == sf and sc == sf:
        return "Porcentaje + continuidad"
    if sp == sf:
        return "Porcentaje"
    if sc == sf:
        return "Continuidad"
    return "Combinada"


@login_required
def api_alertas_alumnos(request):
    filtros = _filtros_request(request)
    page, page_size, offset = _pagination_request(request)
    if not filtros.get("cueanexo"):
        return JsonResponse({"data": [], "resumen": {"NORMAL": 0, "ATENCION": 0, "ALTO": 0, "CRITICO": 0, "SIN DATOS": 0}, "requiere_cue": True, "pagination": _pagination_meta(page, page_size, 0)})
    where, params = _build_where_semanal(filtros, request)
    if filtros.get("alerta"):
        where += " AND nivel_alerta_final=%s"
        params.append(filtros["alerta"])
    select_sql = f"""
        SELECT cueanexo, escuela, id_alumno, id_persona, nombre_apellido, nivel, grado, seccion, turno,
               fecha_desde, fecha_hasta, dias_esperados_semana, dias_registrados, dias_sin_registro_semana,
               porcentaje_cumplimiento_registro, unidades_calificables, inasistencias_equivalentes,
               dias_ausencia_completa, fecha_ultima_presencia, fecha_ultima_ausencia_completa, ultima_fecha_registrada,
               racha_actual_ausencias, racha_maxima_ausencias, porcentaje_asistencia, nivel_porcentaje,
               nivel_continuidad, nivel_alerta_final
        FROM {TABLA_ALERTA_SEMANAL} WHERE {where}
    """
    order = " ORDER BY CASE nivel_alerta_final WHEN 'CRITICO' THEN 1 WHEN 'ALTO' THEN 2 WHEN 'ATENCION' THEN 3 WHEN 'NORMAL' THEN 4 ELSE 5 END, racha_actual_ausencias DESC, racha_maxima_ausencias DESC, porcentaje_asistencia ASC NULLS LAST, nombre_apellido "
    with connections[DB_ALIAS].cursor() as cursor:
        cursor.execute(f"SELECT COUNT(*) FROM ({select_sql}) q", params)
        total = cursor.fetchone()[0]
        cursor.execute(f"SELECT nivel_alerta_final, COUNT(DISTINCT id_alumno) FROM {TABLA_ALERTA_SEMANAL} WHERE {where} GROUP BY nivel_alerta_final", params)
        resumen = {"NORMAL": 0, "ATENCION": 0, "ALTO": 0, "CRITICO": 0, "SIN DATOS": 0}
        for n, c in cursor.fetchall():
            if n in resumen:
                resumen[n] = c
        cursor.execute(select_sql + order + " LIMIT %s OFFSET %s", params + [page_size, offset])
        datos = _dictfetchall(cursor)
    for fila in datos:
        fila["motivo_alerta"] = _motivo_alerta(fila.get("nivel_porcentaje"), fila.get("nivel_continuidad"), fila.get("nivel_alerta_final"))
        for campo in ("fecha_desde", "fecha_hasta", "fecha_ultima_presencia", "fecha_ultima_ausencia_completa", "ultima_fecha_registrada"):
            if fila.get(campo):
                fila[campo] = fila[campo].isoformat()
    return JsonResponse({"data": datos, "resumen": resumen, "requiere_cue": False, "pagination": _pagination_meta(page, page_size, total)})


@login_required
def api_resumen_alertas_semana(request):
    filtros = _filtros_request(request)
    where, params = _build_where_semanal(filtros, request)
    with connections[DB_ALIAS].cursor() as cursor:
        cursor.execute(
            f"""
            SELECT COUNT(DISTINCT id_alumno) FILTER (WHERE nivel_alerta_final IN ('ATENCION','ALTO','CRITICO')),
                   COUNT(DISTINCT id_alumno) FILTER (WHERE nivel_alerta_final='ATENCION'),
                   COUNT(DISTINCT id_alumno) FILTER (WHERE nivel_alerta_final='ALTO'),
                   COUNT(DISTINCT id_alumno) FILTER (WHERE nivel_alerta_final='CRITICO'),
                   MIN(fecha_desde), MAX(fecha_hasta), COUNT(DISTINCT id_alumno)
            FROM {TABLA_ALERTA_SEMANAL} WHERE {where}
            """,
            params,
        )
        alertas, atencion, alto, critico, desde, hasta, alumnos_evaluados = cursor.fetchone()
    if hasta is None:
        desde = date.fromisocalendar(filtros["anio_semana"], filtros["semana"], 1)
        hasta = desde + timedelta(days=6)
    matricula, fuente = _matricula_total(filtros, request, anio=hasta.year, mes=hasta.month)
    incidencia = round(100.0 * int(alertas or 0) / matricula, 2) if matricula else None
    return JsonResponse({
        "matricula_referencia": matricula,
        "matricula_fuente": fuente,
        "alumnos_evaluados": int(alumnos_evaluados or 0),
        "alumnos_alerta": int(alertas or 0),
        "atencion": int(atencion or 0), "alto": int(alto or 0), "critico": int(critico or 0),
        "incidencia": incidencia,
        "fecha_desde": desde.isoformat(), "fecha_hasta": hasta.isoformat(),
    })


@login_required
def api_tendencia_alertas(request):
    filtros = _filtros_request(request)
    inicio_actual = date.fromisocalendar(filtros["anio_semana"], filtros["semana"], 1)
    resultado = []
    for despl in (3, 2, 1, 0):
        inicio = inicio_actual - timedelta(weeks=despl)
        iso = inicio.isocalendar()
        fs = dict(filtros)
        fs["anio_semana"], fs["semana"] = iso.year, iso.week
        where, params = _build_where_semanal(fs, request, anio_iso=iso.year, semana_iso=iso.week)
        with connections[DB_ALIAS].cursor() as cursor:
            cursor.execute(
                f"SELECT COUNT(DISTINCT id_alumno) FILTER (WHERE nivel_alerta_final IN ('ATENCION','ALTO','CRITICO')), COUNT(DISTINCT id_alumno) FILTER (WHERE nivel_alerta_final='CRITICO'), COUNT(DISTINCT id_alumno) FROM {TABLA_ALERTA_SEMANAL} WHERE {where}",
                params,
            )
            alertas, criticos, evaluados = cursor.fetchone()
        fin = inicio + timedelta(days=6)
        matricula, fuente = _matricula_total(fs, request, anio=fin.year, mes=fin.month)
        incidencia = round(100.0 * int(alertas or 0) / matricula, 2) if matricula else None
        resultado.append({"anio_iso": iso.year, "semana_iso": iso.week, "fecha_desde": inicio.isoformat(), "fecha_hasta": fin.isoformat(), "label": f"Sem {iso.week}", "alumnos_alerta": int(alertas or 0), "criticos": int(criticos or 0), "alumnos_evaluados": int(evaluados or 0), "matricula": matricula, "matricula_fuente": fuente, "incidencia": incidencia})
    return JsonResponse({"data": resultado})


@login_required
def api_ranking_alertas(request):
    filtros = _filtros_request(request)
    page, page_size, offset = _pagination_request(request)
    where, params = _build_where_semanal(filtros, request, alias="a")
    with connections[DB_ALIAS].cursor() as cursor:
        cursor.execute(
            f"""
            SELECT a.cueanexo, MAX(a.escuela) AS escuela,
                   COUNT(DISTINCT a.id_alumno) FILTER (WHERE a.nivel_alerta_final IN ('ATENCION','ALTO','CRITICO')) AS alumnos_alerta,
                   COUNT(DISTINCT a.id_alumno) FILTER (WHERE a.nivel_alerta_final='CRITICO') AS criticos
            FROM {TABLA_ALERTA_SEMANAL} a WHERE {where}
            GROUP BY a.cueanexo
            HAVING COUNT(DISTINCT a.id_alumno) FILTER (WHERE a.nivel_alerta_final IN ('ATENCION','ALTO','CRITICO')) > 0
            ORDER BY alumnos_alerta DESC
            """,
            params,
        )
        todos = _dictfetchall(cursor)
    _adjuntar_matricula(todos, filtros, request)
    for fila in todos:
        m = fila.get("matricula") or 0
        fila["incidencia_alerta"] = round(100.0 * (fila.get("alumnos_alerta") or 0) / m, 2) if m else None
    todos.sort(key=lambda f: (-(f["incidencia_alerta"] if f["incidencia_alerta"] is not None else -1), -(f.get("alumnos_alerta") or 0), f.get("escuela") or ""))
    total = len(todos)
    datos = todos[offset:offset + page_size]
    return JsonResponse({"data": datos, "pagination": _pagination_meta(page, page_size, total)})
