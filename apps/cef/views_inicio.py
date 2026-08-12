# -*- coding: utf-8 -*-

from django.shortcuts import redirect, render

from .permisos import cef_asistencia_required, get_permisos_cef_request
from .views_contexto import contexto_base


@cef_asistencia_required
def inicio(request):
    if get_permisos_cef_request(request).get("solo_asistencia"):
        return redirect("cef:asistencia")

    context = contexto_base(request, "inicio", "Inicio CEF")
    return render(request, "cef/inicio_cef.html", context)
