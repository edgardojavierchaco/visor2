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

def dashboard_matric_discapacidad_secundaria(request):
    regiones = [
        "R.E. 1", "R.E. 2", "R.E. 3", "R.E. 4-A", "R.E. 4-B", 
        "R.E. 5", "R.E. 6", "R.E. 7", "R.E. 8-A", "R.E. 8-B", 
        "R.E. 9", "R.E. 10-A", "R.E. 10-B", "R.E. 10-C",
        "SUB. R.E. 1-A", "SUB. R.E. 1-B", "SUB. R.E. 2", 
        "SUB. R.E. 3", "SUB. R.E. 5"
    ]
    return render(request, 'reportes/dashboard_detalle_discapacidad_secundaria.html', {'regions': regiones})

@csrf_exempt
def matric_disc_sec_ajax(request):
    if request.method == 'POST':
        tvista = request.POST.get('Vista')
        cueanexo = request.POST.get('Cueanexo')
        region = request.POST.get('Region')
        departamento = request.POST.get('Departamento')
        localidad = request.POST.get('Localidad')
        ambito = request.POST.get('Ambito')  
        sector = request.POST.get('Sector')  

        if not tvista:
            return JsonResponse({'data': []})

        connection = conectar_bd(request)
        if not connection:
            return JsonResponse({'error': 'Error de conexión a la base de datos'})

        cursor = connection.cursor()

        # =================================================================================================
        # BLINDAJE DE DATOS: EXPRESIONES REGULARES (REGEX) PARA COLUMNAS NUMÉRICAS
        # =================================================================================================
        # Esto reemplaza al antiguo TRIM() y previene los errores 500 (DatatypeMismatch) 
        # garantizando que solo se sumen números puros, ignorando letras o caracteres basura.
        
        query = f"""
            SELECT 
                mc.cueanexo, 
                p.nom_est,                
                SUM(NULLIF(REGEXP_REPLACE(mc.ceguera::text, '[^0-9]', '', 'g'), '')::integer) as ceguera,
                SUM(NULLIF(REGEXP_REPLACE(mc.dism_visual::text, '[^0-9]', '', 'g'), '')::integer) as dism_visual,
                SUM(NULLIF(REGEXP_REPLACE(mc.sordera::text, '[^0-9]', '', 'g'), '')::integer) as sordera,
                SUM(NULLIF(REGEXP_REPLACE(mc.hipoacusia::text, '[^0-9]', '', 'g'), '')::integer) as hipoacusia,
                SUM(NULLIF(REGEXP_REPLACE(mc.intelectual::text, '[^0-9]', '', 'g'), '')::integer) as intelectual,
                SUM(NULLIF(REGEXP_REPLACE(mc.motora_pura::text, '[^0-9]', '', 'g'), '')::integer) as motora_pura,
                SUM(NULLIF(REGEXP_REPLACE(mc.neuromotora::text, '[^0-9]', '', 'g'), '')::integer) as neuromotora,
                SUM(NULLIF(REGEXP_REPLACE(mc.espectro_autista::text, '[^0-9]', '', 'g'), '')::integer) as tea,                               
                p.ambito, 
                p.sector, 
                p.region_loc,
                p.departamento,
                p.localidad,
                SUM(NULLIF(REGEXP_REPLACE(mc.total::text, '[^0-9]', '', 'g'), '')::integer) as total
            FROM public.{tvista} AS mc
            LEFT JOIN (
                SELECT cueanexo, nom_est, sector, ambito, region_loc, departamento, localidad
                FROM dblink('dbname=visualizador user=visualizador password=Estadisticas24 host=visoreducativochaco.com.ar port=5432',
                'SELECT DISTINCT cueanexo, nom_est, ambito, sector, departamento, localidad, region_loc FROM public.v_capa_unica_ofertas')
                AS padron(cueanexo character varying, nom_est character varying, ambito character varying, sector character varying, departamento character varying, localidad character varying, region_loc character varying)
            ) AS p ON mc.cueanexo = p.cueanexo
            WHERE 1=1
        """

        parameters = []       
        if cueanexo:
            query += " AND mc.cueanexo = %s"
            parameters.append(cueanexo) 
        if ambito:
            query += " AND UPPER(TRIM(p.ambito)) = UPPER(TRIM(%s))"
            parameters.append(ambito)
        if sector:
            query += " AND UPPER(TRIM(p.sector)) = UPPER(TRIM(%s))"
            parameters.append(sector)
        if region:
            query += " AND UPPER(TRIM(p.region_loc)) = UPPER(TRIM(%s))"
            parameters.append(region)

        if departamento:
            depto_val = departamento.upper().strip()
            if depto_val == 'FRAY JUSTO SANTA MARIA DE ORO':
                query += " AND UPPER(TRIM(p.departamento)) IN ('FRAY JUSTO SANTA MARIA DE ORO', 'FRAY JUSTO SANTA M. DE ORO', 'FRAY JUSTO SANTA M DE ORO')"
            elif depto_val == 'MAYOR LUIS J. FONTANA':
                query += " AND UPPER(TRIM(p.departamento)) IN ('MAYOR LUIS J. FONTANA', 'MAYOR LUIS J FONTANA', 'MAYOR LUIS J.FONTANA')"
            elif depto_val == 'PRESIDENCIA DE LA PLAZA':
                query += " AND UPPER(TRIM(p.departamento)) IN ('PRESIDENCIA DE LA PLAZA', 'PCIA. DE LA PLAZA', 'PCIA.DE LA PLAZA', 'PCIA,DE LA PLAZA')"
            elif 'HIGGINS' in depto_val:
                query += " AND UPPER(TRIM(p.departamento)) LIKE '%HIGGINS%'"
            else:
                query += " AND UPPER(TRIM(p.departamento)) = %s"
                parameters.append(depto_val)

        if localidad:
            loc_val = localidad.upper().strip()
            if loc_val == 'MISION NUEVA POMPEYA':
                query += " AND UPPER(TRIM(p.localidad)) IN ('MISION NUEVA POMPEYA', 'NUEVA POMPEYA')"
            else:
                query += " AND UPPER(TRIM(p.localidad)) = %s"
                parameters.append(loc_val)

        query += """
            GROUP BY mc.cueanexo, p.nom_est, p.ambito, p.sector, p.region_loc, p.departamento, p.localidad
            ORDER BY mc.cueanexo;
        """

        try:
            cursor.execute(query, parameters)
            rows = cursor.fetchall()
        except Exception as e:
            error_msg = str(e)
            print("Error SQL Secundaria:", error_msg)
            connection.close()
            return JsonResponse({'error': f'Error Postgres: {error_msg}'})

        data = []
        for row in rows:
            data.append({
                'cueanexo': row[0],
                'escuela': row[1] or 'Sin registrar',
                'visual': int(row[2] or 0) + int(row[3] or 0),
                'auditiva': int(row[4] or 0) + int(row[5] or 0),
                'intelectual': int(row[6] or 0),
                'motora': int(row[7] or 0) + int(row[8] or 0),
                'tea': int(row[9] or 0),
                'total': int(row[15] or 0)
            })

        connection.close()
        return JsonResponse({'data': data})
    
    return JsonResponse({'error': 'Método no permitido'})

# Funciones antiguas
def filtrado_matric_disc_sec_cueanexo(request):
    return render(request, 'reportes/filter_matric_disc_sec_cueanexo.html')

@csrf_exempt
def filter_data_matric_disc_sec_cueanexo(request):
    pass