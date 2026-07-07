# apps/especial/views_carga_seccion.py
# -*- coding: utf-8 -*-

from django.contrib import messages
from django.db import transaction
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render

from .forms import EspecialSeccionForm
from .models import SeccionEspecial
from .permisos import especial_required
from .views_contexto import contexto_base, redirect_con_contexto


def _secciones_queryset(especial_context):
    """QuerySet de secciones filtrado por CUE-Anexo y ciclo."""
    return (
        SeccionEspecial.objects.filter(
            cueanexo=especial_context["cueanexo"],
            ciclo=especial_context["ciclo"],
        )
        .select_related(
            "cd_tipo_seccion",
            "turno",
            "rango_etario",
            "modalidad",
            "tipo_estructura_especial",
        )
        .annotate(
            alumnos_activos=Count(
                "alumnos",
                filter=Q(alumnos__estado__in=["activo", "inactivo"]),
            )
        )
        .order_by("nombre_seccion")
    )


def _seccion_segura(seccion_id, especial_context):
    """Obtiene una sección validando que pertenezca al CUE-Anexo y ciclo actual."""
    return get_object_or_404(
        SeccionEspecial.objects.filter(
            cueanexo=especial_context["cueanexo"],
            ciclo=especial_context["ciclo"],
        ).select_related(
            "cd_tipo_seccion",
            "turno",
            "rango_etario",
            "modalidad",
            "tipo_estructura_especial",
        ),
        pk=seccion_id,
    )


@especial_required
def carga_seccion(request):
    """Vista principal de gestión de secciones."""
    context = contexto_base(request, "secciones", "Secciones Educación Especial")
    especial_context = context["especial_context"]

    if request.GET.get("accion") == "agregar":
        return redirect(redirect_con_contexto("especial:carga_seccion_nueva", especial_context))

    secciones = (
        list(_secciones_queryset(especial_context))
        if especial_context["puede_operar"]
        else []
    )

    context.update(
        {
            "secciones": secciones,
            "total_secciones": len(secciones),
        }
    )
    return render(request, "especial/carga_seccion_especial.html", context)


def _guardar_seccion(form, especial_context, user):
    """Guarda una sección asignando CUE-Anexo, ciclo y auditoría."""
    with transaction.atomic():
        seccion = form.save(commit=False)
        seccion.cueanexo = especial_context["cueanexo"]
        seccion.ciclo = especial_context["ciclo"]
        if not seccion.pk:
            seccion.creado_por = user
        seccion.actualizado_por = user
        seccion.save()
    return seccion


@especial_required
def carga_seccion_form(request, seccion_id=None):
    """Formulario de creación/edición de sección."""
    context = contexto_base(request, "secciones", "Secciones Educación Especial")
    especial_context = context["especial_context"]

    if not especial_context["puede_operar"]:
        messages.error(request, "Seleccioná un CUE-Anexo y un ciclo para cargar secciones.")
        return redirect(redirect_con_contexto("especial:carga_seccion", especial_context))

    seccion_edicion = _seccion_segura(seccion_id, especial_context) if seccion_id else None
    
    if not seccion_edicion:
        seccion_edicion = SeccionEspecial(
            cueanexo=especial_context["cueanexo"],
            ciclo=especial_context["ciclo"]
        )

    if request.method == "POST":
        form = EspecialSeccionForm(
            request.POST,
            instance=seccion_edicion,
            ciclo=especial_context["ciclo"],
        )

        if form.is_valid():
            _guardar_seccion(form, especial_context, request.user)
            messages.success(request, "Sección guardada correctamente.")
            return redirect(redirect_con_contexto("especial:carga_seccion", especial_context))

        messages.error(request, "Revisá los datos del formulario para guardar la sección.")
    else:
        form = EspecialSeccionForm(instance=seccion_edicion, ciclo=especial_context["ciclo"])

    context.update(
        {
            "form": form,
            "seccion_edicion": seccion_edicion,
            "form_title": "Editar Sección" if seccion_edicion else "Agregar Sección",
        }
    )
    return render(request, "especial/form_seccion_especial.html", context)