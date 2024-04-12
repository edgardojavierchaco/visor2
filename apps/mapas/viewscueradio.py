import json
import psycopg2
import asyncpg # type: ignore
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt


def filtrado_cueradio(request):
    return render(request,'mapa/filter_cuearadio.html')

#####################################################################
#      PARA RENDERIZAR LOS MARCADORES EN EL MAPA DE LEAFLET         #
#####################################################################

@csrf_exempt
def filter_cueradio(request):
    if request.method == 'POST':
        cueanexos = request.POST.get('Cueanexo')
        radio = request.POST.get('Radio')  # Captura el valor del campo de radio        

        # Conectarse a la base de datos
        connection = psycopg2.connect(
            host='sigechaco.com.ar',
            user='visualizador',
            password='Estadisticas24',
            database='visualizador'
        )

        # Realizar la consulta en la base de datos
        cursor = connection.cursor()
        query = "SELECT cueanexo, lat, long, nom_est, oferta, ambito, sector, region_loc, calle, numero, localidad FROM v_capa_unica_ofertas WHERE 1=1"
        parameters = []

        if cueanexos:
            query += " AND cueanexo = %s"
            parameters.append(cueanexos)

        cursor.execute(query, parameters)
        rows = cursor.fetchall()

        filtered_rows = []

        if cueanexos:
            # Filtrar los marcadores con latitud y longitud distintas de 0 o vacías
            for row in rows:
                cue, lat, lng, nom_est, oferta, ambito, sector, region_loc, calle, numero, loc = row
                if lat != 0 and lng != 0:
                    if cue == cueanexos:
                        filtered_rows.append((cue, lat, lng, nom_est, oferta, ambito, sector, region_loc, calle, numero, loc, 'red'))
                    else:
                        filtered_rows.append((cue, lat, lng, nom_est, oferta, ambito, sector, region_loc, calle, numero, loc, 'blue'))
        
        # Obtener las coordenadas del punto central
        center_lat, center_lng = (filtered_rows[0][1], filtered_rows[0][2])
        print(center_lat,center_lng)
        # Obtener los nombres de las columnas
        column_names = [desc[0] for desc in cursor.description]

        # Consulta para obtener los puntos cercanos en función del radio especificado
        if cueanexos and radio:
            cursor.execute("""
                SELECT cueanexo, lat, long, nom_est, oferta, ambito, sector, region_loc, calle, numero, localidad, 
                ST_Distance(ST_MakePoint(%s, %s)::geography, ST_MakePoint(long, lat)::geography) AS distance
                FROM v_capa_unica_ofertas
                WHERE cueanexo <> %s AND ST_Distance(ST_MakePoint(%s, %s)::geography, ST_MakePoint(long, lat)::geography) <= %s;
            """, (center_lng, center_lat, cueanexos, center_lng, center_lat, radio))
            nearby_rows = cursor.fetchall()
            for row in nearby_rows:
                filtered_rows.append((row[0], row[1], row[2], row[3], row[4], row[5], row[6], row[7], row[8], row[9], row[10], 'green'))

        # Cerrar la conexión a la base de datos
        cursor.close()
        connection.close()

        context = {
            'title': 'Mapa',
            'data_json': json.dumps(filtered_rows),
            'column_names_json': json.dumps(column_names),
            'center_lat': center_lat,
            'center_lng': center_lng,
            'radio': radio,
            'cueanexo': cueanexos,
        }
        print(context)
        # Abrir el template en el navegador con los marcadores como contexto
        return render(request, 'publico/baseradio.html', context)
        