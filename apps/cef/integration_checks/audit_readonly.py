"""Auditor independiente: servicio PostgreSQL RO explícito y SQL fijo agregado.

Nunca importa Django/settings ni recibe SQL del usuario. Codex no ejecuta este módulo
contra ninguna BD. Su uso local queda pendiente de revisión de ChatGPT.
"""
from dataclasses import dataclass
import re

from safety import Blocked, CUES, require

CATALOGS = ("ejes", "codigos_ra", "actividades", "niveles_actividad", "rangos_etarios",
    "dias_semana", "turnos", "beneficio_sino_tipo", "fuente_financiamiento_tipo",
    "prestacion_tipo", "espacio_comedor_tipo", "orientacion_tipo", "estado_material_tipo",
    "materiales")
TABLES = CATALOGS + ("ciclos", "alumnos_cef", "docentes_cef", "grupos",
    "grupo_dias_func", "grupo_estado_movimientos", "inscripciones", "docentes_grupo",
    "jornadas_asistencia", "asistencias", "asistencia_movimientos",
    "datos_relevamiento", "inventario_materiales", "inventario_materiales_estados")


# Relaciones entre tablas CEF derivadas estaticamente del codigo vivo.
CEF_FOREIGN_KEYS = (('actividades', 'eje_id', 'ejes'), ('actividades', 'codigo_ra_id', 'codigos_ra'), ('datos_relevamiento', 'ciclo_id', 'ciclos'), ('datos_relevamiento', 'beneficio_alimentario_gratuito_id', 'beneficio_sino_tipo'), ('datos_relevamiento', 'fuente_financiamiento_id', 'fuente_financiamiento_tipo'), ('datos_relevamiento', 'prestacion_tipo_id', 'prestacion_tipo'), ('datos_relevamiento', 'espacio_comedor_id', 'espacio_comedor_tipo'), ('datos_relevamiento', 'c_orientacion_id', 'orientacion_tipo'), ('grupos', 'ciclo_id', 'ciclos'), ('grupos', 'actividad_id', 'actividades'), ('grupos', 'nivel_id', 'niveles_actividad'), ('grupos', 'rango_etario_id', 'rangos_etarios'), ('grupos', 'turno_id', 'turnos'), ('grupos', 'grupo_origen_id', 'grupos'), ('grupos', 'codigo_ra_override_id', 'codigos_ra'), ('grupo_estado_movimientos', 'grupo_id', 'grupos'), ('grupo_dias_func', 'grupo_id', 'grupos'), ('grupo_dias_func', 'dia_semana_id', 'dias_semana'), ('alumnos_cef', 'ciclo_id', 'ciclos'), ('docentes_cef', 'ciclo_id', 'ciclos'), ('inscripciones', 'grupo_id', 'grupos'), ('docentes_grupo', 'grupo_id', 'grupos'), ('jornadas_asistencia', 'grupo_id', 'grupos'), ('asistencias', 'jornada_id', 'jornadas_asistencia'), ('asistencias', 'inscripcion_id', 'inscripciones'), ('asistencia_movimientos', 'asistencia_id', 'asistencias'), ('inventario_materiales', 'ciclo_id', 'ciclos'), ('inventario_materiales', 'material_id', 'materiales'), ('inventario_materiales_estados', 'inventario_material_id', 'inventario_materiales'), ('inventario_materiales_estados', 'estado_id', 'estado_material_tipo'))

@dataclass(frozen=True)
class Check:
    code: str
    description: str
    sql: str
    expected: tuple = (0,)


CHECKS = [
    Check("R01", "Ciclo seleccionado existente", "SELECT count(*) FROM cef.ciclos WHERE id=%s", (1,)),
    Check("R02", "Fechas oficiales del ciclo coherentes", """
        SELECT count(*) FROM cef.ciclos c WHERE c.id=%s AND (
            c.fecha_inicio IS NULL OR EXTRACT(YEAR FROM c.fecha_inicio)<>c.anio OR
            (c.fecha_fin IS NOT NULL AND (c.fecha_fin<c.fecha_inicio
                OR EXTRACT(YEAR FROM c.fecha_fin)<>c.anio)))"""),
    Check("R03", "Estado del ciclo coherente", """
        SELECT count(*) FROM cef.ciclos WHERE id=%s AND (cerrado AND actual OR actual AND NOT activo)"""),
    Check("R04", "Cuatro alumnos activos por cada CUE autorizado", """
        SELECT count(*) FILTER (WHERE cueanexo='220169000'),
               count(*) FILTER (WHERE cueanexo='220169100')
        FROM cef.alumnos_cef WHERE ciclo_id=%s AND estado='activo'
          AND cueanexo IN ('220169000','220169100')""", (4,4)),
    Check("R05", "Cuatro profesores activos por cada CUE autorizado", """
        SELECT count(*) FILTER (WHERE cueanexo='220169000'),
               count(*) FILTER (WHERE cueanexo='220169100')
        FROM cef.docentes_cef WHERE ciclo_id=%s AND estado='activo'
          AND cueanexo IN ('220169000','220169100')""", (4,4)),
    Check("R06", "Sin alumnos activos duplicados en bancos", """
        SELECT count(*) FROM (SELECT 1 FROM cef.alumnos_cef
        WHERE ciclo_id=%s AND cueanexo IN ('220169000','220169100') AND estado='activo'
        GROUP BY cueanexo,alumno_id HAVING count(*)>1) s"""),
    Check("R07", "Sin profesores activos duplicados en bancos", """
        SELECT count(*) FROM (SELECT 1 FROM cef.docentes_cef
        WHERE ciclo_id=%s AND cueanexo IN ('220169000','220169100') AND estado='activo'
        GROUP BY cueanexo,docente_cuil HAVING count(*)>1) s"""),
    Check("R08", "Sin claves de grupo duplicadas", """
        SELECT count(*) FROM (SELECT 1 FROM cef.grupos WHERE ciclo_id=%s
          AND cueanexo IN ('220169000','220169100')
          GROUP BY cueanexo,actividad_id,numero HAVING count(*)>1) s"""),
    Check("R09", "Vigencias y estados de bancos coherentes", """
        WITH periodos AS (
          SELECT ciclo_id,cueanexo,estado,fecha_alta,fecha_baja FROM cef.alumnos_cef
          UNION ALL SELECT ciclo_id,cueanexo,estado,fecha_alta,fecha_baja FROM cef.docentes_cef
        ) SELECT count(*) FROM periodos b JOIN cef.ciclos c ON c.id=b.ciclo_id
        WHERE c.id=%s AND b.cueanexo IN ('220169000','220169100') AND (
          b.fecha_alta IS NULL OR b.fecha_alta<c.fecha_inicio OR b.fecha_alta>CURRENT_DATE
          OR EXTRACT(YEAR FROM b.fecha_alta)<>c.anio OR b.fecha_baja<b.fecha_alta
          OR b.fecha_baja>CURRENT_DATE OR (b.estado='activo' AND b.fecha_baja IS NOT NULL)
          OR (b.estado='baja' AND b.fecha_baja IS NULL) OR b.estado NOT IN ('activo','baja'))"""),
    Check("R10", "Sin inscripciones activas duplicadas", """
        SELECT count(*) FROM (SELECT 1 FROM cef.inscripciones i JOIN cef.grupos g ON g.id=i.grupo_id
        WHERE g.ciclo_id=%s AND g.cueanexo IN ('220169000','220169100') AND i.estado='activo'
        GROUP BY i.grupo_id,i.alumno_id HAVING count(*)>1) s"""),
    Check("R11", "Sin asignaciones activas duplicadas ni roles exclusivos repetidos", """
        WITH seleccion AS (
          SELECT d.grupo_id,d.docente_cuil,d.rol FROM cef.docentes_grupo d
          JOIN cef.grupos g ON g.id=d.grupo_id WHERE g.ciclo_id=%s
          AND g.cueanexo IN ('220169000','220169100') AND d.estado='activo'
        ), errores AS (
          SELECT 1 FROM seleccion GROUP BY grupo_id,docente_cuil HAVING count(*)>1
          UNION ALL SELECT 1 FROM seleccion WHERE rol IN ('titular','interino')
          GROUP BY grupo_id,rol HAVING count(*)>1
        ) SELECT count(*) FROM errores"""),
    Check("R12", "Horarios y estado de grupos coherentes", """
        SELECT count(*) FROM cef.grupos g LEFT JOIN cef.turnos t ON t.id=g.turno_id
        WHERE g.ciclo_id=%s AND g.cueanexo IN ('220169000','220169100') AND (
          t.id IS NULL OR g.hora_fin<=g.hora_inicio
          OR g.hora_inicio<t.hora_desde_referencia OR g.hora_fin>t.hora_hasta_referencia
          OR g.cupo_maximo<1 OR (g.estado='activo' AND g.fecha_baja IS NOT NULL)
          OR (g.estado='baja' AND g.fecha_baja IS NULL) OR g.estado NOT IN ('activo','baja'))"""),
    Check("R13", "Inscripciones contenidas en un período del banco del mismo CEF y ciclo", """
        SELECT count(*) FROM cef.inscripciones i JOIN cef.grupos g ON g.id=i.grupo_id
        JOIN cef.ciclos c ON c.id=g.ciclo_id
        WHERE c.id=%s AND g.cueanexo IN ('220169000','220169100') AND (
          i.fecha_inscripcion IS NULL OR i.fecha_inscripcion<c.fecha_inicio OR i.fecha_inscripcion>CURRENT_DATE
          OR i.fecha_baja<i.fecha_inscripcion OR i.fecha_baja>CURRENT_DATE
          OR EXTRACT(YEAR FROM i.fecha_inscripcion)<>c.anio
          OR (i.estado='activo' AND (i.fecha_baja IS NOT NULL OR g.estado<>'activo'))
          OR (i.estado='baja' AND i.fecha_baja IS NULL) OR i.estado NOT IN ('activo','baja')
          OR NOT EXISTS (SELECT 1 FROM cef.alumnos_cef b WHERE b.ciclo_id=c.id
             AND b.cueanexo=g.cueanexo AND b.alumno_id=i.alumno_id
             AND b.fecha_alta<=i.fecha_inscripcion
             AND (b.fecha_baja IS NULL OR b.fecha_baja>=COALESCE(i.fecha_baja,i.fecha_inscripcion))
             AND (i.estado<>'activo' OR b.estado='activo')))"""),
    Check("R14", "Asignaciones contenidas en banco y con fechas y roles válidos", """
        SELECT count(*) FROM cef.docentes_grupo d JOIN cef.grupos g ON g.id=d.grupo_id
        JOIN cef.ciclos c ON c.id=g.ciclo_id
        WHERE c.id=%s AND g.cueanexo IN ('220169000','220169100') AND (
          d.fecha_desde IS NULL OR d.fecha_desde<c.fecha_inicio OR d.fecha_desde>CURRENT_DATE
          OR d.fecha_hasta<d.fecha_desde OR d.fecha_hasta>CURRENT_DATE
          OR EXTRACT(YEAR FROM d.fecha_desde)<>c.anio
          OR d.rol NOT IN ('titular','suplente','interino')
          OR (d.estado='activo' AND (d.fecha_hasta IS NOT NULL OR g.estado<>'activo'))
          OR (d.estado='baja' AND d.fecha_hasta IS NULL) OR d.estado NOT IN ('activo','baja')
          OR NOT EXISTS (SELECT 1 FROM cef.docentes_cef b WHERE b.ciclo_id=c.id
             AND b.cueanexo=g.cueanexo AND b.docente_cuil=d.docente_cuil
             AND b.fecha_alta<=d.fecha_desde
             AND (b.fecha_baja IS NULL OR b.fecha_baja>=COALESCE(d.fecha_hasta,d.fecha_desde))
             AND (d.estado<>'activo' OR b.estado='activo')))"""),
    Check("R15", "Jornadas dentro del ciclo y no futuras", """
        SELECT count(*) FROM cef.jornadas_asistencia j JOIN cef.grupos g ON g.id=j.grupo_id
        JOIN cef.ciclos c ON c.id=g.ciclo_id WHERE c.id=%s
        AND g.cueanexo IN ('220169000','220169100') AND (
          j.fecha<c.fecha_inicio OR j.fecha>CURRENT_DATE OR EXTRACT(YEAR FROM j.fecha)<>c.anio)"""),
    Check("R16", "Asistencia ligada al grupo correcto y a inscripción vigente", """
        SELECT count(*) FROM cef.asistencias a
        JOIN cef.jornadas_asistencia j ON j.id=a.jornada_id
        JOIN cef.grupos g ON g.id=j.grupo_id LEFT JOIN cef.inscripciones i ON i.id=a.inscripcion_id
        WHERE g.ciclo_id=%s AND g.cueanexo IN ('220169000','220169100') AND (
          i.id IS NULL OR i.grupo_id<>g.id OR j.fecha<i.fecha_inscripcion OR j.fecha>i.fecha_baja
          OR a.estado NOT IN ('presente','ausente','justificada'))"""),
    Check("R17", "Sin duplicados de asistencia por jornada e inscripción", """
        SELECT count(*) FROM (SELECT 1 FROM cef.asistencias a
        JOIN cef.jornadas_asistencia j ON j.id=a.jornada_id JOIN cef.grupos g ON g.id=j.grupo_id
        WHERE g.ciclo_id=%s AND g.cueanexo IN ('220169000','220169100')
        GROUP BY a.jornada_id,a.inscripcion_id HAVING count(*)>1) s"""),
    Check("R18", "Movimientos de asistencia con estados válidos y cambio efectivo", """
        SELECT count(*) FROM cef.asistencia_movimientos m JOIN cef.asistencias a ON a.id=m.asistencia_id
        JOIN cef.jornadas_asistencia j ON j.id=a.jornada_id JOIN cef.grupos g ON g.id=j.grupo_id
        WHERE g.ciclo_id=%s AND g.cueanexo IN ('220169000','220169100') AND (
          m.estado_nuevo=m.estado_anterior OR m.estado_nuevo NOT IN ('presente','ausente','justificada')
          OR (m.estado_anterior IS NOT NULL AND m.estado_anterior NOT IN ('presente','ausente','justificada')))"""),
    Check("R19", "Integridad global CEF: relaciones internas sin huérfanos",
        "SELECT count(*) FROM (" + " UNION ALL ".join(
            "SELECT 1 FROM cef." + child + " r LEFT JOIN cef." + parent +
            " p ON p.id=r." + col + " WHERE r." + col + " IS NOT NULL AND p.id IS NULL"
            for child,col,parent in CEF_FOREIGN_KEYS) + ") s"),
    Check("R20", "Claves foráneas declaradas CEF validadas", """
        SELECT count(*) FILTER (WHERE NOT k.convalidated),count(*)>0
        FROM pg_catalog.pg_constraint k JOIN pg_catalog.pg_namespace n
          ON n.oid=k.connamespace WHERE n.nspname='cef' AND k.contype='f'""", (0, True)),
    Check("R21", "Catálogos requeridos con filas", "SELECT count(*) FROM (" +
        " UNION ALL ".join("SELECT 1 WHERE NOT EXISTS (SELECT 1 FROM cef." + t + ")"
                           for t in CATALOGS) + ") s"),
    Check("R22", "Rangos, días y turnos de catálogo coherentes", """
        SELECT (SELECT count(*) FROM cef.rangos_etarios WHERE edad_hasta_dias<edad_desde_dias)
             + (SELECT count(*) FROM cef.dias_semana WHERE numero<1 OR numero>7)
             + (SELECT count(*) FROM cef.turnos WHERE hora_hasta_referencia<=hora_desde_referencia)"""),
]

META = {
    "target": """SELECT current_database()=%s,
         COALESCE(inet_server_addr()::text=%s, false), inet_server_port()=%s,
         current_setting('transaction_read_only')='on'""",
    "role": """SELECT rolsuper OR rolcreatedb OR rolcreaterole OR rolreplication OR rolbypassrls
         FROM pg_catalog.pg_roles WHERE rolname=current_user""",
    "privileges": """SELECT EXISTS (
         SELECT 1 FROM pg_catalog.pg_class c JOIN pg_catalog.pg_namespace n ON n.oid=c.relnamespace
         WHERE n.nspname NOT IN ('pg_catalog','information_schema') AND n.nspname NOT LIKE 'pg_toast%%'
         AND c.relkind IN ('r','p','v','m','f') AND (
           pg_catalog.pg_has_role(c.relowner,'USAGE')
           OR pg_catalog.has_table_privilege(c.oid,'INSERT,UPDATE,DELETE,TRUNCATE,TRIGGER')
           OR pg_catalog.has_any_column_privilege(c.oid,'INSERT,UPDATE')))""",
    "create": """SELECT pg_catalog.has_database_privilege(current_database(),'CREATE,TEMP')
         OR EXISTS (SELECT 1 FROM pg_catalog.pg_namespace n WHERE n.nspname NOT LIKE 'pg_%%'
                    AND pg_catalog.has_schema_privilege(n.oid,'CREATE'))""",
    "functions": """SELECT EXISTS (SELECT 1 FROM pg_catalog.pg_proc p
         JOIN pg_catalog.pg_namespace n ON n.oid=p.pronamespace
         WHERE n.nspname NOT IN ('pg_catalog','information_schema')
           AND pg_catalog.has_function_privilege(p.oid,'EXECUTE'))""",
    "tables": """SELECT count(*)=%s AND bool_and(c.relkind='r' AND NOT c.relrowsecurity
         AND NOT c.relhassubclass) FROM pg_catalog.pg_class c
         JOIN pg_catalog.pg_namespace n ON n.oid=c.relnamespace
         WHERE n.nspname='cef' AND c.relname=ANY(%s)""",
}


def certified(sql):
    # Sólo un registro cerrado de SELECT/CTE sin funciones de aplicación.
    bare = re.sub(r"'(?:''|[^'])*'", "''", sql)
    require(not any(x in bare for x in (";", "--", "/*", "$$")), "SQL_NO_CERTIFICADO")
    require(not re.search(r"\b(INSERT|UPDATE|DELETE|MERGE|CALL|COPY|TRUNCATE|DROP|ALTER|CREATE|INTO)\b",
                          bare, re.I), "SQL_NO_CERTIFICADO")
    require(sql.lstrip().upper().startswith(("SELECT ", "WITH ")), "SQL_NO_CERTIFICADO")
    functions = {name.lower() for name in re.findall(r'(?<![\w"])([A-Za-z_]\w*)\s*\(',bare)}
    allowed = {"count","coalesce","extract","current_database","current_setting",
        "inet_server_addr","inet_server_port","bool_and","has_table_privilege",
        "has_any_column_privilege","has_database_privilege","has_schema_privilege",
        "has_function_privilege","pg_has_role",
        "exists","any","in","not","and","or","where","as","filter","from","select"}
    require(not functions-allowed, "FUNCION_SQL_NO_PERMITIDA")


class Reader:
    """No tiene método de SQL libre ni operaciones de mutación."""
    def __init__(self, cursor):
        self._cursor = cursor
        self._queries = dict(META, **{c.code:c.sql for c in CHECKS})
    def get(self, code, parameters=()):
        require(code in self._queries, "CONSULTA_NO_REGISTRADA")
        sql = self._queries[code]
        certified(sql)
        self._cursor.execute(sql, parameters)
        result = self._cursor.fetchone()
        require(result is not None, "CONSULTA_SIN_RESULTADO_AGREGADO")
        return result


def audit(args):
    require(args.service and args.expect_db and args.expect_host and args.cycle,
            "SERVICIO_RO_Y_DESTINO_EXPLICITOS_REQUERIDOS")
    # IP literal para comparar destino real sin resolver DNS ni aceptar otro host.
    require(args.expect_host in ("127.0.0.1","::1") or
            re.fullmatch(r"\d{1,3}(?:\.\d{1,3}){3}",args.expect_host),
            "DIRECCION_IP_EXPLICITA_REQUERIDA")
    options = "-c default_transaction_read_only=on -c statement_timeout=5000 -c lock_timeout=1000 -c search_path=pg_catalog"
    try:
        import psycopg2 as driver
        version = 2
    except ModuleNotFoundError:
        try:
            import psycopg as driver
            version = 3
        except ModuleNotFoundError:
            raise Blocked("DRIVER_EXISTENTE_NO_DISPONIBLE") from None
    connection = None
    cursor = None
    try:
        # Servicio explícito; nunca settings Django, DSN/SQL libre o fallback a su usuario.
        connection = driver.connect(service=args.service, dbname=args.expect_db,
            host=args.expect_host, port=args.expect_port, connect_timeout=5, options=options)
        if version == 2:
            connection.set_session(readonly=True, autocommit=False, isolation_level="REPEATABLE READ")
        else:
            connection.autocommit = False
            connection.read_only = True
            connection.isolation_level = driver.IsolationLevel.REPEATABLE_READ
        cursor = connection.cursor()
        reader = Reader(cursor)
        require(all(reader.get("target",(args.expect_db,args.expect_host,args.expect_port))),
                "DESTINO_O_READ_ONLY_NO_CONFIRMADO")
        require(not reader.get("role")[0], "ROL_PRIVILEGIADO")
        require(not reader.get("privileges")[0], "ROL_CON_PRIVILEGIOS_DE_ESCRITURA")
        require(not reader.get("create")[0], "ROL_CON_CREATE_O_TEMP")
        require(not reader.get("functions")[0], "FUNCIONES_NO_CERTIFICADAS")
        require(reader.get("tables",(len(TABLES),list(TABLES)))[0],
                "TABLAS_FALTANTES_RLS_HERENCIA_O_FDW")
        output = []
        for check in CHECKS:
            params = (args.cycle,) if "%s" in check.sql else ()
            value = reader.get(check.code,params)
            require(all(type(v) in (int,bool) for v in value), "RESPUESTA_NO_AGREGADA")
            output.append({"codigo":check.code,
                "resultado":"PASS" if tuple(value)==check.expected else "FAIL",
                "descripcion":check.description, "cantidades_agregadas":list(value),
                "alcance":"auditoria_READ_ONLY_de_datos_existentes"})
            if check.code == "R01" and value != (1,):
                raise Blocked("CICLO_NO_EXISTENTE")
        output.append({"codigo":"R23","resultado":"NO_CUBIERTA",
            "descripcion":"Correspondencia lógica externa BNH/SGE sin FK: no se leen personas externas"})
        return output
    finally:
        try:
            if connection is not None:
                connection.rollback()
        finally:
            try:
                if cursor is not None:
                    cursor.close()
            finally:
                if connection is not None:
                    connection.close()
