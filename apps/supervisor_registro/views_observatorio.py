from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.http import HttpResponseForbidden
from django.shortcuts import render
from .models import ABMSupervisores, SupervisorRegional
from .services.catalogo_service import CatalogoService
from .services.permission_service import (puede_ver_supervisores, puede_administrar_supervisores, get_regiones_usuario)


def _contexto(request):
    contexto = CatalogoService.contexto(request.user)
    contexto['puede_administrar'] = puede_administrar_supervisores(request.user)
    return contexto


@login_required
def observatorio(request):
    if not puede_ver_supervisores(request.user):
        return HttpResponseForbidden('Sin permisos para consultar el observatorio.')
    return render(request, 'supervisores/observatorio.html', _contexto(request))


@login_required
def mapa_territorial(request):
    if not puede_ver_supervisores(request.user):
        return HttpResponseForbidden('Sin permisos para consultar el mapa.')
    return render(request, 'supervisores/mapa_territorial.html', _contexto(request))


@login_required
def nomina_supervisores(request):
    if not puede_ver_supervisores(request.user):
        return HttpResponseForbidden('Sin permisos para consultar la nómina.')
    regiones = get_regiones_usuario(request.user)
    asignaciones = SupervisorRegional.objects.filter(activo=True, supervisor__activo=True)
    if regiones is not None:
        asignaciones = asignaciones.filter(region_id__in=regiones)
    region = request.GET.get('region', '').strip()
    nivel = request.GET.get('nivel', '').strip()
    situacion = request.GET.get('situacion', '').strip()
    for nombre, valor in [('region',region),('nivel',nivel),('situacion',situacion)]:
        if valor and (not valor.isdigit() or int(valor)<1):
            return HttpResponseForbidden('Filtro inválido: '+nombre)
    if region:
        if regiones is not None and int(region) not in regiones:
            return HttpResponseForbidden('Regional no autorizada')
        asignaciones = asignaciones.filter(region_id=int(region))
    if nivel:
        asignaciones = asignaciones.filter(niveles__activo=True, niveles__nivel_id=int(nivel))
    if situacion:
        asignaciones = asignaciones.filter(supervisor__situaciones__activo=True, supervisor__situaciones__situacion_revista_id=int(situacion))
    ids = asignaciones.order_by().values('supervisor_id').distinct()
    qs = ABMSupervisores.objects.filter(pk__in=ids).select_related('usuario').annotate(
        regionales_count=Count('asignaciones_regionales__region_id', filter=Q(asignaciones_regionales__activo=True), distinct=True)
    ).order_by('usuario__apellido','usuario__nombres','pk')
    q = request.GET.get('q','').strip()[:80]
    if q:
        qs = qs.filter(Q(usuario__apellido__icontains=q) | Q(usuario__nombres__icontains=q) | Q(usuario__username__icontains=q))
    paginacion = Paginator(qs,30)
    pagina = paginacion.get_page(request.GET.get('page'))
    # Detalle nominal de CUEANEXO de sólo lectura: se limita a las regionales
    # visibles para el usuario y a los filtros efectivos de la nómina.
    for supervisor in pagina.object_list:
        regionales_supervisor = SupervisorRegional.objects.filter(
            supervisor_id=supervisor.pk, activo=True
        ).select_related('region')
        if regiones is not None:
            regionales_supervisor = regionales_supervisor.filter(region_id__in=regiones)
        if region:
            regionales_supervisor = regionales_supervisor.filter(region_id=int(region))
        if nivel:
            regionales_supervisor = regionales_supervisor.filter(
                niveles__activo=True, niveles__nivel_id=int(nivel)
            ).distinct()
        regionales_ids = list(regionales_supervisor.values_list('pk', flat=True))
        from .models import SupervisorRegionalOferta
        supervisor.cue_detalles = list(
            SupervisorRegionalOferta.objects.filter(
                supervisor_regional_id__in=regionales_ids, activo=True
            ).select_related('supervisor_regional__region')
            .order_by('supervisor_regional__region__nombre', 'cueanexo', 'oferta', 'pk')
        )
        supervisor.cue_total = len(supervisor.cue_detalles)
    contexto = _contexto(request)
    contexto.update({'pagina':pagina,'q':q,'filtros': {'region':region,'nivel':nivel,'situacion':situacion},
        'total':paginacion.count})
    return render(request,'supervisores/nomina_ministerial.html',contexto)
