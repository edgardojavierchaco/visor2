import json, psycopg2, logging
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.shortcuts import render
from django.db import connection
from django.views.decorators.http import require_GET
from .models import RegionalesGeometria, LocalidadesRegion
from django.core.serializers import serialize

def filtrado_cueradio(request):
    return render(request,'mapa/filter_cuearadio.html')

def filtrado_establecimiento(request):
    return render(request,'mapa/filter_cueradioxestablecimiento.html')


#####################################################################
#      PARA RENDERIZAR LOS MARCADORES EN EL MAPA DE LEAFLET         #
#####################################################################

# Configuración básica del logging
logging.basicConfig(level=logging.ERROR, format='%(asctime)s - %(levelname)s - %(message)s')

@csrf_exempt
def filter_cueradio(request):
    try:
        if request.method == 'POST':
            cueanexos = request.POST.get('Cueanexo')
            radio = request.POST.get('Radio')  # Captura el valor del campo de radio       
           
            # Realizar la consulta en la base de datos
            cursor = connection.cursor()
            query = "SELECT cueanexo, lat, long, nom_est, oferta, ambito, sector, region_loc, calle, numero, localidad FROM v_capa_unica_ofertas WHERE 1=1"
            parameters = []

            if cueanexos:
                query += " AND cueanexo = %s"
                parameters.append(cueanexos)

            try:
                cursor.execute(query, parameters)
                rows = cursor.fetchall()
            except Exception as e:
                logging.error(f"Error ejecutando la consulta principal: {str(e)}")
                return render(request, 'error.html', {'error': f"Error ejecutando la consulta principal: {str(e)}"})

            filtered_rows = []

            # Filtrar los marcadores con latitud y longitud distintas de 0 o vacías
            if cueanexos:
                for row in rows:
                    cue, lat, lng, nom_est, oferta, ambito, sector, region_loc, calle, numero, loc = row
                    if lat != 0 and lng != 0:
                        if cue == cueanexos:
                            filtered_rows.append((cue, lat, lng, nom_est, oferta, ambito, sector, region_loc, calle, numero, loc, 'red'))
                        else:
                            filtered_rows.append((cue, lat, lng, nom_est, oferta, ambito, sector, region_loc, calle, numero, loc, 'blue'))

            # Verificar que haya al menos una fila filtrada para obtener las coordenadas del centro
            if not filtered_rows:
                logging.error("No se encontraron filas filtradas con las coordenadas especificadas.")
                return render(request, 'error.html', {'error': "No se encontraron filas filtradas con las coordenadas especificadas."})

            center_lat, center_lng = (filtered_rows[0][1], filtered_rows[0][2])
            logging.info(f"Coordenadas del punto central: {center_lat}, {center_lng}")

            # Obtener los nombres de las columnas
            column_names = [desc[0] for desc in cursor.description]

            # Consulta para obtener los puntos cercanos en función del radio especificado
            if cueanexos and radio:
                try:
                    cursor.execute("""
                        SELECT cueanexo, lat, long, nom_est, oferta, ambito, sector, region_loc, calle, numero, localidad, 
                        ST_Distance(ST_MakePoint(%s, %s)::geography, ST_MakePoint(long, lat)::geography) AS distance
                        FROM v_capa_unica_ofertas
                        WHERE cueanexo <> %s AND ST_Distance(ST_MakePoint(%s, %s)::geography, ST_MakePoint(long, lat)::geography) <= %s;
                    """, (center_lng, center_lat, cueanexos, center_lng, center_lat, radio))
                    nearby_rows = cursor.fetchall()
                    for row in nearby_rows:
                        filtered_rows.append((row[0], row[1], row[2], row[3], row[4], row[5], row[6], row[7], row[8], row[9], row[10], 'green'))
                except Exception as e:
                    logging.error(f"Error ejecutando la consulta de puntos cercanos: {str(e)}")
                    return render(request, 'error.html', {'error': f"Error ejecutando la consulta de puntos cercanos: {str(e)}"})

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
            return render(request, 'mapa/cueradio.html', context)

    except Exception as general_error:
        logging.error(f"Error inesperado: {str(general_error)}")
        return render(request, 'error.html', {'error': f"Error inesperado: {str(general_error)}"})


def obtener_geometria(request):
    # Serializar los datos a formato GeoJSON
    geometries = RegionalesGeometria.objects.all()    
     
    geojson_data = serialize('geojson', geometries, geometry_field='geom', fields=('region_pad', 'TITULO'))
    print(geojson_data)
    return render(request, 'mapa/regionales.html', {'geometries': geojson_data})


def get_region_data(request):
    region_pad = request.GET.get('region_pad', None)
    if region_pad:
        with connection.cursor() as cursor:
            # Primera consulta para obtener el director
            query1 = "SELECT DISTINCT nom_dir,tel_dir,email_dir FROM public.localidadesregion WHERE reg = %s"
            cursor.execute(query1, [region_pad])
            row1 = cursor.fetchone()
            
            # Segunda consulta para obtener todas las localidades
            query2 = "SELECT loc_reg FROM public.localidadesregion WHERE reg = %s"
            cursor.execute(query2, [region_pad])
            rows2 = cursor.fetchall()  # Utilizamos fetchall() para obtener todas las filas

        # Datos del director
        data = {
            'region_pad': region_pad,
            'director': row1[0] if row1 else 'No disponible',
            'telefono': row1[1] if row1 else 'No disponible',
            'email': row1[2] if row1 else 'No disponible',
        }

        # Datos de localidades: convertimos las filas en una lista
        localidades = [row[0] for row in rows2] if rows2 else ['No disponible']
        data1 = {
            'localidades': localidades
        }

        # Combinar ambas respuestas en una sola
        response_data = {**data, **data1}
        return JsonResponse(response_data)

    return JsonResponse({'error': 'No region_pad provided'}, status=400)