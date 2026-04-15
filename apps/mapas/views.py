import json
import os
from django.conf import settings
from django.shortcuts import render
from .services import OfertaEducativaService
from django.http import JsonResponse
from django.db import connection

def filtrado(request):    
    return render(request, 'mapa/filter.html')


def filter_data(request):
    params = request.POST if request.method == 'POST' else {}

    context = OfertaEducativaService.filtrar_ofertas_mapa(params)
    context['title'] = 'Mapa'

    indec_geojson = {"type": "FeatureCollection", "features": []}

    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT geojson
                FROM public.v_radios_censales_chaco_geojson
            """)
            row = cursor.fetchone()

        if row and row[0]:
            geo = row[0]

            # ============================
            # 🔍 DEBUG 1: tipo de dato
            # ============================
            print("\n🧭 TYPE GEOJSON:", type(geo))

            # ============================
            # 🔍 DEBUG 2: normalizar JSON
            # ============================
            if isinstance(geo, str):
                geo = json.loads(geo)

            indec_geojson = geo

            # ============================
            # 🔍 DEBUG 3: resumen general
            # ============================
            features = geo.get("features", [])
            print("\n📦 TOTAL FEATURES:", len(features))

            # ============================
            # 🔍 DEBUG 4: muestra primeros 3
            # ============================
            print("\n📍 SAMPLE FEATURES (primeros 3):")

            for i, f in enumerate(features[:3]):
                print(f"\n--- FEATURE {i} ---")

                props = f.get("properties", {})
                geom = f.get("geometry", {})

                print("properties:", props)
                print("geometry_type:", geom.get("type") if geom else None)
                print("has_coordinates:", "coordinates" in geom if geom else False)

            # ============================
            # 🔍 DEBUG 5: detectar errores
            # ============================
            invalid = []

            for i, f in enumerate(features):
                geom = f.get("geometry")

                if not geom:
                    invalid.append((i, "NO_GEOMETRY"))
                elif not geom.get("coordinates"):
                    invalid.append((i, "NO_COORDINATES"))

            print("\n🚨 FEATURES INVALIDOS:", len(invalid))

            if invalid[:10]:
                print("\n❌ EJEMPLOS DE ERRORES:")
                for i, reason in invalid[:10]:
                    print(f" - Feature {i}: {reason}")

            # ============================
            # 🔍 DEBUG 6: bounds check rápido
            # ============================
            print("\n✔ GEOJSON LISTO PARA FRONTEND")

    except Exception as e:
        print("\n⚠️ ERROR CARGANDO RADIOS:", e)

    context['indec_geojson'] = indec_geojson
    
    
    # =========================================================
    # 🛣️ RED VIAL IGN (PostGIS → GeoJSON)
    # =========================================================
    vial_geojson = {"type": "FeatureCollection", "features": []}

    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT jsonb_build_object(
                    'type', 'FeatureCollection',
                    'features', jsonb_agg(feature)
                )
                FROM (
                    SELECT jsonb_build_object(
                        'type', 'Feature',
                        'geometry', ST_AsGeoJSON(geom)::jsonb,
                        'properties', jsonb_build_object(
                            'rtn', rtn,
                            'typ', typ,
                            'rst', rst
                        )
                    ) AS feature
                    FROM (
                        SELECT 
                            rtn,
                            typ,
                            rst,
                            ST_LineMerge(
                                ST_UnaryUnion(
                                    ST_SnapToGrid(
                                        ST_Collect(
                                            ST_Transform(geom, 4326)
                                        ), 0.00001
                                    )
                                )
                            ) AS geom
                        FROM public.vial_provincial
                        WHERE typ = '40'
                        GROUP BY rtn, typ, rst
                    ) t
                ) fc;
            """)

            row_vial = cursor.fetchone()

        if row_vial and row_vial[0]:
            vial_geojson = row_vial[0]

            if isinstance(vial_geojson, str):
                vial_geojson = json.loads(vial_geojson)

    except Exception as e:
        print("⚠️ ERROR VIAL PROVINCIAL:", e)

    context['vial_geojson'] = vial_geojson
    
    # =========================================================
    # 🔍 DEBUG
    # =========================================================
    print("✔ VIAL OK:", len(vial_geojson.get("features", [])))
    
    
    # =========================================================
    # 📍 PARAJES CHACO (PostGIS → GeoJSON)
    # =========================================================
    parajes_geojson = {"type": "FeatureCollection", "features": []}

    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT jsonb_build_object(
                    'type', 'FeatureCollection',
                    'features', jsonb_agg(feature)
                )
                FROM (
                    SELECT jsonb_build_object(
                        'type', 'Feature',
                        'geometry', ST_AsGeoJSON(ST_Transform(geom, 4326))::jsonb,
                        'properties', jsonb_build_object(
                            'id', id,
                            'cod_pcia', cod_pcia,
                            'nom_pcia', nom_pcia,
                            'cod_depto', cod_depto,
                            'nom_depto', nom_depto,
                            'cod_ase', cod_ase,
                            'fna', fna,
                            'tipo_asent', tipo_asent,
                            'nom_agl', nom_agl,
                            'lat', lat_gd,
                            'lng', long_gd
                        )
                    ) AS feature
                    FROM public.parajes_chaco
                    WHERE geom IS NOT NULL
                ) fc;
            """)

            row_parajes = cursor.fetchone()

        if row_parajes and row_parajes[0]:
            parajes_geojson = row_parajes[0]

            if isinstance(parajes_geojson, str):
                parajes_geojson = json.loads(parajes_geojson)

            print("\n📍 PARAJES FEATURES:", len(parajes_geojson.get("features", [])))

    except Exception as e:
        print("⚠️ ERROR PARAJES:", e)

    context['parajes_geojson'] = parajes_geojson
    
    # =========================================================
    # 🔍 DEBUG
    # =========================================================
    print("✔ PARAJES OK:", len(parajes_geojson.get("features", [])))

    return render(request, 'mapa/ofertasmark.html', context)
    

def filter_listado_map(request):
    params = request.POST if request.method == 'POST' else {}
    context = OfertaEducativaService.filtrar_ofertas_mapa(params)
    return render(request, 'publico/listadomap.html', context)

def filtrar_tablas_view(request):
    cueanexo = request.GET.get('cueanexo')
    oferta_rec = request.GET.get('oferta')

    if not cueanexo:
        return render(request, 'error.html', {'mensaje': 'No se proporcionó cueanexo'})

    try:
        inst, planes, anexos, ofertas_lista, matricula = OfertaEducativaService.obtener_detalle_completo(cueanexo, oferta_rec)
        
        context = {
            'resultados': inst,
            'resultados1': planes,
            'resultados2': anexos,
            'resultados3': ofertas_lista,
            'resultados_detalle': [matricula] if matricula else []
        }
        return render(request, 'mapa/otro_template.html', context)
    except Exception as e:
        import traceback
        print(traceback.format_exc()) # Esto imprimirá el error real en tu consola negra (terminal)
        return render(request, 'error.html', {'mensaje': f'Error técnico: {str(e)}'})