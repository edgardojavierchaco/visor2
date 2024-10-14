import psycopg2
from django.shortcuts import render
from django.http import JsonResponse
from django.db import connection

def consulta_carrerastitulos(request):
    """
    Consulta los títulos de carreras y localidades en función de los filtros seleccionados.

    Args:
        request: La solicitud HTTP que contiene los filtros seleccionados.

    Returns:
        HttpResponse: Si la solicitud es AJAX, devuelve un JsonResponse con los títulos y datos filtrados.
                      Si es una solicitud estándar, renderiza la plantilla con las localidades, niveles, títulos y datos.
    """
    
    localidades = []
    titulos = []
    nivel = []
    datos = []
    
    selected_localidades = request.GET.getlist('localidad[]')    
    selected_nivel = request.GET.get('nivel')
    selected_titulo=request.GET.get('titulo')

    # Obtine las localidades únicas
    with connection.cursor() as cursor:
        cursor.execute("SELECT DISTINCT localidad FROM public.carreras_titulos WHERE est_oferta = 'Activo'")
        localidades = [row[0] for row in cursor.fetchall()]

    # Obtiene los niveles únicos
    with connection.cursor() as cursor:
        cursor.execute("SELECT DISTINCT niveltitulotipo FROM public.carreras_titulos WHERE est_oferta = 'Activo'")
        nivel = [row[0] for row in cursor.fetchall()]

    # Construye la consulta para filtrar títulos basados en localidad y nivel seleccionados
    titulo_query = "SELECT DISTINCT titulo FROM public.carreras_titulos WHERE est_oferta = 'Activo'"
    if selected_localidades:
        localidades_str = ', '.join(f"'{loc}'" for loc in selected_localidades)
        titulo_query += f" AND localidad IN ({localidades_str})"
    
    if selected_nivel:
        titulo_query += f" AND niveltitulotipo = '{selected_nivel}'"
    
    with connection.cursor() as cursor:
        cursor.execute(titulo_query)
        titulos = [row[0] for row in cursor.fetchall()]

    # lógica para obtener los datos según los filtros seleccionados
    query = """
        SELECT DISTINCT cueanexo, nom_est, sector, calle, numero, telefono_loc, email_loc, localidad, carrera, titulo
        FROM public.carreras_titulos
        WHERE est_oferta = 'Activo'
    """
    if selected_localidades:
        query += f" AND localidad IN ({localidades_str})"
    if selected_nivel:
        query += f" AND niveltitulotipo='{selected_nivel}'"
    if selected_titulo:
        query += f" AND titulo='{selected_titulo}'"
    
    
    with connection.cursor() as cursor:
        cursor.execute(query)
        rows = cursor.fetchall()

        for row in rows:
            datos.append([
                row[0],  # cueanexo
                row[1],  # nom_est
                row[2],  # sector
                row[3],  # calle
                row[4],  # numero
                row[5],  # telefono_loc
                row[6],  # email_loc
                row[7],  # localidad
                row[8],  # carrera
                row[9],  # titulo
            ])

    # Si es una solicitud AJAX para actualizar títulos
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'titulos': titulos, 'data': datos})

    # Si es una solicitud estándar, renderiza la plantilla
    context = {
        'localidades': localidades,
        'nivel': nivel,
        'titulos': titulos,
        'datos': datos,
    }
    return render(request, 'reportes/indexcarreras.html', context)


# datos para el modal carreras-titulos
def datoscarreras(request):
    """
    Obtiene los datos de una carrera específica basándose en el cueanexo proporcionado.

    Args:
        request: La solicitud HTTP que contiene el cueanexo.

    Returns:
        HttpResponse: Renderiza la plantilla del modal con los resultados obtenidos de la base de datos.
                       Si no se proporciona cueanexo o hay un error de conexión, renderiza una página de error.
    """
    
    cueanexo = request.GET.get('cueanexo')
    
    # Validar y sanitizar el valor de cueanexo
    if cueanexo is None:
        # Manejar el caso si no se proporciona cueanexo
        return render(request, 'error.html', {'mensaje': 'No se proporcionó el parámetro cueanexo'})

    # Establecer la conexión a la base de datos Padrón
    try:
        connection = psycopg2.connect(
            host='visoreducativochaco.com.ar',
            user='visualizador',
            password='Estadisticas24',
            database='Padron'
        )
        cursor = connection.cursor()
    except psycopg2.Error as e:
        # Manejar el error de conexión
        return render(request, 'error.html', {'mensaje': 'Error al conectar a la base de datos'})
    

    datosmodal=f"""SELECT DISTINCT cueanexo, calle, numero, telefono_loc, email_loc
                    FROM public.padron_ofertas
                    WHERE est_oferta='Activo' AND cueanexo='{cueanexo}'
    """
    
    cursor.execute(datosmodal)                
    resultadosmodal= cursor.fetchall()      
        
    # Transformar los resultados en una respuesta renderizada
    return render(request, 'reportes/modaldatos.html', {'resultados': resultadosmodal})