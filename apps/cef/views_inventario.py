# -*- coding: utf-8 -*-

from django.contrib import messages
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render

from .forms import CefInventarioMaterialForm
from .models import CefInventarioMaterial
from .permisos import cef_required
from .views_contexto import contexto_base, redirect_con_contexto


def _inventario_queryset(cef_context):
    return (
        CefInventarioMaterial.objects.filter(
            cueanexo=cef_context["cueanexo"],
            ciclo=cef_context["ciclo"],
        )
        .select_related("material")
        .order_by("material__orden", "material__nombre")
    )


def _item_seguro(item_id, cef_context):
    return get_object_or_404(
        CefInventarioMaterial.objects.filter(
            cueanexo=cef_context["cueanexo"],
            ciclo=cef_context["ciclo"],
        ).select_related("material"),
        pk=item_id,
    )


@cef_required
def carga_inventario(request, item_id=None):
    context = contexto_base(request, "inventario", "Inventario CEF")
    cef_context = context["cef_context"]
    item_edicion = None
    mostrar_form = request.GET.get("accion") == "agregar" or bool(item_id)

    if cef_context["puede_operar"] and item_id:
        item_edicion = _item_seguro(item_id, cef_context)

    if not cef_context["puede_operar"]:
        form = None
        inventario = []
    elif request.method == "POST":
        mostrar_form = True
        form = CefInventarioMaterialForm(request.POST, instance=item_edicion)

        if form.is_valid():
            material = form.cleaned_data["material"]
            existente = (
                CefInventarioMaterial.objects.filter(
                    cueanexo=cef_context["cueanexo"],
                    ciclo=cef_context["ciclo"],
                    material=material,
                )
                .exclude(pk=getattr(item_edicion, "pk", None))
                .first()
            )

            with transaction.atomic():
                if existente:
                    form = CefInventarioMaterialForm(request.POST, instance=existente)
                    form.is_valid()
                item = form.save(commit=False)
                item.cueanexo = cef_context["cueanexo"]
                item.ciclo = cef_context["ciclo"]
                if not item.pk:
                    item.creado_por = request.user
                item.actualizado_por = request.user
                item.save()

            if existente:
                messages.success(
                    request,
                    "El material ya existía para este CEF y ciclo; se actualizó la fila existente.",
                )
            else:
                messages.success(request, "Material de inventario guardado correctamente.")
            return redirect(redirect_con_contexto("cef:carga_inventario", cef_context))
    elif mostrar_form:
        form = CefInventarioMaterialForm(instance=item_edicion)
    else:
        form = None

    inventario = (
        list(_inventario_queryset(cef_context)) if cef_context["puede_operar"] else []
    )

    context.update(
        {
            "form": form,
            "inventario": inventario,
            "item_edicion": item_edicion,
            "mostrar_form": mostrar_form,
        }
    )
    return render(request, "cef/inventario_cef.html", context)
