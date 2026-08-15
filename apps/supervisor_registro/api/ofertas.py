#api/ofertas.py
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_GET, require_POST

from apps.consultasge.models_padron import CapaUnicaOfertas

from ..models import SupervisorRegional, SupervisorRegionalNivel, SupervisorRegionalOferta
from ..services.permission_service import puede_operar_region


@login_required
@require_GET
def api_buscar(request):
    cue = request.GET.get("cue", "").strip()
    if len(cue) < 3:
        return JsonResponse([], safe=False)

    data = list(
        CapaUnicaOfertas.objects
        .filter(cueanexo__icontains=cue)
        .order_by("cueanexo", "oferta")[:50]
        .values("cueanexo", "nom_est", "oferta", "acronimo")
    )
    return JsonResponse(data, safe=False)


@login_required
@require_POST
def api_add(request):
    sr = get_object_or_404(SupervisorRegional, pk=request.POST.get("supervisor_regional_id"), activo=True)
    if not puede_operar_region(request.user, sr.region_id, "modificar"):
        return JsonResponse({"ok": False, "error": "No autorizado"}, status=403)

    obj, created = SupervisorRegionalOferta.objects.get_or_create(
        supervisor_regional=sr,
        cueanexo=request.POST.get("cueanexo"),
        oferta=request.POST.get("oferta"),
        defaults={
            "nom_est": request.POST.get("nom_est") or "",
            "acronimo": request.POST.get("acronimo") or None,
            "activo": True,
        },
    )
    if not created:
        obj.nom_est = request.POST.get("nom_est") or obj.nom_est
        obj.acronimo = request.POST.get("acronimo") or None
        obj.activo = True
        obj.save(update_fields=["nom_est", "acronimo", "activo"])
    return JsonResponse({"ok": True, "id": obj.id})


@login_required
@require_POST
def api_delete(request, pk):
    obj = get_object_or_404(SupervisorRegionalOferta.objects.select_related("supervisor_regional"), pk=pk)
    if not puede_operar_region(request.user, obj.supervisor_regional.region_id, "modificar"):
        return JsonResponse({"ok": False, "error": "No autorizado"}, status=403)
    obj.activo = False
    obj.save(update_fields=["activo"])
    return JsonResponse({"ok": True})


@login_required
@require_GET
def buscar_cue(request):
    sr = get_object_or_404(SupervisorRegional, pk=request.GET.get("sr_id"), activo=True)
    if not puede_operar_region(request.user, sr.region_id, "ver"):
        return JsonResponse({"ok": False, "mensaje": "Sin permisos"}, status=403)

    cue = request.GET.get("cueanexo", "").strip()
    niveles = list(
        SupervisorRegionalNivel.objects
        .filter(supervisor_regional=sr, activo=True)
        .values_list("nivel__nombre", flat=True)
    )

    ofertas = CapaUnicaOfertas.objects.filter(
        cueanexo=cue,
        region_loc=sr.region.nombre,
        oferta__in=niveles,
    )

    if not ofertas.exists():
        return JsonResponse({
            "ok": False,
            "mensaje": "El establecimiento no pertenece a la regional o a los niveles asignados.",
        })

    data = list(ofertas.values("cueanexo", "oferta", "acronimo"))
    return JsonResponse({
        "ok": True,
        "nom_est": ofertas.values_list("nom_est", flat=True).first(),
        "ofertas": data,
    })
