# apps/especial/views_ciclo.py
# -*- coding: utf-8 -*-

from urllib.parse import urlencode

from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render

from .forms import EspecialCicloForm
from .models import EspecialCiclo, usuario_es_admin_especial
from .permisos import especial_required
from .views_contexto import contexto_base, redirect_con_contexto


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
    if not usuario_es_admin_especial(request.user):
        raise PermissionDenied("Solo el rol Administrador puede administrar ciclos de Educación Especial.")


@especial_required
def administrar_ciclos(request):
    """Vista para administrar ciclos lectivos (solo administradores)."""
    _exigir_admin(request)
    context = contexto_base(request, "ciclos", "Ciclos lectivos Educación Especial")
    especial_context = context["especial_context"]

    if request.method == "POST":
        form = EspecialCicloForm(request.POST)
        accion = request.POST.get("accion", "crear")

        if accion == "marcar_actual":
            ciclo = get_object_or_404(EspecialCiclo, pk=request.POST.get("ciclo_id"))
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

    context.update(
        {
            "form": form,
            "ciclos_admin": EspecialCiclo.objects.all().order_by("-anio"),
        }
    )
    return render(request, "especial/ciclos_especial.html", context)