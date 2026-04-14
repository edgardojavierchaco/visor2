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
        # ===============================
        # 📥 1. Leer GeoJSON
        # ===============================
        path = os.path.join(settings.BASE_DIR, 'static/gis/radios-censales.geojson')

        if os.path.exists(path):
            with open(path, encoding='utf-8') as f:
                data = json.load(f)

            # ===============================
            # 🧠 2. Traer datos de la vista
            # ===============================
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT 
                        link,
                        ofertas,
                        poblacion_total,
                        demanda_inicial,
                        demanda_primaria,
                        demanda_secundaria
                    FROM public.v_radio_demanda_oferta
                """)

                rows = cursor.fetchall()

            # 👉 Convertir a dict para lookup rápido
            data_db = {
                row[0]: {
                    "ofertas": row[1],
                    "poblacion": row[2],
                    "demanda_inicial": row[3],
                    "demanda_primaria": row[4],
                    "demanda_secundaria": row[5],
                }
                for row in rows
            }

            # ===============================
            # 🔥 3. Filtrar + enriquecer
            # ===============================
            filtered_features = []

            for f in data.get("features", []):
                props = f.get("properties", {})

                # FILTRO CHACO
                if props.get("NOMPROV") != "CHACO":
                    continue

                link = props.get("link") or props.get("LINK")

                # 👉 merge con datos de BD
                if link in data_db:
                    props.update(data_db[link])
                else:
                    props.update({
                        "ofertas": 0,
                        "poblacion": 0,
                        "demanda_inicial": 0,
                        "demanda_primaria": 0,
                        "demanda_secundaria": 0,
                    })

                f["properties"] = props
                filtered_features.append(f)

            indec_geojson = {
                "type": "FeatureCollection",
                "features": filtered_features
            }

    except Exception as e:
        print("⚠️ Error cargando INDEC:", e)

    context['indec_geojson'] = indec_geojson

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