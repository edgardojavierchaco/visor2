from django.db import connection
from django.shortcuts import render
from django.contrib.auth.decorators import login_required

@login_required
def grafico_evaluacion_lectora(request):
    # Ejecutar la consulta
    query = """
        SELECT 
            region,
            COUNT(CASE WHEN velocidad = 0 THEN 1 END) AS no_cargados,
            COUNT(CASE WHEN velocidad != 0 THEN 1 END) AS cargados
        FROM cenpe."Evaluacion_Lectora"
        GROUP BY region
        ORDER BY region;
    """
    with connection.cursor() as cursor:
        cursor.execute(query)
        rows = cursor.fetchall()

    # Procesar los datos para el gráfico y la tabla
    regions = [row[0] for row in rows]  # Extrae las regiones
    no_cargados = [row[1] for row in rows]  # Conteo no cargados
    cargados = [row[2] for row in rows]  # Conteo cargados
    
    
    # Calcular porcentajes y preparar los datos para la tabla
    table_data = []
    for region, nc, c in rows:
        total = nc + c
        porcentaje_cargados = (c / total * 100) if total > 0 else 0
        table_data.append({
            'region': region,
            'no_cargados': nc,
            'cargados': c,
            'porcentaje_cargados': round(porcentaje_cargados, 2)
        })


    # Pasar los datos al template
    context = {
        'regions': regions,
        'no_cargados': no_cargados,
        'cargados': cargados,
        'table_data': table_data,
    }
    
    return render(request, 'oplectura/grafico_evolucion_carga_OL.html', context)

@login_required
def grafico_aplicador_region(request):
    # Ejecutar la consulta
    query = """
        SELECT 
            COUNT(da.dni_docen) AS conteo,
            vcu.region_loc
        FROM 
            cenpe."Docente_Aplicador" AS da
        LEFT JOIN (
            SELECT DISTINCT cueanexo, region_loc
            FROM public.v_capa_unica_ofertas
        ) AS vcu
        ON da.cueanexo = vcu.cueanexo::text
        WHERE da.dni_docen = '0'
        GROUP BY vcu.region_loc
        ORDER BY vcu.region_loc;
    """
    with connection.cursor() as cursor:
        cursor.execute(query)
        rows = cursor.fetchall()

    # Procesar los datos para el gráfico
    regions = [row[1] if row[1] else 'Sin Región' for row in rows]  # Maneja nulos como 'Sin Región'
    counts = [row[0] for row in rows]  # Conteos de docentes

    # Pasar los datos al template
    context = {
        'regions': regions,
        'counts': counts,
    }
    return render(request, 'oplectura/grafico_aplicador_regionOL.html', context)
