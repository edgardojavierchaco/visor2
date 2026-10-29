"""Territorio de TODOS los establecimientos, no solamente escuelas BII.

La vista v_capa_unica_ofertas_old puede devolver varias filas por CUEANEXO.
Se consolida a una región por CUEANEXO para evitar multiplicar matrícula.
"""
from django.db import connections


def padron_por_cue(cueanexos, using='default'):
    cues = list({str(x).strip() for x in cueanexos if str(x).strip()})
    if not cues:
        return {}
    with connections[using].cursor() as cursor:
        cursor.execute('''
            SELECT BTRIM(cueanexo::text) AS cue,
                   MAX(NULLIF(BTRIM(region_loc::text), '')) AS region,
                   MAX(NULLIF(BTRIM(nom_est::text), '')) AS nombre,
                   MAX(NULLIF(BTRIM(departamento::text), '')) AS departamento,
                   MAX(NULLIF(BTRIM(localidad::text), '')) AS localidad,
                   MAX(NULLIF(BTRIM(ambito::text), '')) AS ambito,
                   MAX(NULLIF(BTRIM(sector::text), '')) AS sector
            FROM public.v_capa_unica_ofertas_old
            WHERE BTRIM(cueanexo::text) = ANY(%s)
            GROUP BY BTRIM(cueanexo::text)
        ''', [cues])
        return {r[0]: {'region_loc':r[1], 'nom_est':r[2],
                       'departamento':r[3], 'localidad':r[4],
                       'ambito':r[5], 'sector':r[6]} for r in cursor.fetchall()}


def cues_por_filtro(request, cueanexos, filters):
    # El ámbito territorial ya fue limitado por services.access.scope() en base().
    padron = padron_por_cue(cueanexos)
    return [cue for cue, data in padron.items() if all(
        value.casefold() in str(data.get(field) or '').casefold()
        for field, value in filters.items()
    )]
