"""Portal ministerial EIB: vistas seguras y paginadas."""
import csv
import logging
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Sum
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_GET, require_POST
from .forms_v2 import RegistroForm
from .models import Alumnos_Bilingue, Nivel_curso
from .services.access import scope, require_editor, role
from .services.queries import base, filtered, schools, sums, group
log=logging.getLogger(__name__)

def context(request, tab):
    return {'tab':tab, 'perfil_eib':role(request.user), 'provincial_eib':scope(request) is None}

@login_required
@require_GET
def panorama(request):
    qs=filtered(request)
    stats=sums(qs)
    items=group(qs,'lengua')
    niveles=group(qs,'nivel')
    regiones=[]
    # Agregación por región utilizando catálogo geográfico, sin depender de vistas externas.
    regmap={}
    for cue,region in schools(request).values_list('cueanexo','region_loc').distinct():
        regmap.setdefault(cue,region)
    for row in qs.values('cueanexo').annotate(v=Sum('varones'),m=Sum('mujeres')):
        reg=regmap.get(row['cueanexo'],'Sin región') or 'Sin región'
        regiones.append((reg,(row['v'] or 0)+(row['m'] or 0)))
    totreg={}
    for reg,amount in regiones: totreg[reg]=totreg.get(reg,0)+amount
    ctx=context(request,'panorama')
    ctx.update(stats=stats, pueblos=items,niveles=niveles,regiones=sorted(totreg.items()),
               escuelas=schools(request).values('cueanexo','nom_est')[:300],
               filtros={key:request.GET.get(key,'') for key in ('cueanexo','regional','nivel','lengua','establecimiento')})
    return render(request,'intercultural_v2/panorama.html',ctx)

@login_required
@require_GET
def listado(request):
    from django.core.paginator import Paginator
    qs=filtered(request).order_by('cueanexo','nivel','curso_id','seccion','pk')
    page=Paginator(qs,35).get_page(request.GET.get('page'))
    ctx=context(request,'registros')
    ctx.update(page=page,stats=sums(qs),filtros={key:request.GET.get(key,'') for key in ('cueanexo','nivel','lengua','establecimiento')})
    return render(request,'intercultural_v2/listado.html',ctx)

@login_required
@require_GET
def establecimientos(request):
    from django.core.paginator import Paginator
    qs=schools(request)
    q=request.GET.get('q','').strip()
    if q:
        from django.db.models import Q
        qs=qs.filter(Q(cueanexo__icontains=q)|Q(nom_est__icontains=q)|Q(localidad__icontains=q))
    ctx=context(request,'escuelas')
    ctx['page']=Paginator(qs.order_by('cueanexo'),30).get_page(request.GET.get('page'))
    ctx['q']=q
    return render(request,'intercultural_v2/escuelas.html',ctx)

@login_required
@require_GET
def ficha(request,cueanexo):
    escuela=schools(request).filter(cueanexo=cueanexo).first()
    if escuela is None:
        from django.http import Http404
        raise Http404("Establecimiento no encontrado")
    qs=base(request).filter(cueanexo=cueanexo)
    ctx=context(request,'escuelas')
    ctx.update(escuela=escuela,stats=sums(qs),grupos=group(qs,'lengua'),filas=qs.order_by('nivel','curso_id','seccion')[:500])
    return render(request,'intercultural_v2/ficha.html',ctx)

@login_required
def registro(request,pk=None):
    require_editor(request)
    obj=get_object_or_404(base(request),pk=pk) if pk else None
    form=RegistroForm(request.POST or None,instance=obj,request=request)
    if request.method=='POST' and form.is_valid():
        with transaction.atomic():
            item=form.save()
        log.info('EIB registro guardado usuario=%s pk=%s',request.user.pk,item.pk)
        messages.success(request,'Registro guardado correctamente.')
        return redirect('intercultural:alumnos_list')
    ctx=context(request,'registros'); ctx.update(form=form,obj=obj)
    return render(request,'intercultural_v2/form.html',ctx)

@login_required
@require_POST
def eliminar(request,pk):
    require_editor(request)
    obj=get_object_or_404(base(request),pk=pk)
    if request.POST.get('confirmar')!='SI':
        raise PermissionDenied('Se requiere confirmación explícita')
    log.warning('EIB eliminación usuario=%s pk=%s cue=%s',request.user.pk,obj.pk,obj.cueanexo)
    obj.delete()
    messages.success(request,'Registro eliminado.')
    return redirect('intercultural:alumnos_list')

@login_required
@require_GET
def cursos(request):
    nivel=request.GET.get('nivel','')
    return JsonResponse([{'id':x.pk,'curso':x.curso} for x in Nivel_curso.objects.filter(nivel=nivel).order_by('curso')],safe=False)

@login_required
@require_GET
def buscar(request):
    from django.db.models import Q
    q=request.GET.get('term','').strip()[:80]
    if not q:
        return JsonResponse([],safe=False)
    qs=schools(request).filter(Q(cueanexo__icontains=q)|Q(nom_est__icontains=q))[:30]
    return JsonResponse([{'id':x.cueanexo,'text':f'{x.cueanexo} — {x.nom_est}','nom_est':x.nom_est} for x in qs],safe=False)

@login_required
@require_GET
def exportar(request):
    qs=filtered(request).order_by('cueanexo','pk')
    resp=HttpResponse(content_type='text/csv; charset=utf-8')
    resp['Content-Disposition']='attachment; filename="intercultural_eib.csv"'
    resp.write('\ufeff')
    writer=csv.writer(resp)
    writer.writerow(['CUEANEXO','Nivel','Curso','Sección','Pueblo registrado','Varones','Mujeres','Total'])
    for row in qs.iterator(chunk_size=1000):
        # Proteger frente a CSV formula injection en valores provenientes de BD.
        def safe(x):
            s=str(x)
            return "'"+s if s.lstrip().startswith(('=','+','-','@')) else s
        writer.writerow([safe(row.cueanexo),safe(row.nivel),safe(row.curso.curso),safe(row.seccion),safe(row.lengua),row.varones,row.mujeres,row.varones+row.mujeres])
    log.info('EIB exportación usuario=%s filtros=%s',request.user.pk,dict(request.GET))
    return resp

@login_required
@require_GET
def mapa(request):
    # Geometrías no incluidas en la vista v_escuelas_bilingues: usar tabla georreferenciada del proyecto mediante integración validada.
    ctx=context(request,'mapa')
    ctx['registros']=schools(request).count()
    return render(request,'intercultural_v2/mapa.html',ctx)

@login_required
@require_GET
def guia(request):
    return render(request,'intercultural_v2/guia.html',context(request,'guia'))
