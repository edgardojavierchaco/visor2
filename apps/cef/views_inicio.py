# -*- coding: utf-8 -*-

from django.shortcuts import redirect, render

from .permisos import cef_inicio_required, get_permisos_cef_request
from .views_contexto import contexto_base


@cef_inicio_required
def inicio(request):
    permisos = get_permisos_cef_request(request)
    if permisos.get("solo_asistencia"):
        return redirect("cef:asistencia")
    if permisos.get("solo_metricas"):
        return redirect("cef:metricas")

    context = contexto_base(request, "inicio", "Inicio CEF")
    return render(request, "cef/inicio_cef.html", context)
