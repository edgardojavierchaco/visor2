import psycopg2
import os
from django.shortcuts import render
from django.http import JsonResponse

DB_CONFIG = {
    "dbname": "visualizador",
    "user": "visualizador",
    "password": "Estadisticas24",
    "host": "relevamientoanual.com.ar",
    "port": "5432",  # Puerto por defecto de PostgreSQL
}

def tabla_view(request):
    return render(request, 'reportes/tabla.html')

def get_table_data(request):
    # Obtener las columnas seleccionadas desde la petición GET
    selected_columns = request.GET.getlist('columns[]')  # ["cueanexo", "cargos", "total"]

    # Conectar a la base de datos PostgreSQL
    connection = psycopg2.connect(
        dbname=DB_CONFIG["dbname"],
        user=DB_CONFIG["user"],
        password=DB_CONFIG["password"],
        host=DB_CONFIG["host"],
        port=DB_CONFIG["port"]
    )
    cursor = connection.cursor()

    
    # Verificar qué columnas están seleccionadas para el agrupamiento
    grouping_columns = []

    # Si 'cueanexo' o 'cargos' están seleccionados, los agregamos a las columnas de agrupamiento
    if 'cueanexo' in selected_columns:
        grouping_columns.append('cueanexo')
    if 'cargos' in selected_columns:
        grouping_columns.append('cargos')
    if 'regional' in selected_columns:
        grouping_columns.append('regional')
    if 'localidad' in selected_columns:
        grouping_columns.append('localidad')
    if 'departamento' in selected_columns:
        grouping_columns.append('departamento')
        
    # Si no se ha seleccionado ninguna columna de agrupamiento válida, asignamos un valor por defecto
    if not grouping_columns:
        grouping_columns = ['cueanexo']  # Por ejemplo, siempre agrupar por 'cueanexo' si no se seleccionan otras

    # Generar la lista de columnas seleccionadas para la consulta
    select_columns = ", ".join(selected_columns)

    # Asegurarse de incluir todas las columnas seleccionadas en el GROUP BY
    group_by_columns = grouping_columns 

    # Construir la consulta SQL con el agrupamiento dinámico
    query = f'''
        SELECT 
            {", ".join(group_by_columns)}, 
            SUM(vccp.total) as total,
            SUM(vccp.titular) as titular,
            SUM(vccp.interinos) as interinos,
            SUM(vccp.sin_cubrir) as sin_cubrir
        FROM funcion.visor_cargo_comun_primaria('ra_carga2024') as vccp
        LEFT JOIN (
            SELECT DISTINCT ON(vcuo.padron_cueanexo) vcuo.padron_cueanexo, vcuo.region_loc as regional, departamento, localidad
            FROM public.v_capa_unica_ofertas as vcuo
        ) as vcuo
        ON vccp.cueanexo::text = vcuo.padron_cueanexo::text
        WHERE vccp.total != 0
        GROUP BY 
            {', '.join(group_by_columns)} -- Asegurarse de que todas las columnas sean incluidas en GROUP BY
        ORDER BY 
            {group_by_columns[0]}  -- Orden por la primera columna del agrupamiento
    '''

    cursor.execute(query)
    rows = cursor.fetchall()
    print(rows)
    # Formatear a JSON la respuesta
    table_data = []
    for row in rows:
        row_data = {group_by_columns[i]: row[i] for i in range(len(group_by_columns))}
        row_data.update({
            'total': row[len(group_by_columns)],
            'titular': row[len(group_by_columns) + 1],
            'interinos': row[len(group_by_columns) + 2],
            'sin_cubrir': row[len(group_by_columns) + 3],            
        })
        table_data.append(row_data)
        print(table_data)
    return JsonResponse(table_data, safe=False)


def obtener_columnas_cargos(request):
    """ Obtiene los nombres de las columnas de la tabla 'cargo_comun_primaria' desde la BD 'ra_carga2024' """
    try:
        connection = psycopg2.connect(
            host=os.getenv('POSTGRES_HOST'),
            user=os.getenv('POSTGRES_USER'),
            password=os.getenv('POSTGRES_PASSWORD'),
            database="visualizador"
        )

        sql = """
            SELECT * FROM funcion.visor_cargo_comun_primaria('ra_carga2024') as vccp
            LEFT JOIN(
                SELECT cueanexo,region_loc as regional, departamento, localidad
                        FROM public.v_capa_unica_ofertas
                    ) as vcuo
                    on vccp.cueanexo::text=vcuo.cueanexo::text
                    LIMIT 0;                                                                                        
        """       
        

        with connection.cursor() as cursor:
            cursor.execute(sql)
            columnas = sorted(set(desc[0] for desc in cursor.description))

        return JsonResponse({"columnas": columnas})

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)