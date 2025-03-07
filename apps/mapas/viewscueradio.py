import json, psycopg2, logging
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render
from django.db import connection
from django.views.decorators.http import require_GET
from .models import RegionalesGeometria, LocalidadesRegion
from django.core.serializers import serialize

def filtrado_cueradio(request):
    """
    Renderiza la plantilla para el filtrado de datos en el mapa de cueras.
    
    Args:
        request (HttpRequest): La solicitud HTTP que se está manejando.

    Returns:
        HttpResponse: La respuesta renderizada con la plantilla 'mapa/filter_cuearadio.html'.
    """
    
    return render(request,'mapa/filter_cuearadio.html')

def filtrado_establecimiento(request):
    """
    Renderiza la plantilla para el filtrado de establecimientos en el mapa.

    Args:
        request (HttpRequest): La solicitud HTTP que se está manejando.

    Returns:
        HttpResponse: La respuesta renderizada con la plantilla 'mapa/filter_cueradioxestablecimiento.html'.
    """
    
    return render(request,'mapa/filter_cueradioxestablecimiento.html')


#####################################################################
#      PARA RENDERIZAR LOS MARCADORES EN EL MAPA DE LEAFLET         #
#####################################################################

# Configuración básica del logging
logging.basicConfig(level=logging.ERROR, format='%(asctime)s - %(levelname)s - %(message)s')

@csrf_exempt
def filter_cueradio(request):
    """
    Filtra los datos de cueras y los devuelve en un formato adecuado para ser renderizados en un mapa.
    
    Args:
        request (HttpRequest): La solicitud HTTP que se está manejando, esperándose que sea un POST con datos.

    Returns:
        HttpResponse: La respuesta renderizada con los datos filtrados en 'mapa/cueradio.html', o un JsonResponse en caso de error.
    """
    
    if request.method == 'POST':
        try:
            cueanexos = request.POST.get('Cueanexo')
            radio = request.POST.get('Radio')  

            
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

            # Verifica que haya al menos una fila filtrada para obtener las coordenadas del centro
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

    else:
        return JsonResponse({'error': 'Método no permitido'}, status=405)


def obtener_geometria(request):
    """
    Obtiene y serializa las geometrías de las regiones en formato GeoJSON.

    Args:
        request (HttpRequest): La solicitud HTTP que se está manejando.

    Returns:
        HttpResponse: La respuesta renderizada con los datos en 'mapa/regionales.html', o un JsonResponse en caso de error.
    """
    
    # Serializar los datos a formato GeoJSON
    try:
        geometries = RegionalesGeometria.objects.all()   
        print(geometries)
        
        if not geometries.exists():
            return JsonResponse({'error': 'Ninguna geometría encontrada'}, status=404) 
        
        # Serializar los datos a formato GeoJSON
        geojson_data = serialize('geojson', geometries, geometry_field='geom', fields=('region_pad', 'TITULO'))
        print(geojson_data)
        
        return render(request, 'mapa/regionales.html', {'geometries': geojson_data})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
    


def get_region_data(request):
    """
    Obtiene información sobre la región y sus localidades en base a un 'region_pad'.

    Args:
        request (HttpRequest): La solicitud HTTP que se está manejando, debe contener el parámetro 'region_pad'.

    Returns:
        JsonResponse: Un JsonResponse con los datos de la región y localidades, o un error en caso de fallo.
    """
    
    region_pad = request.GET.get('region_pad', None)
    if region_pad:
        try:
            with connection.cursor() as cursor:
                # consulta para obtener el director
                query1 = "SELECT DISTINCT nom_dir,tel_dir,email_dir FROM public.localidadesregion WHERE reg = %s"
                cursor.execute(query1, [region_pad])
                row1 = cursor.fetchone()
                
                # consulta para obtener todas las localidades
                query2 = "SELECT loc_reg FROM public.localidadesregion WHERE reg = %s"
                cursor.execute(query2, [region_pad])
                rows2 = cursor.fetchall()  

            # Datos del director
            data = {
                'region_pad': region_pad,
                'director': row1[0] if row1 else 'No disponible',
                'telefono': row1[1] if row1 else 'No disponible',
                'email': row1[2] if row1 else 'No disponible',
            }

            # Datos de localidades: convierte las filas en una lista
            localidades = [row[0] for row in rows2] if rows2 else ['No disponible']
            data1 = {
                'localidades': localidades
            }

            # Combinar ambas respuestas 
            response_data = {**data, **data1}
            return JsonResponse(response_data)
        except Exception as e:
            return JsonResponse({'error':str(e)}, status=500)

    return JsonResponse({'error': 'No region_pad provided'}, status=400)


def obtener_geometria2(request):
    """
    Obtiene y serializa las geometrías filtradas por 'region_pad' en formato GeoJSON.

    Args:
        request (HttpRequest): La solicitud HTTP que se está manejando.

    Returns:
        HttpResponse: La respuesta renderizada con los datos en 'mapa/regionaleselec.html', o un JsonResponse en caso de error.
    """
    
    # Obtener el valor del filtro desde la solicitud (por ejemplo, a través de parámetros GET)
    #region_pad = request.GET.get('region_pad')
    
    region_pad='R.E. 10-C'

    try:
        # Filtrar por el campo region_pad
        geometries = RegionalesGeometria.objects.filter(region_pad=region_pad)
        print('geometria:',geometries)
        
        if not geometries.exists():
            return JsonResponse({'error': 'Ninguna geometría encontrada'}, status=404) 
        
        # Serializar los datos a formato GeoJSON
        geojson_data = serialize('geojson', geometries, geometry_field='geom', fields=('region_pad', 'TITULO'))
        print('geojson:',geojson_data)
        
        return render(request, 'mapa/regionaleselec.html', {'geometries': geojson_data})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)