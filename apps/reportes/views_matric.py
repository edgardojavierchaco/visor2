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
            database=os.getenv('POSTGRES_DB') 
        )
        return connection
    except psycopg2.Error as e:
        return None

# ===================================================================== #
#  VISTAS ORIGINALES DE RENDERIZADO                                     #
# ===================================================================== #
def filtrado_aborigen(request):
    return render(request, 'reportes/dashboard_reportes_aborigen.html')

def filtrado_comesp(request):
    return render(request, 'reportes/dashboard_reportes_comesp.html')

def filtrado_snu(request):
    return render(request, 'reportes/dashboard_reportes_snu.html')

# ===================================================================== #
#  FUNCIONES TRADICIONALES ORIGINALES (Para que no tire error Docker)   #
# ===================================================================== #
@csrf_exempt
def filter_data_aborigen(request):
    if request.method == 'POST':
        cueanexo = request.POST.get('Cueanexo')
        ambito = request.POST.get('Ambito')
        sector = request.POST.get('Sector')
        region = request.POST.get('Region')
        departamento = request.POST.get('Departamento')
        localidad = request.POST.get('Localidad')
        relevamiento = request.POST.get('Relevamiento')

        opciones_validas = [
            'visor_matric_aborigen_adulto_primaria',
            'visor_matric_aborigen_adulto_secundaria',
            'visor_matric_aborigen_comun_inicial',
            'visor_matric_aborigen_comun_primaria',
            'visor_matric_aborigen_comun_secundaria',
            'visor_matric_aborigen_comun_snu',
            'visor_matric_aborigen_educacion_especial'            
        ]

        tvistaaborigen = request.POST.get('Vista')

        if tvistaaborigen not in opciones_validas:
            return render(request, 'error.html', {'mensaje': 'Opción de vista no válida'})

        opciones_descriptivas = {
            'visor_matric_aborigen_adulto_primaria': 'Aborigen Adulto Primaria',
            'visor_matric_aborigen_adulto_secundaria': 'Aborigen Adulto Secundaria',
            'visor_matric_aborigen_comun_inicial': 'Aborigen Común Inicial',
            'visor_matric_aborigen_comun_primaria': 'Aborigen Común Primaria',
            'visor_matric_aborigen_comun_secundaria': 'Aborigen Común Secundaria',
            'visor_matric_aborigen_comun_snu': 'Aborigen Común SNU',
            'visor_matric_aborigen_educacion_especial': 'Aborigen Educación Especial',            
        }
        nvistaaborigen = opciones_descriptivas.get(tvistaaborigen, 'Aborigen Educación Especial')

        opciones_relevamiento={      
            'ra_carga2019':'Relevamiento 2019',
            'ra_carga2020':'Relevamiento 2020',
            'ra_carga2021':'Relevamiento 2021',                  
            'ra_carga2022':'Relevamiento 2022',  
            'ra_carga2023':'Relevamiento 2023',  
            'ra_carga2024':'Relevamiento 2024',   
            'ra_carga2025':'Relevamiento 2025',       
        }
        nrelevamiento=opciones_relevamiento.get(relevamiento,'Relevamiento 2022')

        connection = conectar_bd(request)
        if not connection:
            return render(request, 'error_conexion.html')

        cursor = connection.cursor()

        query = f"""
            SELECT                
                SUM(CAST(total AS INT)) AS total,
                SUM(CAST(tot_var AS INT)) AS tot_var                               
            FROM funcion.{tvistaaborigen}('{relevamiento}')  
            LEFT JOIN (
                    SELECT * FROM dblink (
                        'dbname=Padron user=visualizador password=Estadisticas24 host=visoreducativochaco.com.ar port=5432',
                        'SELECT distinct cueanexo, nom_est, nro_est, anio_creac_establec, fecha_creac_establec, region, udt, cui, cua, cuof, sector, ambito, ref_loc, calle, numero, localidad, departamento, cod_postal, categoria, estado_est, estado_loc, telefono_cod_area, telefono_nro, per_funcionamiento, email_loc FROM padron'
                    ) AS padron (
                        cueanexo varchar, nom_est varchar, nro_est varchar, anio_creac_establec varchar,
                        fecha_creac_establec varchar, region varchar, udt varchar, cui varchar, cua varchar, cuof varchar, sector varchar, ambito varchar, ref_loc varchar,
                        calle varchar, numero varchar, localidad varchar, departamento varchar, cod_postal varchar, categoria varchar, estado_est varchar, estado_loc varchar,
                        telefono_cod_area varchar, telefono_nro varchar, per_funcionamiento varchar, email_loc varchar
                    )
                ) AS p using (cueanexo)       
            WHERE 1=1           
        """
        parameters = []
        if cueanexo: query += " AND p.cueanexo = %s"; parameters.append(cueanexo)
        if ambito: query += " AND p.ambito = %s"; parameters.append(ambito)
        if sector: query += " AND p.sector = %s"; parameters.append(sector)
        if region: query += " AND p.region = %s"; parameters.append(region)
        if departamento: query += " AND p.departamento = %s"; parameters.append(departamento)
        if localidad: query += " AND p.localidad = %s"; parameters.append(localidad)

        cursor.execute(query, parameters)
        rows = cursor.fetchall()
        datos_encontrados = len(rows)>0

        dataaborigen = []
        for row in rows:
            dataaborigen.append({
                'total': int(row[0]) if row[0] else 0,
                'tot_var': int(row[1]) if row[1] else 0
            })

        connection.close()

        if not datos_encontrados:
            return render(request, 'consulta_vacia.html')
        
        return render(request, 'reportes/aborigenes.html', {'dataaborigen': dataaborigen, 'nvistaaborigen': nvistaaborigen, 'nrelevamiento':nrelevamiento})

@csrf_exempt
def filter_data_comesp(request):
    if request.method == 'POST':
        cueanexo = request.POST.get('Cueanexo')
        ambito = request.POST.get('Ambito')
        sector = request.POST.get('Sector')
        region = request.POST.get('Region')
        departamento = request.POST.get('Departamento')
        localidad = request.POST.get('Localidad')
        relevamiento = request.POST.get('Relevamiento')

        opciones_validas = [
            'visor_matric_adulto_fp', 'visor_matric_adulto_primaria', 'visor_matric_adulto_secundaria',
            'visor_matric_comun_inicial', 'visor_matric_comun_primaria', 'visor_matric_comun_secundaria',            
            'visor_matric_especial_ed_temprana', 'visor_matric_especial_inicial', 'visor_matric_especial_primaria',           
        ]
        tvistacomesp = request.POST.get('Vista')
        if tvistacomesp not in opciones_validas:
            return render(request, 'error.html', {'mensaje': 'Opción de vista no válida'})

        opciones_descriptivas = {
            'visor_matric_adulto_fp': 'Adulto Formación Profesional',
            'visor_matric_adulto_primaria': 'Adulto Primaria',
            'visor_matric_adulto_secundaria': 'Adulto Secundaria',
            'visor_matric_comun_inicial': 'Común Inicial',
            'visor_matric_comun_primaria': 'Común Primaria',
            'visor_matric_comun_secundaria': 'Común Secundaria',
            'visor_matric_especial_ed_temprana': 'Especial Temprana',
            'visor_matric_especial_inicial': 'Especial Inicial',
            'visor_matric_especial_primaria': 'Especial Primaria',
        }
        nvistacomesp = opciones_descriptivas.get(tvistacomesp, 'Especial Primaria')
        opciones_relevamiento={            
            'ra_carga2019':'Relevamiento 2019', 'ra_carga2020':'Relevamiento 2020',
            'ra_carga2021':'Relevamiento 2021', 'ra_carga2022':'Relevamiento 2022',
            'ra_carga2023':'Relevamiento 2023', 'ra_carga2024':'Relevamiento 2024',
        }
        nrelevamiento=opciones_relevamiento.get(relevamiento,'Relevamiento 2022')

        connection = conectar_bd(request) 
        if not connection:
            return render(request, 'error_conexion.html')

        cursor = connection.cursor()
        query1 = f"""
            SELECT DISTINCT
                turno, grado, SUM(CAST(total AS INT)) AS total, SUM(CAST(total_var AS INT)) AS tot_var                               
            FROM funcion.{tvistacomesp}('{relevamiento}')  
            LEFT JOIN (
                    SELECT * FROM dblink (
                        'dbname=Padron user=visualizador password=Estadisticas24 host=visoreducativochaco.com.ar port=5432',
                        'SELECT distinct cueanexo, nom_est, nro_est, anio_creac_establec, fecha_creac_establec, region, udt, cui, cua, cuof, sector, ambito, ref_loc, calle, numero, localidad, departamento, cod_postal, categoria, estado_est, estado_loc, telefono_cod_area, telefono_nro, per_funcionamiento, email_loc FROM padron'
                    ) AS padron (cueanexo varchar, nom_est varchar, nro_est varchar, anio_creac_establec varchar, fecha_creac_establec varchar, region varchar, udt varchar, cui varchar, cua varchar, cuof varchar, sector varchar, ambito varchar, ref_loc varchar, calle varchar, numero varchar, localidad varchar, departamento varchar, cod_postal varchar, categoria varchar, estado_est varchar, estado_loc varchar, telefono_cod_area varchar, telefono_nro varchar, per_funcionamiento varchar, email_loc varchar)
                ) AS p using (cueanexo)       
            WHERE 1=1           
        """
        parameters = []
        if cueanexo: query1 += " AND cueanexo = %s"; parameters.append(cueanexo)
        if ambito: query1 += " AND ambito = %s"; parameters.append(ambito)
        if sector: query1 += " AND sector = %s"; parameters.append(sector)
        if region: query1 += " AND region = %s"; parameters.append(region)
        if departamento: query1 += " AND departamento = %s"; parameters.append(departamento)
        if localidad: query1 += " AND localidad = %s"; parameters.append(localidad)

        query1 += " GROUP BY grado, turno HAVING SUM(CAST(total AS INT)) <> 0"
        cursor.execute(query1, parameters)
        rows = cursor.fetchall()
        datos_encontrados=len(rows)>0

        datacomesp = []
        for row in rows:
            datacomesp.append({
                'turno': row[0], 'grado': row[1],
                'total': int(row[2]) if row[2] else 0,
                'tot_var': int(row[3]) if row[3] else 0
            })

        connection.close()
        if not datos_encontrados: return render(request, 'consulta_vacia.html')
        return render(request, 'reportes/comunespecial.html', {'datacomesp': datacomesp, 'nvistacomesp': nvistacomesp, 'nrelevamiento':nrelevamiento})

@csrf_exempt
def filter_data_snu(request):
    if request.method == 'POST':
        cueanexo = request.POST.get('Cueanexo')
        ambito = request.POST.get('Ambito')
        sector = request.POST.get('Sector')
        region = request.POST.get('Region')
        departamento = request.POST.get('Departamento')
        localidad = request.POST.get('Localidad')
        relevamiento = request.POST.get('Relevamiento')

        opciones_validas_snu = ['visor_matric_comun_snu']
        tvistasnu = request.POST.get('Vista')
        if tvistasnu not in opciones_validas_snu: return render(request, 'error.html', {'mensaje': 'Opción de vista no válida'})

        nvistasnu = 'Común SNU'
        opciones_relevamiento={            
            'ra_carga2019':'Relevamiento 2019', 'ra_carga2020':'Relevamiento 2020',
            'ra_carga2021':'Relevamiento 2021', 'ra_carga2022':'Relevamiento 2022',
            'ra_carga2023':'Relevamiento 2023', 'ra_carga2024':'Relevamiento 2024',
        }
        nrelevamiento=opciones_relevamiento.get(relevamiento,'Relevamiento 2022')

        connection = conectar_bd(request) 
        if not connection: return render(request, 'error_conexion.html')
        cursor = connection.cursor()

        query2 = f"""
            SELECT plan_est_titulo, SUM(CAST(total AS INT)) AS total, SUM(CAST(total_ingresante AS INT)) AS ingresantes, SUM(CAST(total_pasantia_practicas AS INT)) AS pasantia, SUM(CAST(total_residencia AS INT)) AS residencia
            FROM funcion.{tvistasnu}('{relevamiento}')         
            LEFT JOIN (
                    SELECT * FROM dblink ('dbname=Padron user=visualizador password=Estadisticas24 host=visoreducativochaco.com.ar port=5432', 'SELECT distinct cueanexo, nom_est, nro_est, anio_creac_establec, fecha_creac_establec, region, udt, cui, cua, cuof, sector, ambito, ref_loc, calle, numero, localidad, departamento, cod_postal, categoria, estado_est, estado_loc, telefono_cod_area, telefono_nro, per_funcionamiento, email_loc FROM padron') AS padron (cueanexo varchar, nom_est varchar, nro_est varchar, anio_creac_establec varchar, fecha_creac_establec varchar, region varchar, udt varchar, cui varchar, cua varchar, cuof varchar, sector varchar, ambito varchar, ref_loc varchar, calle varchar, numero varchar, localidad varchar, departamento varchar, cod_postal varchar, categoria varchar, estado_est varchar, estado_loc varchar, telefono_cod_area varchar, telefono_nro varchar, per_funcionamiento varchar, email_loc varchar)
                ) AS p using (cueanexo) WHERE 1=1           
        """        
        parameters = []
        if cueanexo: query2 += " AND p.cueanexo = %s"; parameters.append(cueanexo)
        if ambito: query2 += " AND p.ambito = %s"; parameters.append(ambito)
        if sector: query2 += " AND p.sector = %s"; parameters.append(sector)
        if region: query2 += " AND p.region = %s"; parameters.append(region)
        if departamento: query2 += " AND p.departamento = %s"; parameters.append(departamento)
        if localidad: query2 += " AND p.localidad = %s"; parameters.append(localidad)

        query2 += " GROUP BY plan_est_titulo HAVING SUM(CAST(total AS INT)) <> 0"
        cursor.execute(query2, parameters)
        rows = cursor.fetchall()
        datos_encontrados=len(rows)>0

        datasnu = []
        for row in rows:
            datasnu.append({
                'titulo': row[0], 'total': row[1],
                'ingresantes': int(row[2]) if row[2] is not None else 0,
                'pasantia': int(row[3]) if row[3] is not None else 0,
                'residencia': int(row[4]) if row[4] is not None else 0,
            })

        connection.close()
        if not datos_encontrados: return render(request, 'consulta_vacia.html')
        return render(request, 'reportes/snu.html', {'datasnu': datasnu, 'nvistasnu': nvistasnu, 'nrelevamiento':nrelevamiento})   

# ===================================================================== #
#               ENDPOINTS AJAX PARA NUEVOS DASHBOARDS                   #
# ===================================================================== #

@csrf_exempt
def aborigen_ajax(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Método no permitido'}, status=405)

    cueanexo     = request.POST.get('Cueanexo', '').strip()
    ambito       = request.POST.get('Ambito', '').strip()
    sector       = request.POST.get('Sector', '').strip()
    region       = request.POST.get('Region', '').strip()
    departamento = request.POST.get('Departamento', '').strip()
    localidad    = request.POST.get('Localidad', '').strip()
    relevamiento = request.POST.get('Relevamiento', '').strip()
    tvista       = request.POST.get('Vista', '').strip()

    opciones_validas = [
        'visor_matric_aborigen_adulto_primaria', 'visor_matric_aborigen_adulto_secundaria',
        'visor_matric_aborigen_comun_inicial', 'visor_matric_aborigen_comun_primaria',
        'visor_matric_aborigen_comun_secundaria', 'visor_matric_aborigen_comun_snu',
        'visor_matric_aborigen_educacion_especial'            
    ]
    
    if tvista not in opciones_validas or not relevamiento:
        return JsonResponse({'data': [], 'error': 'Parámetros inválidos'}, status=400)

    try:
        connection = conectar_bd(request)
        if not connection: return JsonResponse({'data': [], 'error': 'Error de conexión'}, status=500)
        cursor = connection.cursor()
        dblink_inner_sql = "SELECT cueanexo, MAX(region), MAX(sector), MAX(ambito), MAX(localidad), MAX(departamento) FROM padron GROUP BY cueanexo"
        query = f"""
            SELECT SUM(CAST(total AS INT)) AS total, SUM(CAST(tot_var AS INT)) AS tot_var                               
            FROM funcion.{tvista}('{relevamiento}')  
            LEFT JOIN (
                SELECT * FROM dblink ('dbname=Padron user=visualizador password=Estadisticas24 host=visoreducativochaco.com.ar port=5432', '{dblink_inner_sql}') AS padron (cueanexo varchar, region varchar, sector varchar, ambito varchar, localidad varchar, departamento varchar)
            ) AS p USING (cueanexo) WHERE 1=1
        """
        
        parameters = []
        if cueanexo: query += " AND p.cueanexo = %s"; parameters.append(cueanexo)
        if ambito: query += " AND p.ambito = %s"; parameters.append(ambito)
        if sector: query += " AND p.sector = %s"; parameters.append(sector)
        if region: query += " AND p.region = %s"; parameters.append(region)
        if departamento: query += " AND p.departamento = %s"; parameters.append(departamento)
        if localidad: query += " AND p.localidad = %s"; parameters.append(localidad)
        
        cursor.execute(query, parameters)
        row = cursor.fetchone()
        connection.close()
        
        total = int(row[0]) if row and row[0] is not None else 0
        varones = int(row[1]) if row and row[1] is not None else 0

        data = [{'etiqueta': 'Matrícula General Aborigen', 'varones': varones, 'total': total}] if total > 0 else []
        return JsonResponse({'data': data})
    except Exception as e:
        return JsonResponse({'data': [], 'error': str(e)}, status=500)
    
@csrf_exempt
def comunespecial_ajax(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Método no permitido'}, status=405)
    cueanexo     = request.POST.get('Cueanexo', '').strip()
    ambito       = request.POST.get('Ambito', '').strip()
    sector       = request.POST.get('Sector', '').strip()
    region       = request.POST.get('Region', '').strip()
    departamento = request.POST.get('Departamento', '').strip()
    localidad    = request.POST.get('Localidad', '').strip()
    relevamiento = request.POST.get('Relevamiento', '').strip()
    tvista       = request.POST.get('Vista', '').strip()

    opciones_validas = [
        'visor_matric_adulto_fp', 'visor_matric_adulto_primaria', 'visor_matric_adulto_secundaria',
        'visor_matric_comun_inicial', 'visor_matric_comun_primaria', 'visor_matric_comun_secundaria',            
        'visor_matric_especial_ed_temprana', 'visor_matric_especial_inicial', 'visor_matric_especial_primaria'
    ]
    if tvista not in opciones_validas or not relevamiento:
        return JsonResponse({'data': [], 'error': 'Parámetros inválidos'}, status=400)

    try:
        connection = conectar_bd(request)
        if not connection: return JsonResponse({'data': [], 'error': 'Error de conexión'}, status=500)
        cursor = connection.cursor()
        dblink_inner_sql = "SELECT cueanexo, MAX(region), MAX(sector), MAX(ambito), MAX(localidad), MAX(departamento) FROM padron GROUP BY cueanexo"

        query = f"""
            SELECT turno, grado, SUM(CAST(total AS INT)) AS total, SUM(CAST(total_var AS INT)) AS tot_var                               
            FROM funcion.{tvista}('{relevamiento}')  
            LEFT JOIN (
                SELECT * FROM dblink ('dbname=Padron user=visualizador password=Estadisticas24 host=visoreducativochaco.com.ar port=5432', '{dblink_inner_sql}') AS padron (cueanexo varchar, region varchar, sector varchar, ambito varchar, localidad varchar, departamento varchar)
            ) AS p USING (cueanexo) WHERE 1=1
        """
        
        parameters = []
        if cueanexo: query += " AND p.cueanexo = %s"; parameters.append(cueanexo)
        if ambito: query += " AND p.ambito = %s"; parameters.append(ambito)
        if sector: query += " AND p.sector = %s"; parameters.append(sector)
        if region: query += " AND p.region = %s"; parameters.append(region)
        if departamento: query += " AND p.departamento = %s"; parameters.append(departamento)
        if localidad: query += " AND p.localidad = %s"; parameters.append(localidad)
        
        query += " GROUP BY turno, grado HAVING SUM(CAST(total AS INT)) <> 0 ORDER BY turno, grado"
        cursor.execute(query, parameters)
        rows = cursor.fetchall()
        connection.close()
        
        data = [{'turno': r[0] or '-', 'grado': r[1] or '-', 'total': int(r[2]), 'varones': int(r[3])} for r in rows]
        return JsonResponse({'data': data})
    except Exception as e:
        return JsonResponse({'data': [], 'error': str(e)}, status=500)
    
@csrf_exempt
def snu_ajax(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Método no permitido'}, status=405)
    relevamiento = request.POST.get('Relevamiento', '').strip()
    tvista       = request.POST.get('Vista', '').strip()
    cueanexo     = request.POST.get('Cueanexo', '').strip()
    ambito       = request.POST.get('Ambito', '').strip()
    sector       = request.POST.get('Sector', '').strip()
    region       = request.POST.get('Region', '').strip()
    departamento = request.POST.get('Departamento', '').strip()
    localidad    = request.POST.get('Localidad', '').strip()

    if not relevamiento or not tvista: return JsonResponse({'data': [], 'error': 'Faltan parámetros'}, status=400)

    try:
        connection = conectar_bd(request)
        if not connection: return JsonResponse({'data': [], 'error': 'Error de conexión'}, status=500)
        cursor = connection.cursor()
        dblink_inner_sql = "SELECT cueanexo, MAX(region), MAX(sector), MAX(ambito), MAX(localidad), MAX(departamento) FROM padron GROUP BY cueanexo"

        query = f"""
            SELECT plan_est_titulo, SUM(CAST(total AS INT)) AS total, SUM(CAST(total_ingresante AS INT)) AS ingresantes, SUM(CAST(total_pasantia_practicas AS INT)) AS pasantia, SUM(CAST(total_residencia AS INT)) AS residencia
            FROM funcion.{tvista}('{relevamiento}')
            LEFT JOIN (
                SELECT * FROM dblink ('dbname=Padron user=visualizador password=Estadisticas24 host=visoreducativochaco.com.ar port=5432', '{dblink_inner_sql}') AS padron (cueanexo varchar, region varchar, sector varchar, ambito varchar, localidad varchar, departamento varchar)
            ) AS p USING (cueanexo) WHERE 1=1
        """
        
        params = []
        if cueanexo: query += " AND p.cueanexo = %s"; params.append(cueanexo)
        if ambito: query += " AND p.ambito = %s"; params.append(ambito)
        if sector: query += " AND p.sector = %s"; params.append(sector)
        if region: query += " AND p.region = %s"; params.append(region)
        if departamento: query += " AND p.departamento = %s"; params.append(departamento)
        if localidad: query += " AND p.localidad = %s"; params.append(localidad)

        query += " GROUP BY plan_est_titulo HAVING SUM(CAST(total AS INT)) <> 0 ORDER BY plan_est_titulo"
        cursor.execute(query, params)
        rows = cursor.fetchall()
        connection.close()

        data = [{'titulo': r[0] or 'SIN TÍTULO', 'total': int(r[1]) if r[1] else 0, 'ingresantes': int(r[2]) if r[2] else 0, 'pasantia': int(r[3]) if r[3] else 0, 'residencia': int(r[4]) if r[4] else 0} for r in rows]
        return JsonResponse({'data': data})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)