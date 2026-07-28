import psycopg2
import os
import dotenv
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
        SELECT DISTINCT cueanexo, nom_est, sector, calle, numero, telefono_loc, email_loc, localidad, carrera, titulo, niveltitulotipo
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
            datos.append({
                "cueanexo": row[0],
                "nom_est": row[1],
                "sector": row[2],
                "localidad": row[7],
                "nivel": row[10]
            })

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


def dashboard_carreras(request):
    localidades, niveles, titulos = [], [], []

    selected_localidades = request.GET.getlist('localidad[]')
    selected_nivel = request.GET.get('nivel')
    selected_titulo = request.GET.get('titulo')

    # -----------------------------
    # Localidades y niveles únicos
    # -----------------------------
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT DISTINCT localidad 
            FROM public.carreras_titulos 
            WHERE est_oferta='Activo' 
            ORDER BY localidad
        """)
        localidades = [row[0] for row in cursor.fetchall()]

        cursor.execute("""
            SELECT DISTINCT niveltitulotipo 
            FROM public.carreras_titulos 
            WHERE est_oferta='Activo' 
            ORDER BY niveltitulotipo
        """)
        niveles = [row[0] for row in cursor.fetchall()]

    # -----------------------------
    # Filtrar títulos según filtros
    # -----------------------------
    titulo_query = "SELECT DISTINCT titulo FROM public.carreras_titulos WHERE est_oferta='Activo'"
    if selected_localidades:
        loc_str = ','.join(f"'{loc}'" for loc in selected_localidades)
        titulo_query += f" AND localidad IN ({loc_str})"
    if selected_nivel:
        titulo_query += f" AND niveltitulotipo='{selected_nivel}'"
    
    titulo_query += " ORDER BY titulo"

    with connection.cursor() as cursor:
        cursor.execute(titulo_query)
        titulos = [row[0] for row in cursor.fetchall()]

    # -----------------------------
    # Datos para la tabla
    # -----------------------------
    query = "SELECT cueanexo, nom_est, sector, localidad, niveltitulotipo FROM public.carreras_titulos WHERE est_oferta='Activo'"
    if selected_localidades:
        query += f" AND localidad IN ({loc_str})"
    if selected_nivel:
        query += f" AND niveltitulotipo='{selected_nivel}'"
    if selected_titulo:
        query += f" AND titulo='{selected_titulo}'"

    with connection.cursor() as cursor:
        cursor.execute(query)
        columnas = [col[0] for col in cursor.description]  # nombres de columnas
        datos = [dict(zip(columnas, row)) for row in cursor.fetchall()]  # filas como dict

    # -----------------------------
    # Mapear datos exactos para DataTables
    # -----------------------------
    datos_json = [
        {
            'cueanexo': d.get('cueanexo', ''),
            'nom_est': d.get('nom_est', ''),
            'sector': d.get('sector', ''),
            'localidad': d.get('localidad', ''),
            'nivel': d.get('niveltitulotipo', '')
        }
        for d in datos
    ]

    # -----------------------------
    # Resumen
    # -----------------------------
    resumen = {'total_carreras': len(datos_json), 'por_sector': {}, 'por_nivel': {}, 'por_localidad': {}}
    for d in datos_json:

        sector = d.get('sector')
        nivel = d.get('nivel')
        localidad = d.get('localidad')

        if sector:
            resumen['por_sector'][sector] = resumen['por_sector'].get(sector, 0) + 1

        if nivel:
            resumen['por_nivel'][nivel] = resumen['por_nivel'].get(nivel, 0) + 1

        if localidad:
            resumen['por_localidad'][localidad] = resumen['por_localidad'].get(localidad, 0) + 1

    # -----------------------------
    # Respuesta AJAX
    # -----------------------------
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'titulos': titulos, 'data': datos_json, 'resumen': resumen})

    # -----------------------------
    # Render inicial de la página
    # -----------------------------
    return render(request, 'reportes/dashboard_carreras.html', {
        'localidades': localidades,
        'niveles': niveles,
        'titulos': titulos,
        'resumen': resumen
    })
    

def datoscarreras(request):

    cueanexo = request.GET.get('cueanexo')

    if not cueanexo:
        return JsonResponse({'error': 'No se proporcionó cueanexo'}, status=400)

    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT cueanexo, nom_est, sector, calle, numero,
                   telefono_loc, email_loc, localidad,
                   carrera, titulo, niveltitulotipo
            FROM public.carreras_titulos
            WHERE est_oferta='Activo'
            AND cueanexo=%s
        """, [cueanexo])

        resultado = cursor.fetchone()

    if not resultado:
        return JsonResponse({'error': 'No se encontraron datos'}, status=404)

    keys = [
        'cueanexo','nom_est','sector','calle','numero',
        'telefono','email','localidad','carrera','titulo','nivel'
    ]

    data = dict(zip(keys, resultado))

    return JsonResponse(data)