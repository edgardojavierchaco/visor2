"""Consultas territoriales EIB; aislamiento por alcance de usuario."""
from django.db import DatabaseError
from django.db.models import Count, Q, Sum
from ..models import EscuelaBilingueGeo, Alumnos_Bilingue
from .access import scope

FILTERS = ('region_loc','departamento','localidad','ambito','sector')

def establecimientos_bii(request):
    qs = EscuelaBilingueGeo.objects.all()
    cues = scope(request)
    if cues is not None:
        qs = qs.filter(cueanexo__in=cues)
    for field in FILTERS:
        value = request.GET.get(field, '').strip()[:120]
        if value:
            qs = qs.filter(**{field + '__icontains': value})
    q = request.GET.get('q','').strip()[:100]
    if q:
        qs = qs.filter(Q(cueanexo__icontains=q)|Q(nom_est__icontains=q))
    return qs

def resumen_bii(request):
    # Subquery evita materializar en Python listas enormes.
    from django.db.models import Subquery
    qs = establecimientos_bii(request)
    total = qs.count()
    coords = qs.filter(lat__gte=-90,lat__lte=90,long__gte=-180,long__lte=180).count()
    registrados = (Alumnos_Bilingue.objects.filter(
        cueanexo__in=Subquery(qs.values('cueanexo'))
    ).values('cueanexo').distinct().count())
    if scope(request) is not None:
        # El subquery anterior ya restringe el universo a los CUE visibles.
        pass
    return {'bii':total,'con_coords':coords,'sin_coords':total-coords,
            'con_carga':registrados,'sin_carga':max(0,total-registrados)}
