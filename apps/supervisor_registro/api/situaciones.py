from django.http import JsonResponse
from django.contrib.auth.decorators import login_required

from ..models import (
    SupervisorSituacionRevista,
    ABMSupervisores
)


@login_required
def api_add(request):

    supervisor = ABMSupervisores.objects.get(pk=request.POST.get("supervisor_id"))

    SupervisorSituacionRevista.objects.create(
        supervisor=supervisor,
        situacion_revista_id=request.POST.get("situacion_id"),
        fecha_desde=request.POST.get("fecha_desde"),
        fecha_hasta=request.POST.get("fecha_hasta") or None,
        activo=True
    )

    return JsonResponse({"ok": True})


@login_required
def api_update(request, pk):

    obj = SupervisorSituacionRevista.objects.get(pk=pk)

    obj.situacion_revista_id = request.POST.get("situacion_id")
    obj.fecha_desde = request.POST.get("fecha_desde")
    obj.fecha_hasta = request.POST.get("fecha_hasta") or None
    obj.save()

    return JsonResponse({"ok": True})


@login_required
def api_delete(request, pk):

    obj = SupervisorSituacionRevista.objects.get(pk=pk)
    obj.activo = False
    obj.save()

    return JsonResponse({"ok": True})