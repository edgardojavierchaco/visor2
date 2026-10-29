"""Consulta de ofertas del padrón sin supervisión activa, sólo lectura.

La unidad comparada es (regional, CUEANEXO, oferta). Una oferta de otro
nivel en el mismo establecimiento NO implica cobertura.
"""
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_GET
from django.db.models.functions import Lower, Trim
from apps.consultasge.models_padron import CapaUnicaOfertas
from apps.supervisa2.models import Region, NivelModalidad
from ..models import SupervisorRegionalOferta
from ..services.permission_service import puede_ver_supervisores, get_regiones_usuario
from ..services.supervisor_geo_service import SupervisorGeoService

MAX_PADRON = 30000  # límite de seguridad: nunca informar un total incompleto como definitivo
MAX_PUNTOS = 1200
MAX_FILAS = 150


def normal(texto):
    return ' '.join(str(texto or '').strip().casefold().split())


def cue(texto):
    return SupervisorGeoService._normalizar_cue(texto) or ''


@login_required
@require_GET
def consultar(request):
    if not puede_ver_supervisores(request.user):
        return JsonResponse({'ok': False, 'error': 'Acceso denegado'}, status=403)
    try:
        region_id = int(request.GET['region']) if request.GET.get('region') else None
        nivel_id = int(request.GET['nivel']) if request.GET.get('nivel') else None
        pagina = max(1, int(request.GET.get('pagina', '1')))
        if pagina > 10000 or (region_id is not None and region_id <= 0) or (nivel_id is not None and nivel_id <= 0):
            raise ValueError
    except (ValueError, TypeError):
        return JsonResponse({'ok': False, 'error': 'Filtros inválidos'}, status=400)

    permitidas = get_regiones_usuario(request.user)
    if region_id and permitidas is not None and region_id not in permitidas:
        return JsonResponse({'ok': False, 'error': 'Regional no autorizada'}, status=403)
    regiones_qs = Region.objects.all()
    if permitidas is not None:
        regiones_qs = regiones_qs.filter(pk__in=permitidas)
    if region_id:
        regiones_qs = regiones_qs.filter(pk=region_id)
    nombres_regionales = list(regiones_qs.values_list('nombre', flat=True))
    if not nombres_regionales:
        return JsonResponse({'ok': True, 'total': 0, 'filas': [], 'puntos': [], 'pagina': pagina, 'parcial': False, 'sin_coordenadas': 0})

    # El nivel/modalidad corresponde a la denominación de la oferta del padrón.
    nivel_nombre = None
    if nivel_id:
        nivel_nombre = NivelModalidad.objects.filter(pk=nivel_id).values_list('nombre', flat=True).first()
        if nivel_nombre is None:
            return JsonResponse({'ok': False, 'error': 'Nivel inexistente'}, status=400)

    # Restricción en SQL ANTES de extraer la información provincial.
    padron = CapaUnicaOfertas.objects.filter(region_loc__in=nombres_regionales)
    if nivel_nombre:
        padron = padron.annotate(oferta_limpia=Lower(Trim('oferta'))).filter(oferta_limpia=normal(nivel_nombre))
    campos = ('cueanexo', 'nom_est', 'oferta', 'region_loc', 'lat', 'long')
    rows = list(padron.values(*campos)[:MAX_PADRON + 1])
    parcial = len(rows) > MAX_PADRON
    if parcial:
        # No etiquetar resultados parciales como cobertura oficial.
        rows = rows[:MAX_PADRON]

    # Respetar las mismas regionales y la vigencia de supervisor, regional y oferta.
    asignadas = SupervisorRegionalOferta.objects.filter(
        activo=True, supervisor_regional__activo=True,
        supervisor_regional__supervisor__activo=True,
        supervisor_regional__region__nombre__in=nombres_regionales,
    )
    if nivel_nombre:
        asignadas = asignadas.annotate(oferta_limpia=Lower(Trim('oferta'))).filter(oferta_limpia=normal(nivel_nombre))
    cubiertas = {
        (normal(reg), cue(c), normal(o))
        for reg, c, o in asignadas.values_list('supervisor_regional__region__nombre', 'cueanexo', 'oferta').iterator(chunk_size=2000)
    }

    pendientes = {}
    for row in rows:
        nombre_region = normal(row['region_loc'])
        clave = (nombre_region, cue(row['cueanexo']), normal(row['oferta']))
        if not clave[1] or not clave[2] or clave in cubiertas:
            continue
        if clave not in pendientes:
            lat, lon = SupervisorGeoService._coordenadas(row)
            pendientes[clave] = {
                'regional': str(row['region_loc'] or ''),
                'cueanexo': clave[1], 'escuela': str(row['nom_est'] or ''),
                'oferta': str(row['oferta'] or ''), 'lat': lat, 'lon': lon,
            }

    filas = sorted(pendientes.values(), key=lambda x: (x['regional'], x['oferta'], x['cueanexo']))
    busqueda = normal(request.GET.get('q', '')[:80])
    if busqueda:
        filas = [f for f in filas if busqueda in normal(' '.join([f['cueanexo'], f['escuela'], f['oferta'], f['regional']]))]
    total = len(filas)
    sin_coordenadas = sum(1 for f in filas if f['lat'] is None or f['lon'] is None)
    offset = (pagina - 1) * MAX_FILAS
    # El mapa sólo recibe un conjunto acotado de puntos; la tabla pagina todos los resultados del universo consultado.
    puntos = [f for f in filas if f['lat'] is not None and f['lon'] is not None][:MAX_PUNTOS]
    return JsonResponse({
        'ok': True, 'total': total, 'parcial': parcial, 'pagina': pagina,
        'por_pagina': MAX_FILAS, 'sin_coordenadas': sin_coordenadas,
        'puntos_mostrados': len(puntos), 'puntos': puntos,
        'filas': filas[offset: offset + MAX_FILAS],
        'nota': 'Revisión contra padrón de ofertas, no acto administrativo de cobertura.',
    })
