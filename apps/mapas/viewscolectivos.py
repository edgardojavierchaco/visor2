import logging
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.db import connection

logger = logging.getLogger(__name__)


@csrf_exempt
def filter_cueradiocolectivo(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Método no permitido'}, status=405)

    cueanexo = request.POST.get('Cueanexo')
    radio = request.POST.get('Radio')

    if not cueanexo:
        return JsonResponse({'error': 'Debe proporcionar un CUE Anexo'}, status=400)

    try:
        with connection.cursor() as cursor:

            # 🔥 1. Obtener punto central
            cursor.execute("""
                SELECT lat, long, nom_est
                FROM v_capa_unica_ofertas
                WHERE cueanexo = %s
                  AND lat IS NOT NULL AND long IS NOT NULL
                  AND lat != 0 AND long != 0
                LIMIT 1;
            """, [cueanexo])

            row = cursor.fetchone()

            if not row:
                return JsonResponse({'error': 'Sin coordenadas'}, status=404)

            center_lat, center_lng, nom_est = row

            # 🔥 2. Marker principal
            markers = [{
                "tipo": "establecimiento",
                "lat": center_lat,
                "lng": center_lng,
                "nombre": nom_est,
                "color": "red"
            }]

            # 🔥 3. Colectivos cercanos
            if radio:
                cursor.execute("""
                    SELECT lat, long, lineas, direccion
                    FROM colectivoss
                    WHERE ST_DWithin(
                        ST_MakePoint(%s, %s)::geography,
                        ST_MakePoint(long, lat)::geography,
                        %s
                    );
                """, [center_lng, center_lat, radio])

                for lat, lng, linea, direccion in cursor.fetchall():
                    markers.append({
                        "tipo": "colectivo",
                        "lat": lat,
                        "lng": lng,
                        "linea": linea,
                        "direccion": direccion,
                        "color": "green"
                    })

        # 🔥 4. RESPUESTA FINAL (JSON)
        return JsonResponse({
            "center": {
                "lat": center_lat,
                "lng": center_lng
            },
            "markers": markers,
            "total": len(markers)
        })

    except Exception as e:
        logger.exception("Error PRO")
        return JsonResponse({'error': str(e)}, status=500)


def mapa_cueradiocolectivo(request):
    return render(request, 'mapa/cueradiocolectivos.html')