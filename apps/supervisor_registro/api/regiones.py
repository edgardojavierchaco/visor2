#api/regiones.py
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_GET

from ..services.permission_service import get_regiones_queryset


@login_required
@require_GET
def regiones_permitidas(request):
    data = list(get_regiones_queryset(request.user).values("id", "nombre"))
    return JsonResponse(data, safe=False)
