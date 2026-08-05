# -*- coding: utf-8 -*-

from urllib.parse import urlencode

from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render

from .forms import CefCicloForm
from .models import CefCiclo, CefDatosRelevamiento
from .permisos import cef_required, get_permisos_cef_request
from .views_contexto import (
    contexto_base,
    invalidar_cache_ciclos_cef,
    redirect_con_contexto,
)


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
    if not get_permisos_cef_request(request)["es_admin"]:
        raise PermissionDenied("Solo el rol Administrador puede administrar ciclos CEF.")


def _copiar_datos_relevamiento_ciclo_anterior(ciclo_nuevo, user):
    ciclo_origen = CefCiclo.objects.filter(anio=ciclo_nuevo.anio - 1).first()
    if ciclo_origen is None:
        return 0

    datos_origen = CefDatosRelevamiento.objects.filter(
        ciclo=ciclo_origen
    ).select_related(
        "beneficio_alimentario_gratuito",
        "fuente_financiamiento",
        "prestacion_tipo",
        "espacio_comedor",
        "c_orientacion",
    )

    cantidad_copiada = 0
    for datos in datos_origen:
        CefDatosRelevamiento.objects.create(
            ciclo=ciclo_nuevo,
            cueanexo=datos.cueanexo,
            beneficio_alimentario_gratuito=datos.beneficio_alimentario_gratuito,
            fuente_financiamiento=datos.fuente_financiamiento,
            prestacion_tipo=datos.prestacion_tipo,
            espacio_comedor=datos.espacio_comedor,
            c_orientacion=datos.c_orientacion,
            observaciones=datos.observaciones,
            creado_por=user,
            actualizado_por=user,
        )
        cantidad_copiada += 1

    return cantidad_copiada


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
            invalidar_cache_ciclos_cef()
            messages.success(request, "Ciclo actual actualizado correctamente.")
            return _redirect_admin_ciclos(cef_context, ciclo)

        if form.is_valid():
            with transaction.atomic():
                if form.cleaned_data.get("actual"):
                    CefCiclo.objects.filter(actual=True).update(actual=False)
                ciclo = form.save(user=request.user)
                _copiar_datos_relevamiento_ciclo_anterior(ciclo, request.user)
            invalidar_cache_ciclos_cef()
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
