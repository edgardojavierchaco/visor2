from django.http import JsonResponse
from django.contrib.auth.decorators import login_required

from apps.supervisa2.models import (
    SituacionRevista,
    NivelModalidad
)


@login_required
def situaciones(request):

    return JsonResponse(
        list(
            SituacionRevista.objects
            .order_by("nombre")
            .values(
                "id",
                "nombre"
            )
        ),
        safe=False
    )


@login_required
def niveles(request):

    return JsonResponse(
        list(
            NivelModalidad.objects
            .order_by("nombre")
            .values(
                "id",
                "nombre"
            )
        ),
        safe=False
    )