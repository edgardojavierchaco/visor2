from django.http import JsonResponse
from django.contrib.auth.decorators import login_required

from ..models import (
    SupervisorRegional,
    ABMSupervisores,
    Region
)

from ..services.permission_service import get_responsable


@login_required
def api_add(request):

    responsable = get_responsable(request.user)

    supervisor = ABMSupervisores.objects.get(pk=request.POST.get("supervisor_id"))
    region = Region.objects.get(pk=request.POST.get("region_id"))

    if not responsable.regiones.filter(pk=region.pk).exists():
        return JsonResponse({"ok": False, "error": "No autorizado"})

    obj, created = SupervisorRegional.objects.get_or_create(
        supervisor=supervisor,
        region=region,
        defaults={"responsable_alta": responsable, "activo": True}
    )

    if not created:
        obj.activo = True
        obj.save()

    return JsonResponse({"ok": True})


@login_required
def api_delete(request, pk):

    obj = SupervisorRegional.objects.get(pk=pk)
    obj.activo = False
    obj.save()

    return JsonResponse({"ok": True})