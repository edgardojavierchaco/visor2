import json
from django.shortcuts import render
from django.db import connection
from django.http import JsonResponse

def mapapuntos(request):
    return render(request, 'mapa/mapa.html')

def obtenerdatos(request):
    
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


#####################################################################
#          PARA MOSTRAR LISTADO DESDE ESTABLECIMIENTOS              #
#####################################################################
def obtener_datos_ofertas(request):
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT cueanexo, nom_est, oferta, ambito, sector, localidad 
            FROM v_capa_unica_ofertas
        """)
        rows = cursor.fetchall()
        print('rows:',rows)
        datosofertas=[]
        datos_encontrados=len(rows)>0

        # Formateamos los datos en un diccionario
        for row in rows:
            datosofertas.append({
                'cueanexo': row[0],
                'nom_est': row[1],
                'oferta': row[2],
                'ambito': row[3],
                'sector': row[4],
                'localidad': row[5],
            })

        # Cerrar la conexión a la base de datos
        connection.close()
        print('datos de ofertas:',datosofertas)
        print(datos_encontrados)

        if not datos_encontrados:
            return render(request, 'consulta_vacia.html')     

        # Devolver los datos como contexto a la plantilla 'listadoestablecimientos.html'
        return render(request, 'mapa/listadoestablecimientos.html', {'datosofertas': datosofertas})