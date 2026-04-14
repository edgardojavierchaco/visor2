import psycopg2
import os
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

def conectar_bd(request):
    try:
        connection = psycopg2.connect(
            host=os.getenv('POSTGRES_HOST'),
            user=os.getenv('POSTGRES_USER'),
            password=os.getenv('POSTGRES_PASSWORD'),
            database=os.getenv('DB_NAME2') 
        )
        return connection
    except psycopg2.Error:
        return None

def dashboard_matric_discapacidad(request):
    regiones = ["R.E. 1", "R.E. 2", "R.E. 3", "R.E. 4-A", "R.E. 4-B", "R.E. 5", "R.E. 6", "R.E. 7", "R.E. 8-A", "R.E. 8-B", "R.E. 9", "R.E. 10-A", "R.E. 10-B", "R.E. 10-C", "SUB. R.E. 1-A", "SUB. R.E. 1-B", "SUB. R.E. 2", "SUB. R.E. 3", "SUB. R.E. 5"]
    return render(request, 'reportes/dashboard_detalle_discapacidad_inicial.html', {'regions': regiones})

@csrf_exempt
def matric_disc_ajax(request):
    if request.method == 'POST':
        tvista = request.POST.get('Vista')
        if not tvista: return JsonResponse({'data': []})

        connection = conectar_bd(request)
        if not connection: return JsonResponse({'error': 'Error de conexión'}, status=500)
        cursor = connection.cursor()

        # BLINDAJE REGEX (Idéntico a Primaria): Limpia caracteres raros antes de sumar
        query = f"""
            SELECT 
                mc.cueanexo, p.nom_est, mc.sala, 
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
                p.ambito, p.sector, p.region_loc, p.departamento, p.localidad, 
                SUM(NULLIF(REGEXP_REPLACE(mc.total::text, '[^0-9]', '', 'g'), '')::integer) as total
            FROM public.{tvista} AS mc
            LEFT JOIN (
                SELECT cueanexo, nom_est, sector, ambito, region_loc, departamento, localidad
                FROM dblink('dbname=visualizador user=visualizador password=Estadisticas24 host=visoreducativochaco.com.ar port=5432',
                'SELECT DISTINCT cueanexo, nom_est, ambito, sector, departamento, localidad, region_loc FROM public.v_capa_unica_ofertas')
                AS padron(cueanexo varchar, nom_est varchar, ambito varchar, sector varchar, departamento varchar, localidad varchar, region_loc varchar)
            ) AS p ON mc.cueanexo = p.cueanexo
            WHERE 1=1
        """
        params = []
        for key, col in [('Cueanexo','mc.cueanexo'), ('Ambito','p.ambito'), ('Sector','p.sector'), ('Region','p.region_loc'), ('Departamento','p.departamento'), ('Localidad','p.localidad')]:
            val = request.POST.get(key)
            if val:
                query += f" AND {col} = %s"; params.append(val)

        query += " GROUP BY mc.cueanexo, p.nom_est, mc.sala, p.ambito, p.sector, p.region_loc, p.departamento, p.localidad ORDER BY mc.cueanexo;"
        
        try:
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            # Se agrega 'or 0' individualmente para prevenir caídas de Python si viene un campo Null desde Postgres
            data = [{
                'cueanexo': r[0], 
                'escuela': r[1] or 'Sin registrar', 
                'sala': r[2] or '',
                'visual': int(r[3] or 0) + int(r[4] or 0), 
                'auditiva': int(r[5] or 0) + int(r[6] or 0), 
                'intelectual': int(r[7] or 0),
                'motora': int(r[8] or 0) + int(r[9] or 0), 
                'tea': int(r[10] or 0), 
                'otros': int(r[11] or 0) + int(r[13] or 0), 
                'total': int(r[19] or 0)
            } for r in rows]

            connection.close()
            return JsonResponse({'data': data})
        except Exception as e:
            if connection:
                connection.close()
            return JsonResponse({'error': str(e)}, status=500)

    return JsonResponse({'error': 'Método no permitido'}, status=405)

# =====================================================================
# VISTAS ANTIGUAS (SISTEMA CLÁSICO) - También blindadas
# =====================================================================

def filtrado_matric_disc_ini_cueanexo(request):    
    return render(request, 'reportes/filter_matric_disc_ini_cueanexo.html')

@csrf_exempt
def filter_data_matric_disc_ini_cueanexo(request):
    if request.method == 'POST':     
        cueanexo = request.POST.get('Cueanexo')   
        ambito = request.POST.get('Ambito')
        sector = request.POST.get('Sector')
        region = request.POST.get('Region')
        departamento = request.POST.get('Departamento')
        localidad = request.POST.get('Localidad')        
        tvistamatricula = request.POST.get('Vista')

        opciones_validas = ['alumnos_cdiscapacidad_inicial', 'alumnos_cdiscapacidad_primaria', 'alumnos_cdiscapacidad_secundaria']

        if tvistamatricula not in opciones_validas:
            return render(request, 'error.html', {'mensaje': 'Opción de vista no válida'})

        opciones_descriptivas = {
            'alumnos_cdiscapacidad_inicial': 'Alumnos Nivel Inicial con discapacidad',
            'alumnos_cdiscapacidad_primaria': 'Alumnos Nivel Primario con discapacidad',
            'alumnos_cdiscapacidad_secundaria': 'Alumnos Nivel Secundario con discapacidad',
        }
        nvistamatricula = opciones_descriptivas.get(tvistamatricula, 'Alumnos con Discapacidad')
        
        connection = conectar_bd(request)
        if not connection:
            return render(request, 'error_conexion.html')

        cursor = connection.cursor()

        # BLINDAJE REGEX (Idéntico a Primaria)
        query = f"""
            SELECT 
                mc.cueanexo, p.nom_est, mc.sala, 
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
                p.ambito, p.sector, p.region_loc, p.departamento, p.localidad, 
                SUM(NULLIF(REGEXP_REPLACE(mc.total::text, '[^0-9]', '', 'g'), '')::integer) as total
            FROM 
                public.{tvistamatricula} AS mc
            LEFT JOIN (
                SELECT cueanexo, nom_est, sector, ambito, region_loc, departamento, localidad
                FROM dblink('dbname=visualizador user=visualizador password=Estadisticas24 host=visoreducativochaco.com.ar port=5432',
                'SELECT DISTINCT cueanexo, nom_est, ambito, sector, departamento, localidad, region_loc FROM public.v_capa_unica_ofertas')
                AS padron(cueanexo varchar, nom_est varchar, ambito varchar, sector varchar, departamento varchar, localidad varchar, region_loc varchar)
            ) AS p ON mc.cueanexo = p.cueanexo
            WHERE 1=1
        """

        parameters = []       
        if cueanexo: query += " AND mc.cueanexo = %s"; parameters.append(cueanexo) 
        if ambito: query += " AND p.ambito = %s"; parameters.append(ambito)
        if sector: query += " AND p.sector = %s"; parameters.append(sector)
        if region: query += " AND p.region_loc = %s"; parameters.append(region)
        if departamento: query += " AND p.departamento = %s"; parameters.append(departamento)
        if localidad: query += " AND p.localidad = %s"; parameters.append(localidad)

        query += " GROUP BY mc.cueanexo, p.nom_est, mc.sala, p.ambito, p.sector, p.region_loc, p.departamento, p.localidad ORDER BY mc.cueanexo;"

        cursor.execute(query, parameters)
        rows = cursor.fetchall()
        
        datos_encontrados = len(rows) > 0

        datamatriccueanexo = []
        for row in rows:
            datamatriccueanexo.append({
                'cueanexo':row[0], 'escuela':row[1], 'sala':row[2], 
                'ceguera': int(row[3] or 0), 'dism_visual': int(row[4] or 0), 
                'sordera': int(row[5] or 0), 'hipoacusia': int(row[6] or 0),
                'intelectual': int(row[7] or 0), 'motora_pura': int(row[8] or 0), 
                'neuromotora': int(row[9] or 0), 'tea': int(row[10] or 0), 
                'region_loc': row[16], 'localidad': row[18],
            })

        connection.close()

        if not datos_encontrados:
            return render(request, 'consulta_vacia.html')
        
        return render(request, 'reportes/matric_disc_ini_cueanexo.html', {
            'datamatriccueanexo': datamatriccueanexo, 'nvistamatricula': nvistamatricula, 'nrelevamiento':'RELEVAMIENTO 2024'
        })