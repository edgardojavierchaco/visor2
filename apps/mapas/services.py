import os
import json
import psycopg2
from django.db import connection

class OfertaEducativaService:
    
    @staticmethod
    def obtener_conexion(usar_db_matricula=False):
        """
        Establece conexión dinámica según el destino.
        - False: Usa DB_NAME1 (Padrón/Planes).
        - True: Usa POSTGRES_DB (Matrícula/Funciones).
        """
        try:
            db_target = os.getenv('POSTGRES_DB') if usar_db_matricula else os.getenv('DB_NAME1')
            conn = psycopg2.connect(
                host=os.getenv('POSTGRES_HOST'),
                user=os.getenv('POSTGRES_USER'),
                password=os.getenv('POSTGRES_PASSWORD'),
                database=db_target,
                connect_timeout=5
            )
            with conn.cursor() as cursor:
                cursor.execute("SET search_path TO funcion, public;")
            return conn
        except Exception as e:
            print(f"Error de conexión a DB {os.getenv('POSTGRES_DB') if usar_db_matricula else os.getenv('DB_NAME1')}: {e}")
            raise e

    @staticmethod
    def filtrar_ofertas_mapa(params):
        """Lógica completa de filtrado para marcadores en el mapa interactivo."""
        query = """
            SELECT cueanexo, lat, long, nom_est, oferta, ambito, sector, 
                   region_loc, calle, numero, localidad, acronimo, apellido_resp, nombre_resp, resploc_telefono, resploc_email 
            FROM v_capa_unica_ofertas_ant WHERE 1=1
        """
        sql_params = []
        
        filtros = {
            'Cueanexo': ('AND cueanexo = %s', None),
            'Ambito': ('AND ambito = %s', None),
            'Sector': ('AND sector = %s', None),
            'Region': ('AND region_loc = %s', None),
            'Departamento': ('AND departamento = %s', None),
            'Localidad': ('AND localidad = %s', None),
            'Cui': ('AND cui_loc = %s', None),
            'Oferta': ('AND oferta LIKE %s', lambda x: f"{x}%"),
            'nomest': ('AND nom_est ILIKE %s', lambda x: f"%{x}%"),
            'Modalidad': ('AND acronimo ILIKE %s', lambda x: f"%{x}%"),
        }

        for key, (sql_part, transform) in filtros.items():
            val = params.get(key)
            if val:
                query += f" {sql_part}"
                sql_params.append(transform(val) if transform else val)

        # Usamos la conexión por defecto de Django para el mapa
        with connection.cursor() as cursor:
            cursor.execute(query, sql_params)
            rows = cursor.fetchall()
            col_names = [desc[0] for desc in cursor.description]

        # Limpieza de coordenadas para evitar errores en Leaflet
        filtered_rows = [
            row for row in rows 
            if row[1] not in (0, '', None) and row[2] not in (0, '', None)
        ]
        
        return {
            'data_json': json.dumps(filtered_rows),
            'column_names_json': json.dumps(col_names)
        }

    @classmethod
    def obtener_detalle_completo(cls, cueanexo, oferta_rec):
        """Coordina consultas seguras entre dos bases de datos distintas."""
        
        # --- PARTE 1: Datos de Padrón y Planes (DB_NAME1) ---
        conn_padron = cls.obtener_conexion(usar_db_matricula=False)
        try:
            with conn_padron.cursor() as cursor:
                # 1. Datos Institucionales con blindaje de columnas (ej. categoria)
                inst = cls._safe_query(cursor, "public.padron_ofertas", {
                    'columnas': ['categoria', 'jornada', 'oferta', 'id_establecimiento', 'ref_loc', 'calle', 
                               'numero', 'anexo', 'apellido_resp', 'nombre_resp', 'resploc_telefono', 
                               'resploc_email', 'sup_tecnico', 'email_suptecnico', 'tel_suptecnico', 
                               'cui_loc', 'cuof_loc'],
                    'where': "cueanexo = %s",
                    'params': [cueanexo]
                })

                # 2. Planes de estudio con blindaje de tabla (v_planes_estudio)
                planes = cls._safe_query(cursor, "v_planes_estudio", {
                    'columnas': ['titulo', 'orientacion'],
                    'where': "CONCAT(cue,anexo) = %s AND estado_ofertalocal = 'Activo'",
                    'params': [cueanexo]
                })

                # 3. Anexos y Ofertas (Tablas base)
                anexos = cls._safe_query(cursor, "padron_ofertas", {
                    'columnas': ['anexo', 'calle', 'numero', 'estado_loc'],
                    'where': "id_establecimiento IN (SELECT id_establecimiento FROM padron_ofertas WHERE cueanexo = %s) AND estado_loc = 'Activo'",
                    'params': [cueanexo],
                    'distinct': True
                })
                
                ofertas_lista = cls._safe_query(cursor, "padron_ofertas", {
                    'columnas': ['cueanexo', 'oferta', 'est_oferta'],
                    'where': "cueanexo = %s AND est_oferta = 'Activo'",
                    'params': [cueanexo]
                })
        finally:
            conn_padron.close()

        # --- PARTE 2: Datos de Matrícula (POSTGRES_DB) ---
        matricula_detalle = []
        conn_mat = cls.obtener_conexion(usar_db_matricula=True)
        try:
            with conn_mat.cursor() as cursor:
                matricula_detalle = cls._obtener_matricula_especifica(cursor, cueanexo, oferta_rec)
        finally:
            conn_mat.close()
            
        return inst, planes, anexos, ofertas_lista, matricula_detalle

    @classmethod
    def _safe_query(cls, cursor, table_name, config):
        """Ejecuta consultas verificando existencia de tablas y columnas."""
        try:
            cursor.execute("SELECT to_regclass(%s)", [table_name])
            if cursor.fetchone()[0] is None:
                return []

            # Filtrar columnas si la tabla es padron_ofertas
            cols_finales = config['columnas']
            if 'padron_ofertas' in table_name:
                cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'padron_ofertas'")
                existentes = [r[0] for r in cursor.fetchall()]
                cols_finales = [c for c in config['columnas'] if c in existentes]

            if not cols_finales: return []

            distinct = "DISTINCT" if config.get('distinct') else ""
            query = f"SELECT {distinct} {', '.join(cols_finales)} FROM {table_name} WHERE {config['where']}"
            cursor.execute(query, config['params'])
            return cls._dict_fetchall(cursor)
        except Exception as e:
            print(f"Aviso SafeQuery ({table_name}): {e}")
            cursor.execute("ROLLBACK")
            return []

    @staticmethod
    def _obtener_matricula_especifica(cursor, cueanexo, oferta_rec):
        """Maneja las funciones del esquema funcion con normalización de strings."""
        mapeo = {
            'Adultos - Primaria': 'Adultos - Primaria ',
            'Adultos - Secundaria Completa': 'Adultos - Secundaria Completa',
            'Común - Jardín de Infantes': 'Común - Jardín de infantes ',
            'Común - Jardín maternal': 'Común - Jardín maternal ',
            'Común - Primaria de 7 años': 'Común - Primaria de 7 años ',
            'Común - Secundaria Completa req. 7 años': 'Común - Secundaria Completa req. 7 años ',
        }
        oferta_norm = mapeo.get(oferta_rec, oferta_rec.strip() if oferta_rec else "")

        queries = {
            'Adultos - Primaria ': """
                SELECT cueanexo, turno, tipo_secc AS tipo, nom_secc as seccion, grado AS Ciclo, total, 
                edad_menos_13 AS "Edad menor 13", SUM(edad_13 + edad_14 + edad_15 + edad_16 + edad_17 + edad_18) AS "Edad 13-18",
                SUM(edad_19+edad_20_a_24+edad_25_a_29) as "Edad 19-29", SUM(edad_30_a_34+edad_35_a_39) as "Edad 30-39",
                SUM(edad_40_a_44+edad_45_a_49) as "Edad 40-49", SUM(edad_50_a_54+edad_55_mas) as "Edad 50 o más"
                FROM funcion.visor_matric_adulto_primaria('ra_carga2024')
                WHERE cueanexo = %s GROUP BY 1,2,3,4,5,6,7 ORDER BY 5; """,
            'Adultos - Secundaria Completa': """
                SELECT cueanexo, turno, grado as Año, tipo_div AS tipo, nom_secc as seccion, total, 
                sum(edad_14+edad_15+edad_16+edad_17) AS "Edad 14-17", sum(edad_18+edad_19+edad_20+edad_21+edad_22+edad_23+edad_24+edad_25_a_29) as "Edad 18-29",
                sum(edad_30_a_34+edad_35_a_39) as "Edad 30-39", sum(edad_40_a_44+edad_45_a_49) as "Edad 40-49", sum(edad_50_a_54+edad_50_y_mas) as "Edad 50 o más"
                FROM funcion.visor_matric_adulto_secundaria('ra_carga2024')
                WHERE cueanexo = %s GROUP BY 1,2,3,4,5,6 ORDER BY 3; """,
            'Común - Jardín de infantes ': """
                SELECT cueanexo, turno, grado as sala, tipo_secc AS tipo, nom_secc as seccion, total,
                menos_1_año as "Menos 1 año", un_año as "1 año", dos_años as "2 años", tres_años as "3 años",
                cuatro_años as "4 Años", cinco_años as "5 años", seis_años as "6 años", total_disc as "Discapacitados"
                FROM funcion.visor_matric_comun_inicial('ra_carga2024')
                WHERE cueanexo = %s GROUP BY 1,2,3,4,5,6,7,8,9,10,11,12,13,14 ORDER BY 3; """,
            'Común - Primaria de 7 años ': """
                SELECT cueanexo, turno, grado, tipo_secc AS tipo, nom_secc as seccion, total,
                edad_5 as "5 años", edad_6 as "6 años", edad_7 as "7 años", edad_8 as "8 años", edad_9 as "9 Años",
                edad_10 as "10 años", edad_11 as "11 años", edad_12 as "12 años", sum(edad_13+edad_14+edad_15+edad_16+edad_17+edad_18_y_mas) as "13+ años",
                tot_discapacidad as "Discapacitados"
                FROM funcion.visor_matric_comun_primaria('ra_carga2024')
                WHERE cueanexo = %s GROUP BY 1,2,3,4,5,6,7,8,9,10,11,12,13,14,16 ORDER BY 3; """,
            'Común - Secundaria Completa req. 7 años ': """
                SELECT cueanexo, turno, grado as año, tipo_div AS tipo, nom_secc as seccion, total,
                edad_12 as "12 años", edad_13 as "13 años", edad_14 as "14 años", edad_15 as "15 años", edad_16 as "16 Años",
                edad_17 as "17 años", edad_18 as "18 años", edad_19 as "19 años", sum(edad_20_24+edad_25_y_mas) as "20+ años",
                total_disc as "Discapacitados"
                FROM funcion.visor_matric_comun_secundaria('ra_carga2024')
                WHERE cueanexo = %s GROUP BY 1,2,3,4,5,6,7,8,9,10,11,12,13,14,16 ORDER BY 3; """
        }
        queries['Común - Jardín maternal '] = queries['Común - Jardín de infantes ']
        
        sql = queries.get(oferta_norm)
        if not sql: return {'encabezados': [], 'valores': []}

        try:
            cursor.execute(sql, [cueanexo])
            return {'encabezados': [d[0] for d in cursor.description], 'valores': cursor.fetchall()}
        except Exception as e:
            cursor.execute("ROLLBACK")
            return {'encabezados': ['Error'], 'valores': [[str(e)]]}

    @staticmethod
    def _dict_fetchall(cursor):
        if not cursor.description: return []
        columns = [col[0] for col in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]