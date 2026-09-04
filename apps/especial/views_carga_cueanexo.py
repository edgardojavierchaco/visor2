# apps/especial/views_carga_cueanexo.py
# -*- coding: utf-8 -*-

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db import transaction
from django.shortcuts import redirect, render

from .forms import EspecialDatosCUEAnexoForm
from .models import EspecialCiclo, EspecialDatosCUEAnexo
from .permisos import especial_required
from .views_contexto import (
    contexto_base,
    datos_establecimiento_items,
    redirect_con_contexto,
    render_especial,
)


@especial_required
def carga_cueanexo(request):
    """Vista que muestra los datos del CUE-Anexo seleccionado."""
    context = contexto_base(request, "cueanexo")
    especial_context = context["especial_context"]

    context.update(
        {
            "datos": _datos_cueanexo(especial_context),
            "establecimiento_items": datos_establecimiento_items(
                especial_context["establecimiento"]
            ),
        }
    )
    return render_especial(
        request,
        "especial/carga_cueanexo_especial.html",
        context,
        "especial/partials/datos_cueanexo_fragmento_especial.html",
    )


def _datos_cueanexo(especial_context):
    if not especial_context["puede_consultar"]:
        return None
    return (
        EspecialDatosCUEAnexo.objects.filter(
            cueanexo=especial_context["cueanexo"], ciclo=especial_context["ciclo"]
        )
        .select_related(
            "beneficio_alimentario_gratuito",
            "fuente_financiamiento",
            "prestacion_tipo",
            "espacio_comedor",
        )
        .first()
    )


@especial_required
def editar_datos_cueanexo(request):
    context = contexto_base(request, "cueanexo", "Modificar datos CUE-Anexo Especial")
    especial_context = context["especial_context"]
    datos = _datos_cueanexo(especial_context)
    if especial_context["ciclo_cerrado"]:
        messages.warning(request, "El ciclo está cerrado. Los datos son de sólo lectura.")
        return redirect(redirect_con_contexto("especial:carga_cueanexo", especial_context))
    if not especial_context["puede_operar"]:
        form = None
        catalogos_faltantes = []
    elif request.method == "POST":
        form = EspecialDatosCUEAnexoForm(request.POST, instance=datos)
        form.instance.cueanexo = especial_context["cueanexo"]
        form.instance.ciclo = especial_context["ciclo"]
        catalogos_faltantes = form.catalogos_faltantes()
        if form.is_valid() and not catalogos_faltantes:
            obj = form.save(commit=False)
            if not obj.pk:
                obj.creado_por = request.user
            obj.actualizado_por = request.user
            try:
                with transaction.atomic():
                    ciclo = EspecialCiclo.objects.select_for_update().get(pk=obj.ciclo_id)
                    if ciclo.cerrado:
                        raise ValidationError("El ciclo seleccionado está cerrado.")
                    obj.save()
            except ValidationError as exc:
                form.add_error(None, "; ".join(exc.messages))
                messages.error(request, "; ".join(exc.messages))
            else:
                messages.success(request, "Datos del CUE-Anexo guardados correctamente.")
                return redirect(redirect_con_contexto("especial:carga_cueanexo", especial_context))
        if catalogos_faltantes:
            messages.error(request, "Faltan catálogos para completar esta carga.")
    else:
        form = EspecialDatosCUEAnexoForm(instance=datos)
        catalogos_faltantes = form.catalogos_faltantes()
    context.update({
        "form": form,
        "datos": datos,
        "catalogos_faltantes": catalogos_faltantes,
        "establecimiento_items": datos_establecimiento_items(especial_context["establecimiento"]),
    })
    return render(request, "especial/editar_datos_cueanexo_especial.html", context)
