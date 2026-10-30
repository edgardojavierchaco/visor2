# -*- coding: utf-8 -*-

from urllib.parse import urlencode

from django.contrib import messages
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET, require_POST

from .forms import CefCicloAnualForm, CefCicloEdicionForm, CefCicloForm
from .models import CefCiclo
from .permisos import cef_required, get_permisos_cef_request
from .services_anual import (
    generar_ciclo_siguiente,
    origen_anual_previsualizable,
    prevalidar_generacion_anual,
)
from .views_contexto import (
    actualizar_habilitacion_ciclo,
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


def _render_prevalidacion_anual(request, ciclo_solicitado, form_anual=None):
    context = contexto_base(
        request,
        "ciclos",
        "Prevalidación anual CEF",
    )
    cef_context = context["cef_context"]
    if not origen_anual_previsualizable(ciclo_solicitado):
        messages.error(
            request,
            (
                "La previsualización anual sólo está disponible para el ciclo "
                "actual abierto o para el último ciclo cerrado sin sucesor."
            ),
        )
        return redirect(
            redirect_con_contexto("cef:administrar_ciclos", cef_context)
        )

    resultado = prevalidar_generacion_anual(ciclo_solicitado)
    context.update(
        {
            "resultado": resultado,
            "form_anual": form_anual if form_anual is not None else CefCicloAnualForm(
                anio_destino=ciclo_solicitado.anio + 1,
            ),
            "volver_url": redirect_con_contexto(
                "cef:administrar_ciclos",
                cef_context,
            ),
        }
    )
    return render(request, "cef/prevalidacion_ciclo_anual_cef.html", context)



@cef_required
@require_GET
def prevalidar_ciclo_anual(request, ciclo_id):
    _exigir_admin(request)
    ciclo = get_object_or_404(CefCiclo, pk=ciclo_id)
    return _render_prevalidacion_anual(request, ciclo)

@cef_required
@require_POST
def generar_ciclo_anual(request, ciclo_id):
    _exigir_admin(request)
    ciclo_origen = get_object_or_404(CefCiclo, pk=ciclo_id)
    form_anual = CefCicloAnualForm(request.POST, anio_destino=ciclo_origen.anio + 1)
    if not form_anual.is_valid():
        return _render_prevalidacion_anual(request, ciclo_origen, form_anual)
    try:
        resumen = generar_ciclo_siguiente(
            ciclo_id,
            request.user,
            fecha_inicio=form_anual.cleaned_data["fecha_inicio"],
            fecha_fin=form_anual.cleaned_data.get("fecha_fin"),
        )
    except ValidationError as exc:
        form_anual.add_error(None, exc)
        return _render_prevalidacion_anual(request, ciclo_origen, form_anual)

    invalidar_cache_ciclos_cef()
    context = contexto_base(request, "ciclos", "Generación anual CEF")
    cef_context = context["cef_context"]
    ciclo_destino = resumen["ciclo_destino"]
    cef_context["ciclo"] = ciclo_destino
    cef_context["querystring"] = _query_ciclo(cef_context, ciclo_destino)
    actualizar_habilitacion_ciclo(cef_context, get_permisos_cef_request(request))
    context.update(
        {
            "resumen": resumen,
            "volver_url": redirect_con_contexto(
                "cef:administrar_ciclos",
                cef_context,
            ),
        }
    )
    return render(request, "cef/generacion_ciclo_anual_resultado_cef.html", context)


@cef_required
def administrar_ciclos(request):
    _exigir_admin(request)
    context = contexto_base(request, "ciclos", "Ciclos lectivos CEF")
    cef_context = context["cef_context"]
    form = CefCicloForm()
    form_actual = None

    if request.method == "POST":
        accion = request.POST.get("accion", "crear")

        if accion == "editar_actual":
            with transaction.atomic():
                ciclo = get_object_or_404(
                    CefCiclo.objects.select_for_update(),
                    pk=request.POST.get("ciclo_id"),
                )
                if not ciclo.actual or ciclo.cerrado:
                    messages.error(
                        request,
                        "Sólo puede editarse el ciclo actual mientras permanece abierto.",
                    )
                    return _redirect_admin_ciclos(cef_context)
                form_actual = CefCicloEdicionForm(request.POST, instance=ciclo)
                if form_actual.is_valid():
                    ciclo = form_actual.save(user=request.user)
                else:
                    ciclo = None
            if ciclo is not None:
                invalidar_cache_ciclos_cef()
                messages.success(request, "Ciclo actual actualizado correctamente.")
                return _redirect_admin_ciclos(cef_context, ciclo)
            messages.error(request, "Revisá los datos del ciclo actual.")

        elif accion == "cerrar_actual":
            with transaction.atomic():
                ciclo = get_object_or_404(
                    CefCiclo.objects.select_for_update(),
                    pk=request.POST.get("ciclo_id"),
                )
                if ciclo.cerrado:
                    messages.error(request, "El ciclo ya se encuentra cerrado.")
                    return _redirect_admin_ciclos(cef_context, ciclo)
                if not ciclo.actual:
                    messages.error(
                        request,
                        "Sólo puede cerrarse el ciclo marcado actualmente como actual.",
                    )
                    return _redirect_admin_ciclos(cef_context)
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
            invalidar_cache_ciclos_cef()
            messages.success(
                request,
                (
                    f"Ciclo {ciclo.anio} cerrado correctamente. Su información "
                    "quedó en modo sólo lectura."
                ),
            )
            return _redirect_admin_ciclos(cef_context, ciclo)

        elif accion == "crear":
            if CefCiclo.objects.exists():
                messages.error(
                    request,
                    (
                        "La creación manual sólo está disponible para el primer ciclo CEF. "
                        "Para avanzar al ciclo siguiente usá la continuidad anual."
                    ),
                )
                return _redirect_admin_ciclos(cef_context)
            form = CefCicloForm(request.POST)
            if form.is_valid():
                try:
                    with transaction.atomic():
                        if CefCiclo.objects.exists():
                            messages.error(request, "Otro usuario ya creó el primer ciclo CEF.")
                            return _redirect_admin_ciclos(cef_context)
                        ciclo = form.save(user=request.user)
                except IntegrityError:
                    messages.error(
                        request,
                        "No se pudo crear el ciclo porque los datos cambiaron durante "
                        "la operación. No se realizó ningún cambio. Revisá los ciclos existentes.",
                    )
                    return _redirect_admin_ciclos(cef_context)
                invalidar_cache_ciclos_cef()
                messages.success(request, "Ciclo creado correctamente.")
                return _redirect_admin_ciclos(cef_context, ciclo)
        else:
            messages.error(request, "La acción solicitada no es válida.")

    ciclos_admin = list(CefCiclo.objects.all().order_by("-anio"))
    ciclo_actual = next(
        (
            ciclo
            for ciclo in ciclos_admin
            if ciclo.actual and not ciclo.cerrado
        ),
        None,
    )
    if ciclo_actual:
        cef_context["ciclo"] = ciclo_actual
        cef_context["querystring"] = _query_ciclo(cef_context, ciclo_actual)
        actualizar_habilitacion_ciclo(cef_context, get_permisos_cef_request(request))
        ciclo_origen_anual = ciclo_actual
    else:
        ciclo_mas_reciente = ciclos_admin[0] if ciclos_admin else None
        ciclo_origen_anual = (
            ciclo_mas_reciente
            if ciclo_mas_reciente
            and ciclo_mas_reciente.cerrado
            and not ciclo_mas_reciente.actual
            else None
        )
    if form_actual is None and ciclo_actual:
        form_actual = CefCicloEdicionForm(instance=ciclo_actual)

    context.update(
        {
            "form": form,
            "form_actual": form_actual,
            "ciclo_actual_admin": ciclo_actual,
            "ciclo_origen_anual": ciclo_origen_anual,
            "ciclos_admin": ciclos_admin,
        }
    )
    return render(request, "cef/ciclos_cef.html", context)
