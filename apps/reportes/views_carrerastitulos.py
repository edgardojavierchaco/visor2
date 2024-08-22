from django.shortcuts import render
from django.http import JsonResponse
from django.db import connection

def consulta_carrerastitulos(request):
    localidades = []
    titulos = []
    datos = []
    selected_localidades = request.GET.getlist('localidad[]')  # Obtener la lista de localidades seleccionadas
    selected_titulo = request.GET.get('titulo')
    
    # Obtener las localidades únicas
    with connection.cursor() as cursor:
        cursor.execute("SELECT DISTINCT localidad FROM public.carreras_titulos WHERE est_oferta = 'Activo'")
        localidades = [row[0] for row in cursor.fetchall()]

    # Obtener los títulos únicos
    with connection.cursor() as cursor:
        cursor.execute("SELECT DISTINCT titulo FROM public.carreras_titulos WHERE est_oferta = 'Activo'")
        titulos = [row[0] for row in cursor.fetchall()]
    
    query = """
        SELECT cueanexo, nom_est, sector, calle, numero, telefono_loc, email_loc, localidad, carrera, titulo
        FROM public.carreras_titulos
        WHERE est_oferta = 'Activo'
    """
    
    # Si una localidad ha sido seleccionada, agregar al WHERE
    if selected_localidades:
        localidades_str = ', '.join(f"'{loc}'" for loc in selected_localidades)
        query += f" AND localidad IN ({localidades_str})"
        
    # Si un título ha sido seleccionado, agregar al WHERE
    if selected_titulo:
        query += f" AND titulo='{selected_titulo}'"
        
    with connection.cursor() as cursor:
        cursor.execute(query)
        rows = cursor.fetchall()

        # Verificar si se obtuvieron resultados y si el número de columnas es correcto
        for row in rows:
            if len(row) == 10:  # Asegurarse de que hay 10 columnas
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
    
    context = {
        'localidades': localidades,
        'titulos': titulos,
        'datos': datos,
    }
    print(context)
    
    # Responder con JSON si es una solicitud AJAX
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'data': datos})  # Asegúrate de enviar los datos bajo la clave 'data'
    
    return render(request, 'reportes/indexcarreras.html', context)
