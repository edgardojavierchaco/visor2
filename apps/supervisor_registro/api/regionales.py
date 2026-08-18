#api/regionales.py
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_POST

from ..models import ABMSupervisores, Region, SupervisorRegional
from ..services.permission_service import puede_operar_region, puede_operar_supervisor
from ..services.supervisor_service import build


@login_required
@require_POST
def api_add(request):
    supervisor = get_object_or_404(ABMSupervisores, pk=request.POST.get("supervisor_id"), activo=True)
    region_id = request.POST.get("region_id")
    if not puede_operar_region(request.user, region_id, "crear"):
        return JsonResponse({"ok": False, "error": "No autorizado"}, status=403)
    if not puede_operar_supervisor(request.user, supervisor, "modificar") and not puede_operar_region(request.user, region_id, "crear"):
        return JsonResponse({"ok": False, "error": "No autorizado"}, status=403)

    region = get_object_or_404(Region, pk=region_id)
    from ..services.expediente_service import add_regional
    from ..services.permission_service import es_admin, get_responsable
    responsable = None if es_admin(request.user) else get_responsable(request.user)
    obj = add_regional(supervisor, region, responsable)
    return JsonResponse({"ok": True, "id": obj.id})


@login_required
@require_POST
def api_delete(request, pk):
    obj = get_object_or_404(SupervisorRegional, pk=pk)
    if not puede_operar_region(request.user, obj.region_id, "eliminar"):
        return JsonResponse({"ok": False, "error": "No autorizado"}, status=403)
    obj.activo = False
    obj.save(update_fields=["activo"])
    return JsonResponse({"ok": True})
