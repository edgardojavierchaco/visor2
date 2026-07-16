# -*- coding: utf-8 -*-

from urllib.parse import urlencode

from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render

from .forms import CefCicloForm
from .models import CefCiclo, usuario_es_admin_cef
from .permisos import cef_required
from .views_contexto import contexto_base, redirect_con_contexto


def _query_ciclo(cef_context, ciclo):
    params = {}
    if cef_context.get("cueanexo"):
        params["cueanexo"] = cef_context["cueanexo"]
    if ciclo:
        params["ciclo"] = ciclo.pk
    return urlencode(params)


def _redirect_admin_ciclos(cef_context, ciclo=None):
    if ciclo is None:
        return redirect(redirect_con_contexto("cef:administrar_ciclos", cef_context))
    querystring = _query_ciclo(cef_context, ciclo)
    return redirect(
        redirect_con_contexto("cef:administrar_ciclos", {"querystring": querystring})
    )


def _exigir_admin(request):
    if not usuario_es_admin_cef(request.user):
        raise PermissionDenied("Solo el rol Administrador puede administrar ciclos CEF.")


@cef_required
def administrar_ciclos(request):
    _exigir_admin(request)
    context = contexto_base(request, "ciclos", "Ciclos lectivos CEF")
    cef_context = context["cef_context"]

    if request.method == "POST":
        form = CefCicloForm(request.POST)
        accion = request.POST.get("accion", "crear")

        if accion == "marcar_actual":
            ciclo = get_object_or_404(CefCiclo, pk=request.POST.get("ciclo_id"))
            with transaction.atomic():
                CefCiclo.objects.filter(actual=True).exclude(pk=ciclo.pk).update(actual=False)
                ciclo.actual = True
                ciclo.activo = True
                ciclo.actualizado_por = request.user
                ciclo.save(update_fields=["actual", "activo", "actualizado_por", "actualizado_en"])
            messages.success(request, "Ciclo actual actualizado correctamente.")
            return _redirect_admin_ciclos(cef_context, ciclo)

        if form.is_valid():
            with transaction.atomic():
                if form.cleaned_data.get("actual"):
                    CefCiclo.objects.filter(actual=True).update(actual=False)
                ciclo = form.save(user=request.user)
            messages.success(request, "Ciclo creado correctamente.")
            return _redirect_admin_ciclos(
                cef_context,
                ciclo if form.cleaned_data.get("actual") else None,
            )
    else:
        form = CefCicloForm()

    context.update(
        {
            "form": form,
            "ciclos_admin": CefCiclo.objects.all().order_by("-anio"),
        }
    )
    return render(request, "cef/ciclos_cef.html", context)
