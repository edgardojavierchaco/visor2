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
    for key,field in (('regional','region_loc'),('departamento','departamento'),('localidad','localidad'),('sector','sector'),('ambito','ambito'),('establecimiento','nom_est')):
        value=request.GET.get(key,'').strip()
        if value:
            scu=schools(request).filter(**{field+'__icontains':value}).values('cueanexo')
            qs=qs.filter(cueanexo__in=scu)
    return qs

def sums(qs):
    result=qs.aggregate(varones=Sum('varones'),mujeres=Sum('mujeres'),registros=Count('pk'))
    result={key:(value or 0) for key,value in result.items()}
    result['total']=result['varones']+result['mujeres']
    result['establecimientos']=qs.values('cueanexo').distinct().count()
    return result

def group(qs, field):
    return list(qs.values(field).annotate(varones=Sum('varones'), mujeres=Sum('mujeres')).order_by(field))
