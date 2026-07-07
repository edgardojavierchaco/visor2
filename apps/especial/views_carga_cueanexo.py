# apps/especial/views_carga_cueanexo.py
# -*- coding: utf-8 -*-

from django.shortcuts import render

from .permisos import especial_required
from .views_contexto import (
    contexto_base,
    datos_establecimiento_items,
)


@especial_required
def carga_cueanexo(request):
    """Vista que muestra los datos del CUE-Anexo seleccionado."""
    context = contexto_base(request, "cueanexo", "Datos CUE-Anexo Educación Especial")
    especial_context = context["especial_context"]

    context.update(
        {
            "establecimiento_items": datos_establecimiento_items(
                especial_context["establecimiento"]
            ),
        }
    )
    return render(request, "especial/carga_cueanexo_especial.html", context)