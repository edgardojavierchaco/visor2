from django.http import JsonResponse

from .models import (
    SituacionServicio,
    CondicionActividad,
    TipoFunciones,
)


def obtener_ayuda_renpe(request):

    tipo = request.GET.get("tipo")
    pk = request.GET.get("id")

    try:

        if tipo == "situacion":

            obj = SituacionServicio.objects.get(
                pk=pk
            )

            return JsonResponse({
                "ok": True,
                "titulo": obj.descrip_sitrev,
                "ayuda": obj.ayuda or ""
            })

        elif tipo == "condicion":

            obj = CondicionActividad.objects.get(
                pk=pk
            )

            return JsonResponse({
                "ok": True,
                "titulo": obj.descrip_condicion,
                "ayuda": obj.ayuda or ""
            })

        elif tipo == "funcion":

            obj = TipoFunciones.objects.get(
                pk=pk
            )

            return JsonResponse({
                "ok": True,
                "titulo": obj.funciones_descripcion,
                "ayuda": obj.ayuda or ""
            })

        return JsonResponse({
            "ok": False
        })

    except Exception:

        return JsonResponse({
            "ok": False
        })