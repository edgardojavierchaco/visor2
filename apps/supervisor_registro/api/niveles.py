from django.http import JsonResponse
from django.contrib.auth.decorators import login_required

from ..models import SupervisorRegional, SupervisorRegionalNivel


@login_required
def api_add(request):

    sr = SupervisorRegional.objects.get(pk=request.POST.get("supervisor_regional_id"))

    obj, created = SupervisorRegionalNivel.objects.get_or_create(
        supervisor_regional=sr,
        nivel_id=request.POST.get("nivel_id"),
        defaults={"activo": True}
    )

    if not created:
        obj.activo = True
        obj.save()

    return JsonResponse({"ok": True})


@login_required
def api_delete(request, pk):

    obj = SupervisorRegionalNivel.objects.get(pk=pk)
    obj.activo = False
    obj.save()

    return JsonResponse({"ok": True})