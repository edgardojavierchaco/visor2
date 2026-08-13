# apps/especial/views_ciclo.py
# -*- coding: utf-8 -*-

from multiprocessing import context
from urllib.parse import urlencode

from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render

from .forms import EspecialCicloForm
from .models import EspecialCiclo
from .permisos import especial_required, get_permisos_especial_request
from .services.previsualizacion_anual import origen_anual_previsualizable, prevalidar_generacion_anual
from .views_contexto import contexto_base, redirect_con_contexto, render_especial


def _query_ciclo(especial_context, ciclo):
    params = {}
    if especial_context.get("cueanexo"):
        params["cueanexo"] = especial_context["cueanexo"]
    if ciclo:
        params["ciclo"] = ciclo.pk
    return urlencode(params)


def _redirect_admin_ciclos(especial_context, ciclo=None):
    if ciclo is None:
        return redirect(redirect_con_contexto("especial:administrar_ciclos", especial_context))
    querystring = _query_ciclo(especial_context, ciclo)
    return redirect(
        redirect_con_contexto("especial:administrar_ciclos", {"querystring": querystring})
    )


def _exigir_admin(request):
    if not get_permisos_especial_request(request)["es_admin"]:
        raise PermissionDenied("Solo el rol Administrador puede administrar ciclos de Educación Especial.")


@especial_required
def prevalidar_ciclo_anual(request, ciclo_id):
    """Muestra una simulación anual de sólo lectura para administradores."""
    _exigir_admin(request)
    context = contexto_base(request, "ciclos", "Previsualización anual Especial")
    especial_context = context["especial_context"]
    ciclo = EspecialCiclo.objects.filter(pk=ciclo_id).first()
    if ciclo is None or not origen_anual_previsualizable(ciclo):
        messages.error(
            request,
            (
                "La previsualización anual sólo está disponible para el ciclo "
                "actual abierto o para el último ciclo cerrado sin sucesor."
            ),
        )
        return redirect(redirect_con_contexto("especial:administrar_ciclos", especial_context))

    resultado = prevalidar_generacion_anual(ciclo, especial_context.get("cueanexo"))
    context.update(
        {
            "origen": ciclo,
            "siguiente_anio": ciclo.anio + 1,
            "resultado": resultado,
            "volver_url": redirect_con_contexto(
                "especial:administrar_ciclos", especial_context
            ),
        }
    )
    return render(request, "especial/prevalidacion_ciclo_anual_especial.html", context)


@especial_required
def administrar_ciclos(request):
    """Vista para administrar ciclos lectivos (solo administradores)."""
    _exigir_admin(request)
    context = contexto_base(request, "ciclos")
    especial_context = context["especial_context"]

    if request.method == "POST":
        form = EspecialCicloForm(request.POST)
        accion = request.POST.get("accion", "crear")

        if accion == "cerrar_actual":
            ciclo_id = request.POST.get("ciclo_id")
            with transaction.atomic():
                ciclo = get_object_or_404(
                    EspecialCiclo.objects.select_for_update(),
                    pk=ciclo_id,
                )
                if ciclo.cerrado:
                    messages.error(request, "El ciclo ya está cerrado.")
                    return _redirect_admin_ciclos(especial_context, ciclo)
                if not ciclo.actual:
                    messages.error(request, "Sólo se puede cerrar el ciclo actual.")
                    return _redirect_admin_ciclos(especial_context, ciclo)
                ciclo.cerrado = True
                ciclo.actual = False
                ciclo.activo = True
                ciclo.actualizado_por = request.user
                ciclo.save(
                    update_fields=[
                        "cerrado",
                        "actual",
                        "activo",
                        "actualizado_por",
                        "actualizado_en",
                    ]
                )
            messages.success(request, "Ciclo cerrado correctamente.")
            return _redirect_admin_ciclos(especial_context, ciclo)

        if accion == "guardar_actual":
            ciclo_id = request.POST.get("ciclo_id")
            with transaction.atomic():
                ciclo = get_object_or_404(
                    EspecialCiclo.objects.select_for_update(),
                    pk=ciclo_id,
                )
                if ciclo.cerrado:
                    messages.error(request, "El ciclo seleccionado está cerrado y sólo puede consultarse.")
                    return _redirect_admin_ciclos(especial_context, ciclo)
                form_data = {
                    "anio": ciclo.anio,
                    "descripcion": request.POST.get("descripcion", ""),
                    "fecha_inicio": ciclo.fecha_inicio,
                    "fecha_fin": request.POST.get("fecha_fin") or "",
                    "activo": "on" if ciclo.activo else "",
                    "actual": "on" if ciclo.actual else "",
                }
                form_actual = EspecialCicloForm(form_data, instance=ciclo)
                if not form_actual.is_valid():
                    for error in form_actual.errors.values():
                        messages.error(request, " ".join(error))
                    return _redirect_admin_ciclos(especial_context, ciclo)
                ciclo = form_actual.save(user=request.user)
            messages.success(request, "Cambios del ciclo guardados correctamente.")
            return _redirect_admin_ciclos(especial_context, ciclo)

        if accion == "marcar_actual":
            ciclo = get_object_or_404(EspecialCiclo, pk=request.POST.get("ciclo_id"))
            if ciclo.cerrado:
                messages.error(request, "Un ciclo cerrado no puede marcarse como ciclo actual.")
                return _redirect_admin_ciclos(especial_context, ciclo)
            with transaction.atomic():
                EspecialCiclo.objects.filter(actual=True).exclude(pk=ciclo.pk).update(actual=False)
                ciclo.actual = True
                ciclo.activo = True
                ciclo.actualizado_por = request.user
                ciclo.save(update_fields=["actual", "activo", "actualizado_por", "actualizado_en"])
            messages.success(request, "Ciclo actual actualizado correctamente.")
            return _redirect_admin_ciclos(especial_context, ciclo)

        if form.is_valid():
            with transaction.atomic():
                if form.cleaned_data.get("actual"):
                    EspecialCiclo.objects.filter(actual=True).update(actual=False)
                ciclo = form.save(user=request.user)
            messages.success(request, "Ciclo creado correctamente.")
            return _redirect_admin_ciclos(
                especial_context,
                ciclo if form.cleaned_data.get("actual") else None,
            )
    else:
        form = EspecialCicloForm()
    ciclos_admin = list(EspecialCiclo.objects.all().order_by("-anio"))

    ciclo_actual_admin = next(
        (ciclo for ciclo in ciclos_admin if ciclo.actual),
        None,
    )
    context.update(
        {
            "form": form,
            "ciclos_admin": ciclos_admin,
            "ciclo_actual_admin": ciclo_actual_admin,
        }
    )
    return render_especial(
        request,
        "especial/ciclos_especial.html",
        context,
        "especial/partials/ciclos_fragmento_especial.html",
    )
