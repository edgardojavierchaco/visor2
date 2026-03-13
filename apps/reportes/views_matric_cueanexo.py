import psycopg2
import os
import dotenv
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse

# ===================================================================== #
#  CONEXIÓN A BASE DE DATOS                                             #
# ===================================================================== #
def conectar_bd(request):
    try:
        connection = psycopg2.connect(
            host=os.getenv('POSTGRES_HOST'),
            user=os.getenv('POSTGRES_USER'),
            password=os.getenv('POSTGRES_PASSWORD'),
            database=os.getenv('DB_NAME2')  # Usando tu configuración correcta
        )
        return connection
    except psycopg2.Error as e:
        print(f"Error de conexión: {e}")
        return None

# ===================================================================== #
#  VISTA QUE CARGA EL HTML (AQUÍ CORREGIMOS EL ERROR DE DOCKER)         #
# ===================================================================== #
def filtrado_matric_cueanexo(request):
    """
    Renderiza el nuevo dashboard responsivo de Matrícula Detalle CUE-Anexo.
    """
    return render(request, 'reportes/dashboard_matricula_detalle_cueanexo.html')

# ===================================================================== #
#  MOTOR AJAX QUE ENVÍA LOS DATOS EN TIEMPO REAL A LA TABLA             #
# ===================================================================== #
@csrf_exempt
def ajax_matric_cueanexo(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Método no permitido'}, status=405)

    cueanexo     = request.POST.get('Cueanexo', '').strip()
    ambito       = request.POST.get('Ambito', '').strip()
    sector       = request.POST.get('Sector', '').strip()
    region       = request.POST.get('Region', '').strip()
    departamento = request.POST.get('Departamento', '').strip()
    localidad    = request.POST.get('Localidad', '').strip()
    tvistamatricula = request.POST.get('Vista', '').strip()

    opciones_validas = [            
        'matric_adulto_primaria', 'matric_cef', 'matric_comun_artistica',
        'matric_comun_inicial', 'matric_comun_primaria', 'matric_comun_secundaria'                    
    ]

    if tvistamatricula not in opciones_validas:
        return JsonResponse({'data': [], 'error': 'Opción de vista no válida'}, status=400)

    try:
        connection = conectar_bd(request)
        if not connection:
            return JsonResponse({'data': [], 'error': 'Error de conexión'}, status=500)

        cursor = connection.cursor()

        query = f"""
            SELECT 
                mc.cueanexo, 
                MAX(mc.escuela) AS escuela, 
                p.region_loc,
                p.ambito, 
                p.sector, 
                SUM(mc.total) AS total
            FROM 
                public.{tvistamatricula} AS mc
            LEFT JOIN (
                SELECT cueanexo, sector, ambito, region_loc, departamento, localidad
                FROM dblink(
                    'dbname=visualizador user=visualizador password=Estadisticas24 host=visoreducativochaco.com.ar port=5432',
                    'SELECT DISTINCT cueanexo, ambito, sector, departamento, localidad, region_loc FROM public.v_capa_unica_ofertas'
                ) AS padron(cueanexo character varying, ambito character varying, sector character varying, departamento character varying, localidad character varying, region_loc character varying)
            ) AS p ON mc.cueanexo = p.cueanexo
            WHERE 1=1
        """

        parameters = []       
        if cueanexo:
            query += " AND mc.cueanexo = %s"; parameters.append(cueanexo) 
        if ambito:
            query += " AND p.ambito = %s"; parameters.append(ambito)
        if sector:
            query += " AND p.sector = %s"; parameters.append(sector)
        if region:
            query += " AND p.region_loc = %s"; parameters.append(region)
        if departamento:
            query += " AND p.departamento = %s"; parameters.append(departamento)
        if localidad:
            query += " AND p.localidad = %s"; parameters.append(localidad)

        query += " GROUP BY mc.cueanexo, p.region_loc, p.ambito, p.sector ORDER BY mc.cueanexo;"

        cursor.execute(query, parameters)
        rows = cursor.fetchall()
        connection.close()

        data = []
        for row in rows:
            data.append({
                'cueanexo': row[0] if row[0] else '-',
                'escuela': row[1] if row[1] else '-',
                'region': row[2] if row[2] else '-',
                'ambito': row[3] if row[3] else '-',
                'sector': row[4] if row[4] else '-',
                'matricula': int(row[5]) if row[5] else 0
            })

        return JsonResponse({'data': data})

    except Exception as e:
        print(f"[ajax_matric_cueanexo ERROR] {str(e)}")
        return JsonResponse({'data': [], 'error': str(e)}, status=500)