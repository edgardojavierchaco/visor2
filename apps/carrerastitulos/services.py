"""Consultas SNU parametrizadas, paginadas y sin duplicación de ofertas visibles.

Requiere que public.v_carreras_titulos_integrada contenga EXCLUSIVAMENTE
CUEANEXO vinculados a la oferta 'Común - SNU' en el padrón.
La deduplicación es de presentación: (cueanexo, nivel, carrera, titulo),
normalizados por espacios exteriores y mayúsculas. No elimina filas físicas.
"""
from django.core.cache import cache
from django.db import connection
from .access import SnuScope

VIEW = 'public.v_carreras_titulos_integrada'
FILTER_FIELDS = {
    'region': 'region', 'departamento': 'departamento',
    'localidad': 'localidad', 'sector': 'sector',
    'nivel': 'nivel', 'ambito': 'ambito',
    'carrera': 'carrera', 'titulo': 'titulo',
}

# La selección de una fila representativa es determinista para cada
# combinación visible. No usar c_oferta como parte de la identidad visible.
DEDUP_KEYS = (
    "cueanexo",
    "LOWER(BTRIM(COALESCE(nivel, '')))",
    "LOWER(BTRIM(COALESCE(carrera, '')))",
    "LOWER(BTRIM(COALESCE(titulo, '')))",
)
DEDUP_KEY_SQL = ', '.join(DEDUP_KEYS)
# Columnas proyectadas explícitamente: evita recuperar geom y otros datos grandes.
COLUMNS = (
    'cueanexo', 'establecimiento', 'region', 'departamento', 'localidad',
    'sector', 'nivel', 'ambito', 'carrera', 'titulo', 'c_oferta',
    'calle', 'numero', 'telefono', 'email',
    'latitud', 'longitud', 'georreferenciado', 'existe_en_padron',
)


def fetch(sql, params=()):
    with connection.cursor() as cursor:
        cursor.execute(sql, params)
        if not cursor.description:
            return []
        keys = [x[0] for x in cursor.description]
        return [dict(zip(keys, row)) for row in cursor.fetchall()]


def _scope_parts(scope):
    """Condición SQL parametrizada; aplica al origen, antes de deduplicar."""
    if scope is None:  # Consulta PÚBLICA, solamente a la vista SNU.
        return [], []
    if not isinstance(scope, SnuScope):
        raise ValueError('Alcance ministerial inválido: acceso denegado.')
    if scope.kind == 'global':
        return [], []
    if scope.kind == 'regional' and scope.regiones:
        return ['region = ANY(%s)'], [list(scope.regiones)]
    if scope.kind == 'supervisor' and scope.cueanexos:
        return ['cueanexo = ANY(%s)'], [list(scope.cueanexos)]
    raise ValueError('Alcance ministerial vacío: acceso denegado.')


def clauses(query, scope=None):
    parts, args = ['TRUE'], []
    restrictions, values = _scope_parts(scope)
    parts.extend(restrictions)
    args.extend(values)
    for key, column in FILTER_FIELDS.items():
        values = [v.strip() for v in query.getlist(key) if v and v.strip()][:30]
        if values:
            parts.append(f'{column} = ANY(%s)')
            args.append(values)
    search = (query.get('q') or '').strip()[:120]
    if search:
        parts.append(
            "(COALESCE(establecimiento,'') ILIKE %s OR "
            "COALESCE(carrera,'') ILIKE %s OR "
            "COALESCE(titulo,'') ILIKE %s OR "
            "COALESCE(localidad,'') ILIKE %s OR "
            "cueanexo ILIKE %s)"
        )
        args.extend(['%' + search + '%'] * 5)
    return ' AND '.join(parts), args


def _unique_from(where):
    """Devuelve una subconsulta de ofertas visibles únicas, después de filtrar.

    DISTINCT ON elige una fila representativa por combinación académica.
    Todos los indicadores utilizan esta misma definición de oferta.
    """
    return (
        '(SELECT DISTINCT ON (' + DEDUP_KEY_SQL + ') '
        + ', '.join(COLUMNS)
        + f' FROM {VIEW} WHERE {where}'
        + ' ORDER BY ' + DEDUP_KEY_SQL
        + ', c_oferta ASC NULLS LAST, establecimiento ASC NULLS LAST) AS ofertas_unicas'
    )


def filters(scope=None):
    """Facetas limitadas por permisos; caché segmentada por ámbito."""
    if scope is None:
        scope_key = ('public',)
    elif isinstance(scope, SnuScope):
        scope_key = (scope.kind, scope.regiones, scope.cueanexos)
    else:
        raise ValueError('Alcance inválido')
    key = ('carreras_snu_facetas_permisos_v3', scope_key)
    stored = cache.get(key)
    if stored is not None:
        return stored
    parts, params = _scope_parts(scope)
    where = ('WHERE ' + ' AND '.join(parts)) if parts else ''
    result = {}
    for name, col in FILTER_FIELDS.items():
        rows = fetch(
            f'SELECT DISTINCT {col} AS value FROM {VIEW} {where} '
            'ORDER BY value NULLS LAST', params
        )
        result[name] = [r['value'] for r in rows if r['value']]
    cache.set(key, result, 600)
    return result


def results(query, scope=None):
    where, args = clauses(query, scope)
    try:
        page = max(1, min(int(query.get('page', 1)), 100000))
    except (ValueError, TypeError):
        page = 1
    size = 25
    base = ' FROM ' + _unique_from(where)
    total = fetch('SELECT COUNT(*) AS n' + base, args)[0]['n']
    rows = fetch(
        'SELECT cueanexo, establecimiento, region, departamento, localidad, sector, '
        'nivel, carrera, titulo, c_oferta, latitud, longitud, georreferenciado'
        + base + ' ORDER BY localidad NULLS LAST, establecimiento NULLS LAST, '
        'carrera NULLS LAST, titulo NULLS LAST, cueanexo '
        'LIMIT %s OFFSET %s', args + [size, (page - 1) * size]
    )
    return {'total': total, 'page': page, 'page_size': size,
            'pages': max(1, (total + size - 1) // size), 'data': rows}


def summary(query, scope=None):
    where, args = clauses(query, scope)
    return fetch('''SELECT COUNT(*) AS ofertas,
        COUNT(DISTINCT cueanexo) AS establecimientos,
        COUNT(DISTINCT NULLIF(BTRIM(carrera), '')) AS carreras,
        COUNT(DISTINCT NULLIF(BTRIM(titulo), '')) AS titulos,
        COUNT(DISTINCT localidad) AS localidades,
        COUNT(DISTINCT region) AS regiones,
        COUNT(DISTINCT cueanexo) FILTER (WHERE georreferenciado) AS georreferenciados,
        COUNT(DISTINCT cueanexo) FILTER (WHERE NOT existe_en_padron) AS sin_padron
        FROM ''' + _unique_from(where), args)[0]


def group_stats(query, scope=None):
    where, args = clauses(query, scope)
    base = _unique_from(where)
    out = {}
    for field in ('region', 'departamento', 'localidad', 'sector',
                  'nivel', 'ambito', 'carrera', 'titulo'):
        out[field] = fetch(
            f"SELECT COALESCE(NULLIF({field}, ''), 'Sin dato') AS nombre, "
            f'COUNT(*) AS ofertas, COUNT(DISTINCT cueanexo) AS establecimientos '
            f'FROM {base} GROUP BY 1 ORDER BY ofertas DESC, nombre LIMIT 15', args
        )
    return out


def map_points(query, scope=None):
    where, args = clauses(query, scope)
    return fetch('''SELECT cueanexo,
        MAX(establecimiento) AS establecimiento,
        MAX(localidad) AS localidad,
        MAX(region) AS region,
        MAX(latitud) AS latitud,
        MAX(longitud) AS longitud,
        COUNT(*) AS ofertas,
        COUNT(DISTINCT NULLIF(BTRIM(carrera), '')) AS carreras
        FROM ''' + _unique_from(where)
        + ' WHERE georreferenciado GROUP BY cueanexo ORDER BY cueanexo LIMIT 5000', args)


def institution(cue, scope=None):
    restrictions, restrictions_params = _scope_parts(scope)
    conditions = 'cueanexo = %s'
    args = [cue]
    if restrictions:
        conditions += ' AND ' + ' AND '.join(restrictions)
        args.extend(restrictions_params)
    return fetch("""SELECT cueanexo, establecimiento, region, departamento, localidad, ambito,
        sector, calle, numero, telefono, email, nivel, carrera, titulo,
        latitud, longitud, georreferenciado, existe_en_padron
        FROM """ + _unique_from(conditions) + ' ORDER BY carrera, titulo, nivel', args)


def export_rows(query, scope=None, limit=20000):
    """Consulta para exportación CSV con la misma deduplicación y filtros."""
    where, args = clauses(query, scope)
    cols = ['cueanexo', 'establecimiento', 'region', 'departamento', 'localidad',
            'sector', 'nivel', 'carrera', 'titulo']
    sql = ('SELECT ' + ', '.join(cols) + ' FROM ' + _unique_from(where)
           + ' ORDER BY localidad, establecimiento, carrera, titulo LIMIT %s')
    return cols, sql, args + [limit]
