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

# Vista para mostrar el formulario de filtrado de matricula aborigen
def filtrado_matriccueanexo(request):
    """
    Renderiza el formulario de filtrado de matrícula aborigen.

    Args:
        request: El objeto de solicitud HTTP.

    Returns:
        Renderizado de la plantilla 'reportes/filter_matriccueanexo.html'.
    """
    
    return render(request, 'reportes/filter_matriccueanexo.html')



#####################################################################
#               PARA REPORTE DE MATRICULA CON CUEANEXO              #
#####################################################################

# Vista para procesar los datos del formulario de filtrado de matricula 
@csrf_exempt
def filter_data_matric_cueanexo(request):
    """
    Procesa los datos del formulario de filtrado de matrícula aborigen y devuelve los resultados.

    Args:
        request: El objeto de solicitud HTTP.

    Returns:
        Renderizado de la plantilla correspondiente con los datos obtenidos o un error si no hay datos.
    """
    
    if request.method == 'POST':     
        cueanexo = request.POST.get('Cueanexo')   
        ambito = request.POST.get('Ambito')
        sector = request.POST.get('Sector')
        region = request.POST.get('Region')
        departamento = request.POST.get('Departamento')
        localidad = request.POST.get('Localidad')        

        # Validar que tvista esté en la lista de opciones válidas
        opciones_validas = [
            'matric_aborigen_adulto_primaria',
            'matric_aborigen_adulto_secundaria',
            'matric_aborigen_comun_inicial',
            'matric_aborigen_comun_primaria',
            'matric_aborigen_comun_secundaria',
            'matric_aborigen_comun_snu',
            'matric_aborigen_educacion_especial',
            'matric_adulto_fp',
            'matric_adulto_primaria',
            'matric_adulto_secundaria',
            'matric_cef',
            'matric_comun_artistica',
            'matric_comun_inicial',
            'matric_comun_primaria',
            'matric_comun_secundaria',
            'matric_comun_snu',
            'matric_especial_ed_temprana',
            'matric_especial_inicial',
            'matric_especial_primaria'        
        ]

        # Obtener el valor seleccionado para tvista
        tvistamatricula = request.POST.get('Vista')
        print('ra_carga2024', 'vista:'+tvistamatricula, sector)

        # Validar que tvista esté en la lista de opciones válidas
        if tvistamatricula not in opciones_validas:
            return render(request, 'error.html', {'mensaje': 'Opción de vista no válida'})

        # Asignar un valor descriptivo a la opción de tvista seleccionada
        opciones_descriptivas = {
            'matric_aborigen_adulto_primaria': 'Aborigen Adulto Primaria',
            'matric_aborigen_adulto_secundaria': 'Aborigen Adulto Secundaria',
            'matric_aborigen_comun_inicial': 'Aborigen Común Inicial',
            'matric_aborigen_comun_primaria': 'Aborigen Común Primaria',
            'matric_aborigen_comun_secundaria': 'Aborigen Común Secundaria',
            'matric_aborigen_comun_snu': 'Aborigen Común SNU',
            'matric_aborigen_educacion_especial': 'Aborigen Educación Especial', 
            'matric_adulto_fp': 'Adulto Formación Profesional', 
            'matric_adulto_primaria': 'Adulto Primaria', 
            'matric_adulto_secundaria': 'Adulto Secundaria', 
            'matric_cef': 'CEF', 
            'matric_comun_artistica': 'Común Artística', 
            'matric_comun_inicial': 'Común Inicial', 
            'matric_comun_primaria': 'Común Primaria', 
            'matric_comun_secundaria': 'Común Secundaria', 
            'matric_comun_snu': 'Común SNU', 
            'matric_especial_ed_temprana': 'Especial Educación Temprana', 
            'matric_especial_inicial': 'Especial Inicial', 
            'matric_especial_primaria': 'Especial Primaria',            
        }
        nvistamatricula = opciones_descriptivas.get(tvistamatricula, 'Común Inicial')
        

        # Conectarse a la base de datos
        connection = conectar_bd(request)
        if not connection:
            return render(request, 'error_conexion.html')

        cursor = connection.cursor()

        query = f"""
            SELECT 
                mc.cueanexo, 
                mc.escuela, 
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
                    sector, 
                    ambito,
                    region_loc,
                    departamento,
                    localidad
                FROM 
                    dblink(
                        'dbname=visualizador user=visualizador password=Estadisticas24 host=visoreducativochaco.com.ar port=5432',
                        'SELECT DISTINCT cueanexo, ambito, sector, departamento, localidad, region_loc FROM public.v_capa_unica_ofertas'
                    ) AS padron(cueanexo character varying, ambito character varying, sector character varying, departamento character varying, localidad character varying, region_loc character varying)
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
            GROUP BY mc.cueanexo, mc.escuela, p.ambito, p.sector, p.region_loc, p.departamento, p.localidad
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
                'total': int(row[7])
            })

        # Cerrar la conexión a la base de datos
        connection.close()
        print(datamatriccueanexo)

        # Si no hay datos para la consulta
        if not datos_encontrados:
            return render(request, 'consulta_vacia.html')
        
        # Devolver los datos como contexto a la plantilla 'cargos.html'
        return render(request, 'reportes/matric_cueanexo.html', {'datamatriccueanexo': datamatriccueanexo, 'nvistamatricula': nvistamatricula, 'nrelevamiento':'RELEVAMIENTO 2024'})
    
