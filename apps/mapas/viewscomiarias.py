import json, psycopg2, logging
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render
from django.db import connection
from django.views.decorators.http import require_GET
from .models import RegionalesGeometria, LocalidadesRegion
from django.core.serializers import serialize

def filtrado_cueradiocomisarias(request):    
    return render(request, 'mapa/filter_comisarias.html')
    

@csrf_exempt
def filter_cueradiocomisarias(request):
    if request.method == 'POST':
        try:
            cueanexos = request.POST.get('Cueanexo')
            radio = request.POST.get('Radio')  

            # consulta en la base de datos
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
                        filtered_rows.append((cue, lat, lng, nom_est, oferta, ambito, sector, region_loc, calle, numero, loc, 'red'))

            # Verificar que haya al menos una fila filtrada para obtener las coordenadas del centro
            if not filtered_rows:
                logging.error("No se encontraron filas filtradas con las coordenadas especificadas.")
                return render(request, 'error.html', {'error': "No se encontraron filas filtradas con las coordenadas especificadas."})

            center_lat, center_lng = (filtered_rows[0][1], filtered_rows[0][2])
            logging.info(f"Coordenadas del punto central: {center_lat}, {center_lng}")

            # Obtener los nombres de las columnas
            column_names = [desc[0] for desc in cursor.description]

            # Consulta para obtener las líneas de colectivos cercanas en función del radio especificado
            if cueanexos and radio:
                try:
                    cursor.execute("""
                        SELECT long, lat, nom_cria, direccion, telefono,
                        ST_Distance(ST_MakePoint(%s, %s)::geography, ST_MakePoint(long, lat)::geography) AS distance
                        FROM public.comisarias
                        WHERE ST_Distance(ST_MakePoint(%s, %s)::geography, ST_MakePoint(long, lat)::geography) <= %s;
                    """, (center_lng, center_lat, center_lng, center_lat, radio))
                    nearby_lines = cursor.fetchall()
                    
                    for line in nearby_lines:
                        filtered_rows.append((line[2], line[1], line[0], line[3],line[4], 'green'))
                    print('filas:',filtered_rows)
                except Exception as e:
                    logging.error(f"Error ejecutando la consulta de colectivos cercanos: {str(e)}")
                    return render(request, 'error.html', {'error': f"Error ejecutando la consulta de colectivos cercanos: {str(e)}"})

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
            print('contexto:',context)
            return render(request, 'mapa/cueradiocomisarias.html', context)
            
        except Exception as general_error:
            logging.error(f"Error inesperado: {str(general_error)}")
            return render(request, 'error.html', {'error': f"Error inesperado: {str(general_error)}"})

    else:
        return JsonResponse({'error': 'Método no permitido'}, status=405)
