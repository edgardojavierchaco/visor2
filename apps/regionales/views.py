from django.shortcuts import render
from django.contrib.gis.geos import Point, Polygon
from shapely.geometry import shape
import json

def regionalesview(request):
    # Cargar el archivo GeoJSON
    with open('Regiones.geojson', 'r') as f:
        geojson_data = json.load(f)

    # Obtener las características (features) del GeoJSON
    features = geojson_data['features']

    # Lista para almacenar las coordenadas de los polígonos
    perimeter_coords = []

    # Iterar sobre las características y extraer las coordenadas de los polígonos
    for feature in features:
        geometry = feature['geometry']
        # Convertir la geometría en un objeto shapely
        shapely_geom = shape(geometry)
        # Si la geometría es un MultiPolygon, extraer las coordenadas
        if shapely_geom.geom_type == 'MultiPolygon':
            for polygon in shapely_geom.geoms:  # Utilizamos la propiedad geoms
                perimeter_coords.append(list(polygon.exterior.coords))
        # Si es un Polygon, solo hay un conjunto de coordenadas
        elif shapely_geom.geom_type == 'Polygon':
            perimeter_coords.append(list(shapely_geom.exterior.coords))
        print(perimeter_coords)
    return render(request, 'mapa/regionales.html', {'perimeter_coords': perimeter_coords})
