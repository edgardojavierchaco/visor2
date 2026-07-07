# -*- coding: utf-8 -*-

from django.shortcuts import render

from .permisos import cef_required
from .views_contexto import contexto_base


@cef_required
def inicio(request):
    context = contexto_base(request, "inicio", "Inicio CEF")
    return render(request, "cef/inicio_cef.html", context)
