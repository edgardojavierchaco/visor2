# apps/sirtee/api/views_select2.py

from django.http import JsonResponse
from django.views.decorators.http import require_GET
from django.db import connection


@require_GET
def escuelas_select2(request):
    term = request.GET.get("q", "")

    sql = """
        SELECT cueanexo, nom_est, cui_loc, oferta
        FROM v_capa_unica_ofertas_ant
        WHERE cueanexo ILIKE %s
           OR nom_est ILIKE %s
        ORDER BY nom_est
        LIMIT 20
    """

    like = f"%{term}%"

    with connection.cursor() as cursor:
        cursor.execute(sql, [like, like])
        rows = cursor.fetchall()

    results = [
        {
            "id": r[0],
            "text": f"{r[0]} - {r[1]} ({r[3]})",
            "nom_est": r[1],
            "cui": r[2],
            "oferta": r[3],
        }
        for r in rows
    ]

    return JsonResponse({"results": results})