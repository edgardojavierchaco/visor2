from django.shortcuts import render
from django.contrib.gis.geos import Point
from shapely.geometry import MultiPoint
import psycopg2

def regionalesview(request):
    # Supongamos que tienes una lista de cueanexo que quieres pasar al query
    lista_cueanexo = ['220005800','220005801','220005807','220005809']

    # Crear la lista de cueanexo en formato de cadena separada por comas
    lista_cueanexo_str = ','.join([f"'{cueanexo}'" for cueanexo in lista_cueanexo])

    # Construir la consulta SQL con la lista de cueanexo filtrados
    coordenadas = f"SELECT cueanexo, lat, long FROM v_capa_unica_ofertas WHERE cueanexo IN ({lista_cueanexo_str})"

    # Realizar la conexión a la base de datos y ejecutar la consulta
    conn = psycopg2.connect(
        database="visualizador", 
        user="visualizador", 
        password="Estadisticas24", 
        host="sigechaco.com.ar", 
        port="5432"
    )
    cursor = conn.cursor()
    cursor.execute(coordenadas)

    # Obtener los resultados de la consulta
    resultados = cursor.fetchall()

    # Filtrar las coordenadas para eliminar los valores nulos o vacíos
    markers_coords = [(float(row[1]), float(row[2])) for row in resultados if row[1] is not None and row[2] is not None]

    # Si no hay coordenadas válidas, retornar un mensaje de error
    if not markers_coords:
        return render(request, 'mapa/error.html', {'error_message': 'No se encontraron coordenadas válidas para mostrar.'})

    # Convertir las coordenadas de los marcadores en objetos Point de Django
    points = [Point(lat, lon) for lat, lon in markers_coords]

    # Crear un objeto MultiPoint de Shapely
    multi_point = MultiPoint(points)

    # Calcular el contorno convexo
    convex_hull = multi_point.convex_hull

    # Obtener las coordenadas del contorno convexo
    perimeter_coords = list(convex_hull.exterior.coords)
    
    for coord in perimeter_coords:
        lat_lon_pair = [coord[i] for i in range(0, len(coord), 2)]
        perimeter_coords.append(lat_lon_pair)
    print(perimeter_coords)
    
    # Cerrar el cursor y la conexión
    cursor.close()
    conn.close()

    return render(request, 'mapa/regionales.html', {'perimeter_coords': perimeter_coords})
