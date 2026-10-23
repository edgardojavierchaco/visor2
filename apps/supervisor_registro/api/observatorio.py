"""Indicadores SIGSE. Datos de asignaciones registradas, NO cobertura total del padrón."""
from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.http import JsonResponse
from django.views.decorators.http import require_GET
from ..models import ABMSupervisores, SupervisorRegional, SupervisorRegionalOferta
from ..services.permission_service import get_regiones_usuario, puede_ver_supervisores


def _numero(request, nombre):
    value = request.GET.get(nombre)
    if not value:
        return None
    try:
        n = int(value)
        if n < 1:
            raise ValueError()
        return n
    except (ValueError, TypeError):
        raise ValueError("Filtro %s inválido" % nombre)


@login_required
@require_GET
def indicadores(request):
    if not puede_ver_supervisores(request.user):
        return JsonResponse({"ok": False, "error": "Acceso denegado"}, status=403)
    try:
        region = _numero(request, "region")
        nivel = _numero(request, "nivel")
        situacion = _numero(request, "situacion")
    except ValueError as exc:
        return JsonResponse({"ok": False, "error": str(exc)}, status=400)
    permitido = get_regiones_usuario(request.user)
    if region and permitido is not None and region not in permitido:
        return JsonResponse({"ok": False, "error": "Regional no autorizada"}, status=403)
    asignaciones = SupervisorRegional.objects.filter(activo=True, supervisor__activo=True)
    if permitido is not None:
        asignaciones = asignaciones.filter(region_id__in=permitido)
    if region:
        asignaciones = asignaciones.filter(region_id=region)
    if nivel:
        asignaciones = asignaciones.filter(niveles__activo=True, niveles__nivel_id=nivel)
    if situacion:
        asignaciones = asignaciones.filter(supervisor__situaciones__activo=True,
            supervisor__situaciones__situacion_revista_id=situacion)
    ids = asignaciones.order_by().values('pk').distinct()
    ofertas = SupervisorRegionalOferta.objects.filter(activo=True, supervisor_regional_id__in=ids)
    regiones = list(asignaciones.order_by().values('region__nombre')
        .annotate(supervisores=Count('supervisor_id', distinct=True))
        .order_by('region__nombre')[:100])
    return JsonResponse({"ok": True, "alcance": "asignaciones registradas",
        "indicadores": {
            "supervisores": asignaciones.values('supervisor_id').distinct().count(),
            "regionales": asignaciones.values('region_id').distinct().count(),
            "cueanexos": ofertas.values('cueanexo').distinct().count(),
            "ofertas_registradas": ofertas.values('cueanexo', 'oferta').distinct().count(),
            "asignaciones": ids.count(),
        }, "regionales_detalle": regiones})
