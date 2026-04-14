import logging
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.db import connection

logger = logging.getLogger(__name__)


def mapa_salud(request):
    return render(request, 'mapa/cueradiosalud.html')


@csrf_exempt
def api_salud(request):

    if request.method != 'POST':
        return JsonResponse({'error': 'Método no permitido'}, status=405)

    cueanexo = request.POST.get('Cueanexo')
    radio = request.POST.get('Radio')

    if not cueanexo:
        return JsonResponse({'error': 'Debe proporcionar CUE'}, status=400)

    try:
        with connection.cursor() as cursor:

            # 🔥 Centro
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

            lat, lng, nombre = row

            markers = [{
                "tipo": "establecimiento",
                "lat": lat,
                "lng": lng,
                "nombre": nombre
            }]

            # 🔥 Salud cercana
            if radio:
                cursor.execute("""
                    SELECT lat, long, tipo, telefono, enlace
                    FROM salud
                    WHERE ST_DWithin(
                        ST_MakePoint(%s, %s)::geography,
                        ST_MakePoint(long, lat)::geography,
                        %s
                    );
                """, [lng, lat, radio])

                for r in cursor.fetchall():
                    markers.append({
                        "tipo": (r[2] or "OTRO").strip().upper(),
                        "lat": r[0],
                        "lng": r[1],
                        "telefono": r[3],
                        "enlace": r[4]
                    })

        return JsonResponse({
            "center": {"lat": lat, "lng": lng},
            "markers": markers
        })

    except Exception as e:
        logger.exception("Error salud")
        return JsonResponse({'error': str(e)}, status=500)