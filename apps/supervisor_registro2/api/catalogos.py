#api/catalogos.py
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_GET

from apps.supervisa2.models import NivelModalidad, SituacionRevista


@login_required
@require_GET
def situaciones(request):
    return JsonResponse(
        list(SituacionRevista.objects.order_by("nombre").values("id", "nombre")),
        safe=False,
    )


@login_required
@require_GET
def niveles(request):
    return JsonResponse(
        list(NivelModalidad.objects.order_by("nombre").values("id", "nombre")),
        safe=False,
    )