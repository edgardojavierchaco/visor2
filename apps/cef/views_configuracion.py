from django.shortcuts import render

from .permisos import cef_configuracion_required


@cef_configuracion_required
def configuracion_inicio(request):
    context = {
        "title": "Configuracion CEF",
        "active_menu": "configuracion",
    }
    return render(request, "cef/configuracion_cef.html", context)
