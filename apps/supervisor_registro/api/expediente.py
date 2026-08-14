#api/expediente.py
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_GET, require_POST

from ..audit.services import log_change
from ..audit.utils import snapshot
from ..models import (
    SupervisorRegional,
    SupervisorRegionalNivel,
    SupervisorRegionalOferta,
    SupervisorSituacionRevista,
)
from ..selectors.supervisor_selectors import get_supervisor, get_supervisor_regional
from ..services import expediente_service as svc
from ..services.permission_service import (
    es_admin,
    get_regiones_usuario,
    puede_operar_region,
    puede_operar_supervisor,
)


def _forbidden():
    return JsonResponse({"ok": False, "error": "Sin permisos"}, status=403)


@login_required
@require_POST
def add_situacion(request):
    supervisor = get_supervisor(request.POST.get("supervisor_id"))
    if not puede_operar_supervisor(request.user, supervisor, "modificar"):
        return _forbidden()

    obj = svc.add_situacion(supervisor, request.POST)
    log_change(user=request.user, action="CREATE", instance=obj, before=None, after=snapshot(obj), request=request)
    return JsonResponse({"ok": True, "id": obj.id})


@login_required
@require_POST
def update_situacion(request, pk):
    obj = get_object_or_404(SupervisorSituacionRevista.objects.select_related("supervisor"), pk=pk)
    if not puede_operar_supervisor(request.user, obj.supervisor, "modificar"):
        return _forbidden()
    before = snapshot(obj)
    svc.update_situacion(obj, request.POST)
    log_change(user=request.user, action="UPDATE", instance=obj, before=before, after=snapshot(obj), request=request)
    return JsonResponse({"ok": True})


@login_required
@require_POST
def delete_situacion(request, pk):
    obj = get_object_or_404(SupervisorSituacionRevista.objects.select_related("supervisor"), pk=pk)
    if not puede_operar_supervisor(request.user, obj.supervisor, "modificar"):
        return _forbidden()
    before = snapshot(obj)
    svc.delete_situacion(obj)
    log_change(user=request.user, action="DELETE", instance=obj, before=before, after=None, request=request)
    return JsonResponse({"ok": True})


@login_required
@require_POST
def add_regional(request):
    supervisor = get_supervisor(request.POST.get("supervisor_id"))
    region_id = request.POST.get("region_id")
    if not puede_operar_region(request.user, region_id, "crear"):
        return _forbidden()

    from ..models import Region, ResponsableRegional
    region = get_object_or_404(Region, pk=region_id)
    responsable = None if es_admin(request.user) else get_object_or_404(ResponsableRegional, usuario=request.user, activo=True)
    obj = svc.add_regional(supervisor, region, responsable)
    log_change(user=request.user, action="CREATE", instance=obj, before=None, after=snapshot(obj), request=request)
    return JsonResponse({"ok": True, "id": obj.id})


@login_required
@require_POST
def delete_regional(request, pk):
    obj = get_supervisor_regional(pk)
    if not puede_operar_region(request.user, obj.region_id, "eliminar"):
        return _forbidden()
    before = snapshot(obj)
    svc.delete_regional(obj)
    log_change(user=request.user, action="DELETE", instance=obj, before=before, after=None, request=request)
    return JsonResponse({"ok": True})


@login_required
@require_POST
def add_nivel(request):
    sr = get_supervisor_regional(request.POST.get("sr_id"))
    if not puede_operar_region(request.user, sr.region_id, "modificar"):
        return _forbidden()
    obj = svc.add_nivel(sr, request.POST.get("nivel_id"))
    log_change(user=request.user, action="CREATE", instance=obj, before=None, after=snapshot(obj), request=request)
    return JsonResponse({"ok": True, "id": obj.id})


@login_required
@require_POST
def delete_nivel(request):
    obj = get_object_or_404(SupervisorRegionalNivel.objects.select_related("supervisor_regional"), pk=request.POST.get("id"))
    if not puede_operar_region(request.user, obj.supervisor_regional.region_id, "modificar"):
        return _forbidden()
    before = snapshot(obj)
    svc.delete_nivel(obj)
    log_change(user=request.user, action="DELETE", instance=obj, before=before, after=None, request=request)
    return JsonResponse({"ok": True})


@login_required
@require_POST
def update_nivel(request, pk):
    obj = get_object_or_404(SupervisorRegionalNivel.objects.select_related("supervisor_regional"), pk=pk)
    if not puede_operar_region(request.user, obj.supervisor_regional.region_id, "modificar"):
        return _forbidden()
    before = snapshot(obj)
    svc.update_nivel(obj, request.POST)
    log_change(user=request.user, action="UPDATE", instance=obj, before=before, after=snapshot(obj), request=request)
    return JsonResponse({"ok": True})


@login_required
@require_POST
def add_oferta(request):
    sr = get_supervisor_regional(request.POST.get("sr_id"))
    if not puede_operar_region(request.user, sr.region_id, "modificar"):
        return _forbidden()
    obj = svc.add_oferta(sr, request.POST)
    log_change(user=request.user, action="CREATE", instance=obj, before=None, after=snapshot(obj), request=request)
    return JsonResponse({"ok": True, "id": obj.id})


@login_required
@require_POST
def delete_oferta(request, pk):
    obj = get_object_or_404(SupervisorRegionalOferta.objects.select_related("supervisor_regional"), pk=pk)
    if not puede_operar_region(request.user, obj.supervisor_regional.region_id, "modificar"):
        return _forbidden()
    before = snapshot(obj)
    svc.delete_oferta(obj)
    log_change(user=request.user, action="DELETE", instance=obj, before=before, after=None, request=request)
    return JsonResponse({"ok": True})


@login_required
@require_POST
def update_oferta(request, pk):
    obj = get_object_or_404(SupervisorRegionalOferta.objects.select_related("supervisor_regional"), pk=pk)
    if not puede_operar_region(request.user, obj.supervisor_regional.region_id, "modificar"):
        return _forbidden()
    before = snapshot(obj)
    svc.update_oferta(obj, request.POST)
    log_change(user=request.user, action="UPDATE", instance=obj, before=before, after=snapshot(obj), request=request)
    return JsonResponse({"ok": True})


@login_required
@require_GET
def get_expediente(request, supervisor_id):
    supervisor = get_supervisor(supervisor_id)
    if not puede_operar_supervisor(request.user, supervisor, "ver"):
        return _forbidden()

    regiones = get_regiones_usuario(request.user)
    regional_qs = (
        SupervisorRegional.objects
        .filter(supervisor=supervisor, activo=True)
        .select_related("region")
        .prefetch_related("niveles__nivel", "ofertas")
    )
    if regiones is not None:
        regional_qs = regional_qs.filter(region_id__in=regiones)

    situaciones = list(
        supervisor.situaciones.filter(activo=True)
        .select_related("situacion_revista")
        .values("id", "fecha_desde", "fecha_hasta", "situacion_revista", "situacion_revista__nombre")
    )

    regionales, niveles, ofertas = [], [], []
    for sr in regional_qs:
        regionales.append({"id": sr.id, "region": str(sr.region)})
        for n in sr.niveles.all():
            if n.activo:
                niveles.append({
                    "id": n.id,
                    "regional": str(sr.region),
                    "nivel": str(n.nivel),
                    "nivel_id": n.nivel_id,
                    "supervisor_regional_id": sr.id,
                })
        for o in sr.ofertas.all():
            if o.activo:
                ofertas.append({
                    "id": o.id,
                    "regional": str(sr.region),
                    "cueanexo": o.cueanexo,
                    "establecimiento": o.nom_est,
                    "oferta": o.oferta,
                    "acronimo": o.acronimo,
                    "supervisor_regional_id": sr.id,
                })

    return JsonResponse({
        "situaciones": situaciones,
        "regionales": regionales,
        "niveles": niveles,
        "ofertas": ofertas,
    })
