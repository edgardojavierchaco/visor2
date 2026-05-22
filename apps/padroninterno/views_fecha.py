import datetime
import json

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.utils import timezone

from .models import FechaActualizacionPadronInterno, usuario_es_admin_padron


def get_contexto_fecha_padron(request):
    obj_fecha = FechaActualizacionPadronInterno.objects.filter(id=1).first()

    return {
        "padron_ultima_fecha": obj_fecha.fecha if obj_fecha else None,
        "padron_is_admin": usuario_es_admin_padron(request.user),
    }


@login_required
def actualizar_fecha_padron(request):
    if request.method != "POST":
        return JsonResponse({"status": "error", "message": "Método no permitido."}, status=405)

    if not usuario_es_admin_padron(request.user):
        return JsonResponse({"status": "error", "message": "No autorizado."}, status=403)

    try:
        data = json.loads(request.body.decode("utf-8") or "{}")
        nueva_fecha_str = data.get("fecha")

        if not nueva_fecha_str:
            return JsonResponse({"status": "error", "message": "Fecha requerida."}, status=400)

        nueva_fecha = timezone.make_aware(
            datetime.datetime.strptime(nueva_fecha_str, "%Y-%m-%dT%H:%M")
        )

        FechaActualizacionPadronInterno.objects.update_or_create(
            id=1,
            defaults={"fecha": nueva_fecha},
        )

        return JsonResponse({"status": "success", "message": "Fecha actualizada correctamente."})
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({"status": "error", "message": "Formato de fecha inválido."}, status=400)
    except Exception as exc:
        return JsonResponse({"status": "error", "message": str(exc)}, status=500)
