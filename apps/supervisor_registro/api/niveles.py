#api/niveles.py
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_POST

from ..models import SupervisorRegional, SupervisorRegionalNivel
from ..services.permission_service import puede_operar_region


@login_required
@require_POST
def api_add(request):
    sr = get_object_or_404(SupervisorRegional, pk=request.POST.get("supervisor_regional_id"), activo=True)
    if not puede_operar_region(request.user, sr.region_id, "modificar"):
        return JsonResponse({"ok": False, "error": "No autorizado"}, status=403)

    obj, created = SupervisorRegionalNivel.objects.get_or_create(
        supervisor_regional=sr,
        nivel_id=request.POST.get("nivel_id"),
        defaults={"activo": True},
    )
    if not created and not obj.activo:
        obj.activo = True
        obj.save(update_fields=["activo"])
    return JsonResponse({"ok": True, "id": obj.id})


@login_required
@require_POST
def api_delete(request, pk):
    obj = get_object_or_404(SupervisorRegionalNivel.objects.select_related("supervisor_regional"), pk=pk)
    if not puede_operar_region(request.user, obj.supervisor_regional.region_id, "modificar"):
        return JsonResponse({"ok": False, "error": "No autorizado"}, status=403)
    obj.activo = False
    obj.save(update_fields=["activo"])
    return JsonResponse({"ok": True})
