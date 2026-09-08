from django.http import JsonResponse
from django.views.decorators.http import require_GET
from .domain.access import operator_required
from .models import SituacionServicio, CondicionActividad, TipoFunciones, TipoDesigFunc


@operator_required
@require_GET
def obtener_ayuda_renpe(request):
    catalogs = {"situacion": (SituacionServicio, "descrip_sitrev"), "condicion": (CondicionActividad, "descrip_condicion"), "funcion": (TipoFunciones, "funciones_descripcion"), "t_designacion": (TipoDesigFunc, "desigfunc_descripcion")}
    spec = catalogs.get(request.GET.get("tipo"))
    pk = request.GET.get("id", "")
    if not spec or not pk.isascii() or not pk.isdecimal() or len(pk) > 9:
        return JsonResponse({"ok": False}, status=400)
    model, title = spec
    obj = model.objects.filter(pk=pk).first()
    return JsonResponse({"ok": bool(obj), "titulo": getattr(obj, title, ""), "ayuda": (obj.ayuda or "") if obj else ""})
