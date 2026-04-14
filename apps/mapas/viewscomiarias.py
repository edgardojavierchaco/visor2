import logging
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.db import connection

logger = logging.getLogger(__name__)


def mapa_cueradiocomisarias(request):
    """Renderiza el mapa principal"""
    return render(request, 'mapa/cueradiocomisarias.html')


@csrf_exempt
def filter_cueradiocomisarias(request):

    if request.method != 'POST':
        return JsonResponse({'error': 'Método no permitido'}, status=405)

    cueanexo = request.POST.get('Cueanexo')
    radio = request.POST.get('Radio')

    if not cueanexo:
        return JsonResponse({'error': 'Debe proporcionar un CUE Anexo'}, status=400)

    try:
        with connection.cursor() as cursor:

            # 🔥 1. Obtener punto central (SIN loops)
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
                return JsonResponse({'error': 'Sin coordenadas válidas'}, status=404)

            center_lat, center_lng, nom_est = row

            # 🔥 2. Marker principal
            markers = [{
                "tipo": "establecimiento",
                "lat": center_lat,
                "lng": center_lng,
                "nombre": nom_est,
                "color": "red"
            }]

            # 🔥 3. Comisarías cercanas (ULTRA OPTIMIZADO)
            if radio:
                cursor.execute("""
                    SELECT lat, long, nom_cria, direccion, telefono
                    FROM comisarias
                    WHERE ST_DWithin(
                        ST_MakePoint(%s, %s)::geography,
                        ST_MakePoint(long, lat)::geography,
                        %s
                    );
                """, [center_lng, center_lat, radio])

                for lat, lng, nombre, direccion, telefono in cursor.fetchall():
                    markers.append({
                        "tipo": "comisaria",
                        "lat": lat,
                        "lng": lng,
                        "nombre": nombre,
                        "direccion": direccion,
                        "telefono": telefono,
                        "color": "green"
                    })

        # 🔥 4. RESPUESTA JSON (para frontend moderno)
        return JsonResponse({
            "center": {
                "lat": center_lat,
                "lng": center_lng
            },
            "markers": markers,
            "total": len(markers)
        })

    except Exception as e:
        logger.exception("Error en comisarías")
        return JsonResponse({'error': str(e)}, status=500)