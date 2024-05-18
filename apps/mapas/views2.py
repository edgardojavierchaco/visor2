import psycopg2
import json
from django.shortcuts import render

def mapapuntos(request):
    return render(request, 'mapa/mapa.html')

def obtenerdatos(request):
    # Conectarse a la base de datos
    connection = psycopg2.connect(
        host='relevamientoanual.com.ar',            
        user='visualizador',
        password='Estadisticas24',
        database='visualizador'
    )

    # Realizar la consulta en la base de datos
    cursor = connection.cursor()
    query = "SELECT cueanexo, lat, long, nom_est, oferta, ambito, sector, region_loc, calle, numero, localidad FROM v_capa_unica_ofertas"
    cursor.execute(query)
    rows = cursor.fetchall()

    # Filtrar las filas con coordenadas válidas
    filtered_rows = [(cueanexo, lat, long, nom_est, oferta, ambito, sector, region_loc, calle, numero, localidad) 
                     for cueanexo, lat, long, nom_est, oferta, ambito, sector, region_loc, calle, numero, localidad in rows 
                     if lat is not None and long is not None]

    # Convertir los datos a GeoJSON
    print(filtered_rows)
    features = []
    for row in filtered_rows:
        cueanexo, lat, long, nom_est, oferta, ambito, sector, region_loc, calle, numero, localidad = row
        feature = {
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [float(long), float(lat)]  # Cambiar a longitud, latitud si la base de datos almacena longitud primero
            },
            "properties": {
                "cueanexo": cueanexo,
                "nom_est": nom_est,
                "oferta": oferta,
                "ambito": ambito,
                "sector": sector,
                "region_loc": region_loc,
                "calle": calle,
                "numero": numero,
                "localidad": localidad
            }
        }
        features.append(feature)

    geojson_data = {
        "type": "FeatureCollection",
        "features": features
    }
    print(geojson_data)
    # Cerrar la conexión a la base de datos
    cursor.close()
    connection.close()

    # Pasar el GeoJSON al template
    return render(request, 'mapa/mapa.html', {'geojson_data': json.dumps(geojson_data)})