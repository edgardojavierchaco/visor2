import json
import psycopg2
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt


def filtrado_cueradio(request):
    return render(request,'mapa/filter_cuearadio.html')

#####################################################################
#      PARA RENDERIZAR LOS MARCADORES EN EL MAPA DE LEAFLET         #
#####################################################################

# Función para conectarse a la base de datos PostgreSQL
def connect_to_database():
    return psycopg2.connect(
        host='visoreducativochaco.com.ar',
        user='visualizador',
        password='Estadisticas24',
        database='visualizador'
    )

# Función para ejecutar una consulta y devolver los resultados
def execute_query(cursor, query, parameters=None):
    cursor.execute(query, parameters)
    return cursor.fetchall()

# Función para calcular la distancia entre dos puntos geográficos
def calculate_distance(cursor, center_lng, center_lat, long, lat):
    cursor.execute("""
        SELECT ST_Distance(
            ST_MakePoint(%s, %s)::geography,
            ST_MakePoint(%s, %s)::geography
        );
    """, (center_lng, center_lat, long, lat))
    distance = cursor.fetchone()[0]
    return distance

# Vista para filtrar datos y renderizar el mapa
@csrf_exempt
def filter_cueradio(request):
    if request.method == 'POST':
        cueanexos = request.POST.get('Cueanexo')
        radio = request.POST.get('Radio')

        with connect_to_database() as connection:
            with connection.cursor() as cursor:
                # Obtener datos de v_capa_unica_ofertas
                query = "SELECT cueanexo, lat, long, nom_est, oferta, ambito, sector, region_loc, calle, numero, localidad FROM v_capa_unica_ofertas WHERE 1=1"
                parameters = []
                if cueanexos:
                    query += " AND cueanexo = %s"
                    parameters.append(cueanexos)
                rows = execute_query(cursor, query, parameters)

                # Filtrar datos
                filtered_rows = []
                for row in rows:
                    cue, lat, lng, nom_est, oferta, ambito, sector, region_loc, calle, numero, loc = row
                    if lat != 0 and lng != 0:
                        if cue == cueanexos:
                            color = 'red'
                        else:
                            color = 'blue'
                        filtered_rows.append((cue, lat, lng, nom_est, oferta, ambito, sector, region_loc, calle, numero, loc, color))

                # Calcular el centro y los datos cercanos
                if cueanexos and radio:
                    center_lat, center_lng = filtered_rows[0][1], filtered_rows[0][2]
                    nearby_rows = execute_query(cursor, """
                        SELECT cueanexo, lat, long, nom_est, oferta, ambito, sector, region_loc, calle, numero, localidad, 
                        ST_Distance(ST_MakePoint(%s, %s)::geography, ST_MakePoint(long, lat)::geography) AS distance
                        FROM v_capa_unica_ofertas
                        WHERE cueanexo <> %s AND ST_Distance(ST_MakePoint(%s, %s)::geography, ST_MakePoint(long, lat)::geography) <= %s;
                    """, (center_lng, center_lat, cueanexos, center_lng, center_lat, radio))

                    # Filtrar datos cercanos
                    for row in nearby_rows:
                        filtered_rows.append(row[:11] + ('green',))

                    # Calcular distancia a comisarías
                    comisarias_filtered_rows = []
                    comisarias = execute_query(cursor, "SELECT nom_cria, direccion, telefono, lat, long FROM public.comisarias")
                    for comisaria in comisarias:
                        nom_cria, direccion, telefono, lat, long = comisaria
                        distance = calculate_distance(cursor, center_lng, center_lat, long, lat)
                        if distance is not None and float(radio) >= distance:
                            comisarias_filtered_rows.append((nom_cria, lat, long, telefono, direccion, 'purple'))
                    print('comisarias:',comisarias_filtered_rows)
                    
                    # Calcular distancia a centros de salud
                    salud_filtered_rows = []
                    salud = execute_query(cursor, "SELECT tipo, telefono, lat, long, enlace FROM public.salud")
                    for centro in salud:
                        tipo, telefono, lat, long, enlace = centro
                        distance = calculate_distance(cursor, center_lng, center_lat, long, lat)
                        if distance is not None and float(radio) >= distance:
                            salud_filtered_rows.append((tipo, lat, long, telefono, enlace, 'purple'))
                    print('salud:',salud_filtered_rows)
                    
                    # Calcular distancia a paradas de colectivos
                    colectivos_filtered_rows=[]
                    colectivos=execute_query(cursor, "SELECT codigo, direccion, lat, long, lineas FROM public.colectivos_par")
                    for omnibus in colectivos:
                        codigo, direccion, lat, long, lineas = omnibus
                        distance=calculate_distance(cursor, center_lng, center_lat, long, lat)
                        if distance is not None and float(radio)>=distance:
                            colectivos_filtered_rows.append((codigo,direccion, lineas,lat, long, 'black'))
                    print('colectivos:',colectivos_filtered_rows)
                    
        context = {
            'title': 'Mapa',
            'data_json': json.dumps(filtered_rows),
            'comisarias_data_json': json.dumps(comisarias_filtered_rows),
            'hospitales_data_json': json.dumps(salud_filtered_rows),
            'colectivos_data_json':json.dumps(colectivos_filtered_rows),
            'center_lat': center_lat,
            'center_lng': center_lng,
            'radio': radio,
            'cueanexo': cueanexos,
        }
        return render(request, 'mapa/cueradio.html', context)
