from django.http import JsonResponse
from django.contrib.auth.decorators import login_required

from ..services.permission_service import assert_responsable


@login_required
def regiones_permitidas(request):

    responsable = assert_responsable(request.user)

    data = list(
        responsable.regiones.values(
            "id",
            "nombre"
        )
    )

    return JsonResponse(data, safe=False)