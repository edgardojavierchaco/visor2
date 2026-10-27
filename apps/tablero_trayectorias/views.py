import csv
from decimal import Decimal
from functools import wraps
from django.contrib.auth.decorators import login_required
from django.db import connection
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render
from django.views.decorators.cache import never_cache
from .access import resolve_scope

FIELDS = ('cue','nombre_escuela','nivel','grado_o_anio','ciclo_lectivo_dato',
          'abandono_interanual_cantidad','abandono_interanual_pct',
          'sobreedad_cantidad','sobreedad_pct','repitencia_cantidad','repitencia_pct',
          'promocion_efectiva_cantidad','promocion_efectiva_pct')
HEADERS = ('CUE','Nombre de la escuela','Nivel','Grado o año','Ciclo lectivo',
           'Abandono interanual - Cantidad','Abandono interanual - Porcentaje',
           'Sobreedad - Cantidad','Sobreedad - Porcentaje',
           'Repitencia - Cantidad','Repitencia - Porcentaje',
           'Promoción efectiva - Cantidad','Promoción efectiva - Porcentaje')

def authorized(fn):
    @login_required
    @never_cache
    @wraps(fn)
    def wrapped(request,*args,**kwargs):
        request.tray_scope = resolve_scope(request.user)
        response=fn(request,*args,**kwargs)
        response['Cache-Control']='private, no-store, max-age=0'
        return response
    return wrapped

def base_rows(scope, filters=None):
    """SQL parameterizado: nunca se aplican permisos solo en JS."""
    filters = filters or {}
    if scope['kind']=='cues' and not scope['cues']:
        return []
    sql='SELECT '+', '.join(FIELDS)+' FROM indicadores.visorindicador WHERE TRUE'
    params=[]
    if scope['kind']=='cues':
        sql+=' AND TRIM(cue::text) = ANY(%s::text[])'; params.append(scope['cues'])
    for key in ('nivel','grado_o_anio','ciclo_lectivo_dato'):
        value=filters.get(key)
        if value not in ('',None,'Todos','Todas'):
            if key=='grado_o_anio':
                try: value=int(value)
                except (TypeError,ValueError): return []
            sql+=' AND '+key+' = %s'; params.append(value)
    if filters.get('nom_est'):
        sql+=' AND nombre_escuela = %s'
        params.append(str(filters['nom_est'])[:255])
    if filters.get('search'):
        term=str(filters['search'])[:120]
        sql+=' AND (cue::text ILIKE %s OR nombre_escuela ILIKE %s)'
        params.extend(['%'+term+'%']*2)
    sql+=' ORDER BY cue,nivel,grado_o_anio,ciclo_lectivo_dato'
    with connection.cursor() as cur:
        cur.execute(sql,params)
        return [dict(zip(FIELDS,row)) for row in cur.fetchall()]

@authorized
def dashboard(request):
    return render(request,'tablero_trayectorias/dashboard.html')

@authorized
def datos(request):
    def convert(v):
        return float(v) if isinstance(v,Decimal) else v
    rows=base_rows(request.tray_scope)
    return JsonResponse({'results':[{k:convert(v) for k,v in row.items()} for row in rows],
                         'source':'Relevamiento Anual (RA)'})

@authorized
def exportar(request):
    rows=base_rows(request.tray_scope, {
        'search':request.GET.get('search',''), 'nom_est':request.GET.get('nom_est',''), 'nivel':request.GET.get('nivel',''),
        'grado_o_anio':request.GET.get('grado',''), 'ciclo_lectivo_dato':request.GET.get('ciclo','')})
    response=HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition']='attachment; filename="trayectorias_educativas_RA.csv"'
    response.write('\ufeff')
    writer=csv.writer(response,delimiter=';',quoting=csv.QUOTE_MINIMAL)
    writer.writerow(HEADERS)
    for row in rows:
        def safe_csv(v):
            if isinstance(v, str) and v.lstrip().startswith(('=', '+', '-', '@', '\t', '\r')):
                return "'" + v
            return v
        writer.writerow([safe_csv(row.get(k)) for k in FIELDS])
    return response

@authorized
def guia(request):
    return render(request, 'tablero_trayectorias/guia.html')
