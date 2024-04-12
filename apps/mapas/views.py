import json
import psycopg2
import asyncpg # type: ignore
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse

def filtrado(request):    
    return render(request, 'mapa/filter.html')

def filtrado_list(request):
    return render(request,'mapa/filter_listadomap.html')

@csrf_exempt
def operaciones_comunes(request, template_name='publico/basecriterios.html'):   
    if request.method == 'POST':
        cueanexo = request.POST.get('Cueanexo')
        ambito = request.POST.get('Ambito')
        sector = request.POST.get('Sector')
        region = request.POST.get('Region')
        departamento = request.POST.get('Departamento')
        localidad = request.POST.get('Localidad')
        oferta = request.POST.get('Oferta')

        print("Parámetros de la solicitud:", ambito, sector, localidad, oferta)

        # Conectarse a la base de datos
        connection = psycopg2.connect(
            host='sigechaco.com.ar',            
            user='visualizador',
            password='Estadisticas24',
            database='visualizador'
        )

        # Realizar la consulta en la base de datos
        cursor = connection.cursor()
        query = "SELECT cueanexo, lat, long, nom_est, oferta, ambito, sector, region_loc, calle, numero, localidad FROM v_capa_unica_ofertas WHERE 1=1 "
        parameters = []
        if cueanexo:
            query += "AND cueanexo = %s"
            parameters.append(cueanexo)
        if ambito:
            query += " AND ambito = %s"
            parameters.append(ambito)
        if sector:
            query += " AND sector = %s"
            parameters.append(sector)
        if region:
            query += " AND region_loc = %s"
            parameters.append(region)
        if departamento:
            query += " AND departamento = %s"
            parameters.append(departamento)
        if localidad:
            query += "AND localidad = %s"
            parameters.append(localidad)
        if oferta:
            query += "AND acronimo LIKE %s"
            parameters.append('%'+oferta+'%')

        cursor.execute(query, parameters)
        rows = cursor.fetchall()

        # Filtrar los marcadores con latitud y longitud distintas de 0 o vacías
        filtered_rows = [(cueanexo, lat, lng, nom_est, oferta, ambito, sector, region_loc, calle, numero, localidad) 
                         for cueanexo, lat, lng, nom_est, oferta, ambito, sector, region_loc, calle, numero, localidad in rows 
                         if lat != 0 and lng != '' and lng != 0 and lat != '']

        # Obtener los nombres de las columnas
        column_names = [desc[0] for desc in cursor.description] # type: ignore
        filtered_rows = [row for row in rows if row[1] != 0 and row[2] != 0]

        # Cerrar la conexión a la base de datos
        cursor.close()
        connection.close()

        context = {
            'title': 'Mapa',
            'data_json': json.dumps(filtered_rows),
            'column_names_json': json.dumps(column_names)
        }

        print("Contexto en operaciones_comunes:", context)

        if template_name == 'publico/basecriterios.html':
            return context
        elif template_name == 'publico/listadomap.html':
            return context
        else:
            return context
        
def filter_data(request):
    context = operaciones_comunes(request, template_name='publico/basecriterios.html')
    print("Contexto en filter_data:", context)
    return render(request, 'publico/basecriterios.html', context)

def filter_listado_map(request):
    context = operaciones_comunes(request, template_name='publico/listadomap.html')
    print("Contexto en filter_listado_map:", context)
    return render(request, 'publico/listadomap.html', context)


    
#####################################################################
#      PARA MOSTRAR DATOS MARCADOR SELLECIONADO EN EL MAPA          #
#####################################################################
async def filtrar_tablas_view(request):      
    
    
    cueanexo = request.GET.get('cueanexo')

    # Validar y sanitizar el valor de cueanexo
    if cueanexo is None:
        # Manejar el caso si no se proporciona cueanexo
        return render(request, 'error.html', {'mensaje': 'No se proporcionó el parámetro cueanexo'})

    # Establecer la conexión a la base de datos
    try:
        connection = await asyncpg.connect(
            host='sigechaco.com.ar',
            user='visualizador',
            password='Estadisticas24',
            database='Padron'
        )
    except asyncpg.PostgresError as e:
        # Manejar el error de conexión
        return render(request, 'error.html', {'mensaje': 'Error al conectar a la base de datos'})

    # Construir y ejecutar la consulta SQL para obtener los datos de las dos tablas
    
    institucional = """
        SELECT categoria, jornada, oferta, id_establecimiento, ref_loc, calle, numero, anexo,apellido_resp, nombre_resp, resploc_telefono,resploc_email,
            sup_tecnico, email_suptecnico, tel_suptecnico
        FROM padron_ofertas        
        WHERE cueanexo = $1 
    """ 
    planes="""
        SELECT titulo, orientacion
        FROM v_planes_estudio
        WHERE CONCAT(cue,anexo)=$1
    """

    # Construir y ejecutar la consulta SQL para obtener los datos de las dos tablas
    anexos = """
        SELECT DISTINCT po.anexo, po.calle, po.numero, po.estado_loc
        FROM padron_ofertas po
        WHERE po.id_establecimiento IN (
            SELECT id_establecimiento
            FROM padron_ofertas
            WHERE cueanexo = $1 
        ) AND po.estado_loc = $2
    """
    ofertas = """
        SELECT anexo, calle, numero, cueanexo, oferta, est_oferta
        FROM padron_ofertas
        WHERE cueanexo = $1 AND est_oferta = $2        
    """
    params = [cueanexo]
    params2= [cueanexo,'Activo']

    try:
        resultados = await connection.fetch(institucional, *params)
        resultados1=await connection.fetch(planes,*params)    
        resultados2=await connection.fetch(anexos, *params2) 
        resultados3=await connection.fetch(ofertas, *params2)   
        #print(resultados)
        #print(resultados1)
        print(resultados2)
        
    except asyncpg.PostgresError as e:
        # Manejar el error de consulta
        await connection.close()
        return render(request, 'error.html', {'mensaje': 'Error al ejecutar la consulta'})

    # Cerrar la conexión a la base de datos
    await connection.close()    
    
    return render(request, 'publico/otro_templatemap.html', {'resultados': resultados, 'resultados1':resultados1, 'resultados2':resultados2, 'resultados3':resultados3})