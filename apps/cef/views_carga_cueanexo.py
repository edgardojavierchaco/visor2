# -*- coding: utf-8 -*-

from django.contrib import messages
from django.shortcuts import redirect, render

from .forms import CefDatosRelevamientoForm
from .models import CefDatosRelevamiento
from .permisos import cef_required
from .views_contexto import (
    contexto_base,
    datos_establecimiento_items,
    redirect_con_contexto,
)


def _datos_relevamiento(cef_context):
    if not cef_context["puede_operar"]:
        return None

    return (
        CefDatosRelevamiento.objects.filter(
            cueanexo=cef_context["cueanexo"],
            ciclo=cef_context["ciclo"],
        )
        .select_related(
            "beneficio_alimentario_gratuito",
            "fuente_financiamiento",
            "prestacion_tipo",
            "espacio_comedor",
            "c_orientacion",
        )
        .first()
    )


@cef_required
def carga_cueanexo(request):
    context = contexto_base(request, "cueanexo", "Datos CUE-Anexo CEF")
    cef_context = context["cef_context"]
    datos = _datos_relevamiento(cef_context)

    context.update(
        {
            "datos": datos,
            "establecimiento_items": datos_establecimiento_items(
                cef_context["establecimiento"]
            ),
        }
    )
    return render(request, "cef/carga_cueanexo_cef.html", context)


@cef_required
def editar_datos_cueanexo(request):
    context = contexto_base(request, "cueanexo", "Modificar datos CUE-Anexo CEF")
    cef_context = context["cef_context"]
    datos = _datos_relevamiento(cef_context)

    if not cef_context["puede_operar"]:
        form = None
        catalogos_faltantes = []
    elif request.method == "POST":
        form = CefDatosRelevamientoForm(request.POST, instance=datos)
        catalogos_faltantes = form.catalogos_faltantes()

        if form.is_valid() and not catalogos_faltantes:
            obj = form.save(commit=False)
            obj.cueanexo = cef_context["cueanexo"]
            obj.ciclo = cef_context["ciclo"]
            if not obj.pk:
                obj.creado_por = request.user
            obj.actualizado_por = request.user
            obj.save()
            messages.success(request, "Datos del CUE-Anexo guardados correctamente.")
            return redirect(redirect_con_contexto("cef:carga_cueanexo", cef_context))

        if catalogos_faltantes:
            messages.error(request, "Faltan catálogos para completar esta carga.")
    else:
        form = CefDatosRelevamientoForm(instance=datos)
        catalogos_faltantes = form.catalogos_faltantes()

    context.update(
        {
            "form": form,
            "datos": datos,
            "catalogos_faltantes": catalogos_faltantes,
            "establecimiento_items": datos_establecimiento_items(
                cef_context["establecimiento"]
            ),
        }
    )
    return render(request, "cef/editar_datos_cueanexo_cef.html", context)
