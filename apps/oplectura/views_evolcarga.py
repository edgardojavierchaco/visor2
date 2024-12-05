from django.db import connection
from django.shortcuts import render
from django.contrib.auth.decorators import login_required

@login_required
def grafico_evaluacion_lectora(request):
    # Consulta SQL actualizada
    query = """
        SELECT 
            region,
            SUM(cargado) AS cargado,
            SUM(ausente) AS ausente,
            SUM(no_cargado) AS no_cargado,
            SUM(total) AS total
        FROM (
            SELECT
                region,
                CASE 
                    WHEN COUNT(CASE WHEN asistencia = 'true' THEN 1 END) >= 1 
                    THEN COUNT(CASE WHEN asistencia = 'true' THEN 1 END)
                    ELSE 0
                END AS cargado,
                CASE 
                    WHEN COUNT(CASE WHEN asistencia = 'true' THEN 1 END) >= 1 
                    THEN COUNT(CASE WHEN asistencia = 'false' THEN 1 END)
                    ELSE 0
                END AS ausente,
                CASE 
                    WHEN COUNT(CASE WHEN asistencia = 'true' THEN 1 END) = 0 
                    THEN COUNT(asistencia) 
                    ELSE 0
                END AS no_cargado,
                COUNT(asistencia) AS total
            FROM cenpe."Evaluacion_Lectora"
            GROUP BY region, cueanexo, seccion
        ) AS subquery
        GROUP BY region
        ORDER BY region;
    """
    with connection.cursor() as cursor:
        cursor.execute(query)
        rows = cursor.fetchall()

    # Procesar los datos para el gráfico y la tabla
    regions = [row[0] for row in rows]  # Nombres de las regiones
    cargados = [row[1] for row in rows]  # Cargados
    ausentes = [row[2] for row in rows]  # Ausentes
    no_cargados = [row[3] for row in rows]  # No cargados
    totales = [row[4] for row in rows]  # Total de registros (cargados + ausentes)
    
    # Asegurarse de que los valores sean números
    cargados = [float(c) for c in cargados]
    ausentes = [float(a) for a in ausentes]
    no_cargados = [float(n) for n in no_cargados]
    totales = [float(t) for t in totales]

    # Preparar datos para la tabla
    table_data = []
    for region, cargado, ausente, no_cargado, total in rows:
        porcentaje_cargados = ((cargado+ausente) / total * 100) if total > 0 else 0
        table_data.append({
            'region': region,
            'cargados': cargado,
            'ausentes': ausente,
            'no_cargados': no_cargado,
            'total': total,
            'porcentaje_cargados': round(porcentaje_cargados, 2)
        })

    # Contexto para el template
    context = {
        'regions': regions,
        'cargados': cargados,
        'ausentes': ausentes,
        'no_cargados': no_cargados,
        'totales': totales,
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
