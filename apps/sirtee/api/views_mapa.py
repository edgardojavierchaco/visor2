from django.http import JsonResponse
from django.views.decorators.http import require_GET

from apps.sirtee.dashboard.services.mapa import MapaSIRTEE


@require_GET
def mapa_operativo(request):

    region = request.GET.get("region") or None
    departamento = request.GET.get("departamento") or None
    criticidad = request.GET.get("criticidad") or None
    estado = request.GET.get("estado") or None

    datos = MapaSIRTEE.escuelas_operativas(
        region=region,
        departamento=departamento,
        criticidad=criticidad,
        estado_intervencion=estado,
    )

    return JsonResponse(datos, safe=False)