import json
from django.shortcuts import render
from django.db import connection
from django.http import JsonResponse
from django.views.decorators.cache import cache_page

def mapapuntos(request):
    """
    Renderiza la plantilla del mapa.

    Esta vista simplemente carga la plantilla HTML 'mapa/mapa.html', donde se
    mostrará el mapa interactivo que puede luego cargar puntos a través de
    peticiones AJAX o a través de un contexto pasado desde otras vistas.

    Args:
        request: El objeto HttpRequest que contiene metadatos sobre la solicitud.

    Returns:
        HttpResponse: Renderiza la plantilla 'mapa/mapa.html'.
    """
    
    return render(request, 'mapa/mapa.html')

@cache_page(60 * 5)
def obtenerdatos(request):

    oferta = request.GET.get("oferta")
    region = request.GET.get("region")
    sector = request.GET.get("sector")

    filtros = []
    params = []

    if oferta:
        filtros.append("oferta = %s")
        params.append(oferta)

    if region:
        filtros.append("region_loc = %s")
        params.append(region)

    if sector:
        filtros.append("sector = %s")
        params.append(sector)

    where = " AND ".join(filtros)
    if where:
        where = " AND " + where

    query = f"""
        SELECT cueanexo, lat, long, nom_est, oferta, ambito,
               sector, region_loc, calle, numero, localidad
        FROM v_capa_unica_ofertas_ant
        WHERE lat IS NOT NULL AND long IS NOT NULL
        {where}
    """

    with connection.cursor() as cursor:
        cursor.execute(query, params)
        columns = [col[0] for col in cursor.description]

        features = []
        for row in cursor.fetchall():
            d = dict(zip(columns, row))

            features.append({
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [float(d["long"]), float(d["lat"])]
                },
                "properties": d
            })

    return JsonResponse({
        "type": "FeatureCollection",
        "features": features
    })

def mapa_view(request):
    return render(request, "mapa/mapa.html")

#####################################################################
#          PARA MOSTRAR LISTADO DESDE ESTABLECIMIENTOS              #
#####################################################################
def obtener_datos_ofertas(request):
    """
    Consulta y obtiene datos de ofertas educativas desde la base de datos.

    Esta función realiza una consulta a la base de datos para obtener información
    sobre los establecimientos educativos y las ofertas asociadas, incluyendo 
    nombre del establecimiento, tipo de oferta, ámbito, sector, y localidad. 
    Los datos se envían al template 'listadoestablecimientos.html'.

    Args:
        request: El objeto HttpRequest que contiene metadatos sobre la solicitud.

    Returns:
        HttpResponse: Renderiza la plantilla 'mapa/listadoestablecimientos.html' con los datos de las ofertas.
        Si no se encuentran resultados, renderiza 'consulta_vacia.html'.
    """
    
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT cueanexo, nom_est, oferta, ambito, sector, localidad 
            FROM v_capa_unica_ofertas_ant
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