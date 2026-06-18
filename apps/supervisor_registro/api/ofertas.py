from django.http import JsonResponse
from django.contrib.auth.decorators import login_required

from ..models import (
    SupervisorRegionalOferta,
    SupervisorRegional,
    SupervisorRegionalNivel,
    SupervisorSituacionRevista
)

from apps.consultasge.models_padron import (
    CapaUnicaOfertas
)


@login_required
def api_buscar(request):

    cue = request.GET.get("cue", "").strip()

    if len(cue) < 3:
        return JsonResponse(
            [],
            safe=False
        )

    qs = (
        CapaUnicaOfertas.objects
        .filter(cueanexo__icontains=cue)
        .order_by(
            "cueanexo",
            "oferta"
        )[:50]
    )

    data = []

    for obj in qs:

        data.append({
            "cueanexo": obj.cueanexo,
            "nom_est": obj.nom_est,
            "oferta": obj.oferta,
            "acronimo": obj.acronimo
        })

    return JsonResponse(
        data,
        safe=False
    )


@login_required
def api_add(request):

    sr = SupervisorRegional.objects.get(pk=request.POST.get("supervisor_regional_id"))

    obj, created = SupervisorRegionalOferta.objects.get_or_create(
        supervisor_regional=sr,
        cueanexo=request.POST.get("cueanexo"),
        oferta=request.POST.get("oferta"),
        defaults={
            "nom_est": request.POST.get("nom_est"),
            "acronimo": request.POST.get("acronimo"),
            "activo": True
        }
    )

    if not created:
        obj.activo = True
        obj.save()

    return JsonResponse({"ok": True})


@login_required
def api_delete(request, pk):

    obj = SupervisorRegionalOferta.objects.get(pk=pk)
    obj.activo = False
    obj.save()

    return JsonResponse({"ok": True})


@login_required
def buscar_cue(request):

    sr = SupervisorRegional.objects.get(
        pk=request.GET["sr_id"]
    )

    cue = request.GET["cueanexo"]

    niveles = list(
        SupervisorRegionalNivel.objects.filter(
            supervisor_regional=sr,
            activo=True
        ).values_list(
            "nivel__nombre",
            flat=True
        )
    )

    ofertas = CapaUnicaOfertas.objects.filter(
        cueanexo=cue,
        region_loc=sr.region.nombre,
        oferta__in=niveles
    )

    if not ofertas.exists():

        return JsonResponse({
            "ok": False,
            "mensaje":
            "El establecimiento no pertenece a la regional o a los niveles asignados."
        })

    return JsonResponse({
        "ok": True,
        "nom_est": ofertas.first().nom_est,
        "ofertas": [
            {
                "cueanexo": x.cueanexo,
                "oferta": x.oferta,
                "acronimo": x.acronimo
            }
            for x in ofertas
        ]
    })