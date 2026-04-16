import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import EstadoUsuario

@csrf_exempt
def guardar_estado(request):
    if request.method == "POST" and request.user.is_authenticated:
        try:
            data = json.loads(request.body)

            EstadoUsuario.objects.update_or_create(
                usuario=request.user,
                defaults={"data": data}
            )

            return JsonResponse({"status": "ok"})

        except Exception as e:
            return JsonResponse({"status": "error", "msg": str(e)})

    return JsonResponse({"status": "invalid"})