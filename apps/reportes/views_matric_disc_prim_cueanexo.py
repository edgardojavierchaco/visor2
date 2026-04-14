import psycopg2
import os
import dotenv
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse

# Función para conectar a la base de datos
def conectar_bd(request):
    try:
        connection = psycopg2.connect(
            host=os.getenv('POSTGRES_HOST'),
            user=os.getenv('POSTGRES_USER'),
            password=os.getenv('POSTGRES_PASSWORD'),
            database=os.getenv('DB_NAME2') 
        )
        return connection
    except psycopg2.Error as e:
        return None

# Vista para mostrar la página/formulario inicialmente
def filtrado_matric_disc_prim_cueanexo(request):
    return render(request, 'reportes/dashboard_detalle_discapacidad_primaria.html')

# ═══════════════════════════════════════════════════════════════════════════
# NUEVA VISTA PARA EL DASHBOARD DINÁMICO (AJAX)
# ═══════════════════════════════════════════════════════════════════════════
@csrf_exempt
def matric_disc_prim_ajax(request):
    if request.method == 'POST':
        tvistamatricula = request.POST.get('Vista')
        
        # Validar si no hay modalidad seleccionada
        if not tvistamatricula:
            return JsonResponse({'data': []})

        cueanexo = request.POST.get('Cueanexo')   
        ambito = request.POST.get('Ambito')
        sector = request.POST.get('Sector')
        region = request.POST.get('Region')
        departamento = request.POST.get('Departamento')
        localidad = request.POST.get('Localidad')        
        
        connection = conectar_bd(request)
        if not connection:
            return JsonResponse({'error': 'Error de conexión a la base de datos'}, status=500)

        try:
            cursor = connection.cursor()

            # =================================================================================================
            # BLINDAJE DE DATOS: EXPRESIONES REGULARES (REGEX) PARA COLUMNAS NUMÉRICAS
            # =================================================================================================
            # DIAGNÓSTICO DEL PROBLEMA:
            # La base de datos almacena la cantidad de alumnos (ej: en la columna 'ceguera') en formato 
            # TEXTO (character varying). Por errores humanos al cargar los datos, estas celdas pueden 
            # contener espacios en blanco (" "), letras ("A"), o texto ("5 alumnos"). 
            # Intentar sumar esto directamente con SUM() generaba un Error 500 (DatatypeMismatch) en PostgreSQL.
            #
            # SOLUCIÓN IMPLEMENTADA (Regex a prueba de fallos):
            # Se aplica el siguiente filtro en cadena a cada columna matemática:
            # SUM(NULLIF(REGEXP_REPLACE(mc.columna::text, '[^0-9]', '', 'g'), '')::integer)
            # 
            # ¿CÓMO FUNCIONA ESTE FILTRO? (Ejemplo con el valor " 5 alumnos ")
            # 1. ::text         -> Asegura que el motor lea la celda como texto (" 5 alumnos ").
            # 2. REGEXP_REPLACE -> Busca cualquier carácter que NO sea un número ('[^0-9]') y lo elimina globalmente ('g').
            #                      (El valor " 5 alumnos " se convierte en el texto puro "5").
            #                      (Si el valor era " - ", se convierte en un texto vacío "").
            # 3. NULLIF         -> Si después de limpiar no quedó nada (''), lo convierte en un valor Nulo.
            #                      (Esto es crucial para que SUM() simplemente lo ignore en vez de fallar).
            # 4. ::integer      -> Convierte el texto numérico ultra-limpio ("5") en un número matemático real (5).
            # 5. SUM()          -> Ejecuta la suma total de manera segura.
            #
            # IMPORTANCIA A FUTURO:
            # Si en el futuro la base de datos se corrige y estas columnas pasan a ser de tipo Numérico Real (Integer),
            # este código NO se romperá. El paso 1 (::text) garantiza que cualquier valor (número o texto) 
            # ingrese al filtro, se estandarice y salga como número puro.
            # =================================================================================================
            
            query = f"""
                SELECT 
                    mc.cueanexo, 
                    p.nom_est,
                    mc.grado_anio, 
                    SUM(NULLIF(REGEXP_REPLACE(mc.ceguera::text, '[^0-9]', '', 'g'), '')::integer) as ceguera,
                    SUM(NULLIF(REGEXP_REPLACE(mc.dism_visual::text, '[^0-9]', '', 'g'), '')::integer) as dism_visual,
                    SUM(NULLIF(REGEXP_REPLACE(mc.sordera::text, '[^0-9]', '', 'g'), '')::integer) as sordera,
                    SUM(NULLIF(REGEXP_REPLACE(mc.hipoacusia::text, '[^0-9]', '', 'g'), '')::integer) as hipoacusia,
                    SUM(NULLIF(REGEXP_REPLACE(mc.intelectual::text, '[^0-9]', '', 'g'), '')::integer) as intelectual,
                    SUM(NULLIF(REGEXP_REPLACE(mc.motora_pura::text, '[^0-9]', '', 'g'), '')::integer) as motora_pura,
                    SUM(NULLIF(REGEXP_REPLACE(mc.neuromotora::text, '[^0-9]', '', 'g'), '')::integer) as neuromotora,
                    SUM(NULLIF(REGEXP_REPLACE(mc.espectro_autista::text, '[^0-9]', '', 'g'), '')::integer) as tea,
                    SUM(NULLIF(REGEXP_REPLACE(mc.mas_una_disc::text, '[^0-9]', '', 'g'), '')::integer) as mas_una_disc,
                    SUM(NULLIF(REGEXP_REPLACE(mc.sin_disc::text, '[^0-9]', '', 'g'), '')::integer) as sin_disc,
                    SUM(NULLIF(REGEXP_REPLACE(mc.otra_disc::text, '[^0-9]', '', 'g'), '')::integer) as otra_disc,                
                    p.ambito, 
                    p.sector, 
                    p.region_loc,
                    p.departamento,
                    p.localidad,
                    SUM(NULLIF(REGEXP_REPLACE(mc.total::text, '[^0-9]', '', 'g'), '')::integer) as total
                FROM 
                    public.{tvistamatricula} AS mc
                LEFT JOIN (
                    SELECT 
                        cueanexo, 
                        nom_est,
                        sector, 
                        ambito,
                        region_loc,
                        departamento,
                        localidad
                    FROM 
                        dblink(
                            'dbname=visualizador user=visualizador password=Estadisticas24 host=visoreducativochaco.com.ar port=5432',
                            'SELECT DISTINCT cueanexo, nom_est, ambito, sector, departamento, localidad, region_loc FROM public.v_capa_unica_ofertas'
                        ) AS padron(cueanexo character varying, nom_est character varying, ambito character varying, sector character varying, departamento character varying, localidad character varying, region_loc character varying)
                ) AS p
                ON mc.cueanexo = p.cueanexo
                WHERE 1=1
            """

            parameters = []       
            if cueanexo:
                query += " AND mc.cueanexo = %s"
                parameters.append(cueanexo) 
            if ambito:
                query += " AND p.ambito = %s"
                parameters.append(ambito)
            if sector:
                query += " AND p.sector = %s"
                parameters.append(sector)
            if region:
                query += " AND p.region_loc = %s"
                parameters.append(region)
            if departamento:
                query += " AND p.departamento = %s"
                parameters.append(departamento)
            if localidad:
                query += " AND p.localidad = %s"
                parameters.append(localidad)

            query += """
                GROUP BY mc.cueanexo, p.nom_est, mc.grado_anio, p.ambito, p.sector, p.region_loc, p.departamento, p.localidad
                ORDER BY mc.cueanexo, mc.grado_anio;
            """

            cursor.execute(query, parameters)
            rows = cursor.fetchall()

            datamatriccueanexo = []
            for row in rows:
                datamatriccueanexo.append({
                    'cueanexo': row[0] or '',
                    'escuela': row[1] or '',
                    'grado_anio': row[2] or '',                
                    'ceguera': int(row[3] or 0),
                    'dism_visual': int(row[4] or 0),
                    'sordera': int(row[5] or 0),
                    'hipoacusia': int(row[6] or 0),
                    'intelectual': int(row[7] or 0),
                    'motora_pura': int(row[8] or 0),
                    'neuromotora': int(row[9] or 0),
                    'tea': int(row[10] or 0),
                    'mas_una_disc': int(row[11] or 0),
                    'sin_disc': int(row[12] or 0),
                    'otra_disc': int(row[13] or 0),
                    'region_loc': row[16] or '',
                    'localidad': row[18] or '',
                    'total': int(row[19] or 0)
                })

            connection.close()
            return JsonResponse({'data': datamatriccueanexo})

        except Exception as e:
            if connection:
                connection.close()
            return JsonResponse({'error': str(e)}, status=500)

    return JsonResponse({'data': []})

# ═══════════════════════════════════════════════════════════════════════════
# VISTA VIEJA (También corregida para que no crashee por seguridad)
# ═══════════════════════════════════════════════════════════════════════════
@csrf_exempt
def filter_data_matric_disc_prim_cueanexo(request):
    if request.method == 'POST':     
        cueanexo = request.POST.get('Cueanexo')   
        ambito = request.POST.get('Ambito')
        sector = request.POST.get('Sector')
        region = request.POST.get('Region')
        departamento = request.POST.get('Departamento')
        localidad = request.POST.get('Localidad')        

        opciones_validas = [
            'alumnos_cdiscapacidad_inicial',
            'alumnos_cdiscapacidad_primaria',
            'alumnos_cdiscapacidad_secundaria'                  
        ]

        tvistamatricula = request.POST.get('Vista')

        if tvistamatricula not in opciones_validas:
            return render(request, 'error.html', {'mensaje': 'Opción de vista no válida'})

        opciones_descriptivas = {
            'alumnos_cdiscapacidad_inicial': 'Alumnos Nivel Incial con discapacidad',
            'alumnos_cdiscapacidad_primaria': 'Alumnos Nivel Primario con discapacidad',
            'alumnos_cdiscapacidad_secundaria': 'Alumnos Nivel Secundario con discapacidad',
        }
        nvistamatricula = opciones_descriptivas.get(tvistamatricula, 'Alumnos Nivel Incial con Discapacidad')
        
        connection = conectar_bd(request)
        if not connection:
            return render(request, 'error_conexion.html')

        cursor = connection.cursor()

        query = f"""
            SELECT 
                mc.cueanexo, 
                p.nom_est,
                mc.grado_anio, 
                SUM(NULLIF(REGEXP_REPLACE(mc.ceguera::text, '[^0-9]', '', 'g'), '')::integer) as ceguera,
                SUM(NULLIF(REGEXP_REPLACE(mc.dism_visual::text, '[^0-9]', '', 'g'), '')::integer) as dism_visual,
                SUM(NULLIF(REGEXP_REPLACE(mc.sordera::text, '[^0-9]', '', 'g'), '')::integer) as sordera,
                SUM(NULLIF(REGEXP_REPLACE(mc.hipoacusia::text, '[^0-9]', '', 'g'), '')::integer) as hipoacusia,
                SUM(NULLIF(REGEXP_REPLACE(mc.intelectual::text, '[^0-9]', '', 'g'), '')::integer) as intelectual,
                SUM(NULLIF(REGEXP_REPLACE(mc.motora_pura::text, '[^0-9]', '', 'g'), '')::integer) as motora_pura,
                SUM(NULLIF(REGEXP_REPLACE(mc.neuromotora::text, '[^0-9]', '', 'g'), '')::integer) as neuromotora,
                SUM(NULLIF(REGEXP_REPLACE(mc.espectro_autista::text, '[^0-9]', '', 'g'), '')::integer) as tea,
                SUM(NULLIF(REGEXP_REPLACE(mc.mas_una_disc::text, '[^0-9]', '', 'g'), '')::integer) as mas_una_disc,
                SUM(NULLIF(REGEXP_REPLACE(mc.sin_disc::text, '[^0-9]', '', 'g'), '')::integer) as sin_disc,
                SUM(NULLIF(REGEXP_REPLACE(mc.otra_disc::text, '[^0-9]', '', 'g'), '')::integer) as otra_disc,                
                p.ambito, 
                p.sector, 
                p.region_loc,
                p.departamento,
                p.localidad,
                SUM(NULLIF(REGEXP_REPLACE(mc.total::text, '[^0-9]', '', 'g'), '')::integer) as total
            FROM 
                public.{tvistamatricula} AS mc
            LEFT JOIN (
                SELECT 
                    cueanexo, 
                    nom_est,
                    sector, 
                    ambito,
                    region_loc,
                    departamento,
                    localidad
                FROM 
                    dblink(
                        'dbname=visualizador user=visualizador password=Estadisticas24 host=visoreducativochaco.com.ar port=5432',
                        'SELECT DISTINCT cueanexo, nom_est, ambito, sector, departamento, localidad, region_loc FROM public.v_capa_unica_ofertas'
                    ) AS padron(cueanexo character varying, nom_est character varying, ambito character varying, sector character varying, departamento character varying, localidad character varying, region_loc character varying)
            ) AS p
            ON mc.cueanexo = p.cueanexo
            WHERE 1=1
        """

        parameters = []       
        if cueanexo:
            query += " AND mc.cueanexo = %s"
            parameters.append(cueanexo) 
        if ambito:
            query += " AND p.ambito = %s"
            parameters.append(ambito)
        if sector:
            query += " AND p.sector = %s"
            parameters.append(sector)
        if region:
            query += " AND p.region_loc = %s"
            parameters.append(region)
        if departamento:
            query += " AND p.departamento = %s"
            parameters.append(departamento)
        if localidad:
            query += " AND p.localidad = %s"
            parameters.append(localidad)

        query += """
            GROUP BY mc.cueanexo, p.nom_est, mc.grado_anio, p.ambito, p.sector, p.region_loc, p.departamento, p.localidad
            ORDER BY mc.cueanexo;
        """

        cursor.execute(query, parameters)
        rows = cursor.fetchall()
        datos_encontrados = len(rows)>0

        datamatriccueanexo = []
        for row in rows:
            datamatriccueanexo.append({
                'cueanexo':row[0],
                'escuela':row[1],
                'grado_anio':row[2],                
                'ceguera': int(row[3] or 0),
                'dism_visual': int(row[4] or 0),
                'sordera': int(row[5] or 0),
                'hipoacusia': int(row[6] or 0),
                'intelectual': int(row[7] or 0),
                'motora_pura': int(row[8] or 0),
                'neuromotora': int(row[9] or 0),
                'tea': int(row[10] or 0),
                'region_loc': row[16],
                'localidad': row[18],
            })

        connection.close()

        if not datos_encontrados:
            return render(request, 'consulta_vacia.html')
        
        return render(request, 'reportes/dashboard_detalle_discapacidad_primaria.html', {
            'datamatriccueanexo': datamatriccueanexo, 
            'nvistamatricula': nvistamatricula, 
            'nrelevamiento':'RELEVAMIENTO 2024'
        })