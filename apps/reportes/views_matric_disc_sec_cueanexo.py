import psycopg2
import os
import dotenv
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt

# Función para conectar a la base de datos
def conectar_bd(request):
    """
    Establece una conexión a la base de datos PostgreSQL.

    Args:
        request: El objeto de solicitud HTTP.

    Returns:
        connection: Un objeto de conexión a la base de datos si la conexión es exitosa, de lo contrario None.
    """
    
    try:
        connection = psycopg2.connect(
            host=os.getenv('POSTGRES_HOST'),
            user=os.getenv('POSTGRES_USER'),
            password=os.getenv('POSTGRES_PASSWORD'),
            database=os.getenv('DB_NAME2') 
        )
        return connection
    except psycopg2.Error as e:
        # Manejar el error de conexión
        return None

# Vista para mostrar el formulario de filtrado de matricula discapacidad
def filtrado_matric_disc_sec_cueanexo(request):
    
    
    return render(request, 'reportes/filter_matric_disc_sec_cueanexo.html')



#####################################################################
#      PARA REPORTE DE MATRICULA DISCAPACIDAD CON CUEANEXO          #
#####################################################################

# Vista para procesar los datos del formulario de filtrado de matricula 
@csrf_exempt
def filter_data_matric_disc_sec_cueanexo(request):
    
    
    if request.method == 'POST':     
        cueanexo = request.POST.get('Cueanexo')   
        ambito = request.POST.get('Ambito')
        sector = request.POST.get('Sector')
        region = request.POST.get('Region')
        departamento = request.POST.get('Departamento')
        localidad = request.POST.get('Localidad')        

        # Validar que tvista esté en la lista de opciones válidas
        opciones_validas = [
            'alumnos_cdiscapacidad_inicial',
            'alumnos_cdiscapacidad_primaria',
            'alumnos_cdiscapacidad_secundaria'                  
        ]

        # Obtener el valor seleccionado para tvista
        tvistamatricula = request.POST.get('Vista')
        print('ra_carga2024', 'vista:'+tvistamatricula, sector)

        # Validar que tvista esté en la lista de opciones válidas
        if tvistamatricula not in opciones_validas:
            return render(request, 'error.html', {'mensaje': 'Opción de vista no válida'})

        # Asignar un valor descriptivo a la opción de tvista seleccionada
        opciones_descriptivas = {
            'alumnos_cdiscapacidad_inicial': 'Alumnos Nivel Incial con discapacidad',
            'alumnos_cdiscapacidad_primaria': 'Alumnos Nivel Primario con discapacidad',
            'alumnos_cdiscapacidad_secundaria': 'Alumnos Nivel Secundario con discapacidad',
                  
        }
        nvistamatricula = opciones_descriptivas.get(tvistamatricula, 'Alumnos Nivel Incial con Discapacidad')
        

        # Conectarse a la base de datos
        connection = conectar_bd(request)
        if not connection:
            return render(request, 'error_conexion.html')

        cursor = connection.cursor()

        query = f"""
            SELECT 
                mc.cueanexo, 
                p.nom_est,                
                sum(mc.ceguera) as ceguera,
                sum(mc.dism_visual) as dism_visual,
                sum(mc.sordera) as sordera,
                sum(mc.hipoacusia) as hipoacusia,
                sum(mc.intelectual) as intelectual,
                sum(mc.motora_pura) as motora_pura,
                sum(mc.neuromotora) as neuromotora,
                sum(mc.espectro_autista) as tea,                               
                p.ambito, 
                p.sector, 
                p.region_loc,
                p.departamento,
                p.localidad,
                SUM(mc.total) 
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
            query += " AND p.localidad = %s"  # Aquí agregamos el espacio antes de "AND"
            parameters.append(localidad)

        # Agregamos GROUP BY después de los filtros dinámicos
        query += """
            GROUP BY mc.cueanexo, p.nom_est, p.ambito, p.sector, p.region_loc, p.departamento, p.localidad
            ORDER BY mc.cueanexo;
        """

        cursor.execute(query, parameters)
        rows = cursor.fetchall()


        # verificar si hay datos en rows 
        datos_encontrados = len(rows)>0

        # Convertir los resultados de la consulta a formato JSON
        datamatriccueanexo = []
        for row in rows:
            datamatriccueanexo.append({
                'cueanexo':row[0],
                'escuela':row[1],                                
                'ceguera': int(row[2]),
                'dism_visual': int(row[3]),
                'sordera': int(row[4]),
                'hipoacusia': int(row[5]),
                'intelectual': int(row[6]),
                'motora_pura': int(row[7]),
                'neuromotora': int(row[8]),
                'tea': int(row[9]),
                'region_loc': row[12],
                'localidad': row[14],
            })

        # Cerrar la conexión a la base de datos
        connection.close()
        print(datamatriccueanexo)

        # Si no hay datos para la consulta
        if not datos_encontrados:
            return render(request, 'consulta_vacia.html')
        
        # Devolver los datos como contexto a la plantilla 'cargos.html'
        return render(request, 'reportes/matric_disc_sec_cueanexo.html', {'datamatriccueanexo': datamatriccueanexo, 'nvistamatricula': nvistamatricula, 'nrelevamiento':'RELEVAMIENTO 2024'})
    
