from django.db.models import Q, Sum, Count, F
from ..models import Alumnos_Bilingue, EscuelasBilingues
from .access import scope

def base(request):
    qs=Alumnos_Bilingue.objects.select_related('curso')
    cues=scope(request)
    if cues is not None:
        qs=qs.filter(cueanexo__in=cues)
    return qs

def schools(request):
    qs=EscuelasBilingues.objects.all()
    cues=scope(request)
    if cues is not None:
        qs=qs.filter(cueanexo__in=cues)
    return qs

def filtered(request):
    qs=base(request)
    fields={'cueanexo':'cueanexo','nivel':'nivel','lengua':'lengua','seccion':'seccion','curso':'curso_id'}
    for param,field in fields.items():
        value=request.GET.get(param,'').strip()
        if value:
            qs=qs.filter(**{field:value})
    territoriales = (('regional','region_loc'), ('departamento','departamento'),
                     ('localidad','localidad'), ('sector','sector'),
                     ('ambito','ambito'), ('establecimiento','nom_est'))
    filtros = {field: request.GET.get(param, '').strip()
               for param, field in territoriales if request.GET.get(param, '').strip()}
    if filtros:
        from .geo_padron import cues_por_filtro
        cues = qs.order_by().values_list('cueanexo', flat=True).distinct()
        autorizados = cues_por_filtro(request, cues, filtros)
        qs = qs.filter(cueanexo__in=autorizados)
    return qs

def sums(qs):
    result=qs.aggregate(varones=Sum('varones'),mujeres=Sum('mujeres'),registros=Count('pk'))
    result={key:(value or 0) for key,value in result.items()}
    result['total']=result['varones']+result['mujeres']
    result['establecimientos']=qs.values('cueanexo').distinct().count()
    return result

def group(qs, field):
    return list(qs.values(field).annotate(varones=Sum('varones'), mujeres=Sum('mujeres')).order_by(field))
