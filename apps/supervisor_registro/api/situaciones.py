#api/situaciones.py
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_POST

from ..models import ABMSupervisores, SupervisorSituacionRevista
from ..services.permission_service import puede_operar_supervisor


@login_required
@require_POST
def api_add(request):
    supervisor = get_object_or_404(ABMSupervisores, pk=request.POST.get("supervisor_id"), activo=True)
    if not puede_operar_supervisor(request.user, supervisor, "modificar"):
        return JsonResponse({"ok": False, "error": "No autorizado"}, status=403)

    obj = SupervisorSituacionRevista.objects.create(
        supervisor=supervisor,
        situacion_revista_id=request.POST.get("situacion_id"),
        fecha_desde=request.POST.get("fecha_desde"),
        fecha_hasta=request.POST.get("fecha_hasta") or None,
        activo=True,
    )
    return JsonResponse({"ok": True, "id": obj.id})


@login_required
@require_POST
def api_update(request, pk):
    obj = get_object_or_404(SupervisorSituacionRevista.objects.select_related("supervisor"), pk=pk)
    if not puede_operar_supervisor(request.user, obj.supervisor, "modificar"):
        return JsonResponse({"ok": False, "error": "No autorizado"}, status=403)
    obj.situacion_revista_id = request.POST.get("situacion_id")
    obj.fecha_desde = request.POST.get("fecha_desde")
    obj.fecha_hasta = request.POST.get("fecha_hasta") or None
    obj.save(update_fields=["situacion_revista", "fecha_desde", "fecha_hasta"])
    return JsonResponse({"ok": True})


@login_required
@require_POST
def api_delete(request, pk):
    obj = get_object_or_404(SupervisorSituacionRevista.objects.select_related("supervisor"), pk=pk)
    if not puede_operar_supervisor(request.user, obj.supervisor, "modificar"):
        return JsonResponse({"ok": False, "error": "No autorizado"}, status=403)
    obj.activo = False
    obj.save(update_fields=["activo"])
    return JsonResponse({"ok": True})
