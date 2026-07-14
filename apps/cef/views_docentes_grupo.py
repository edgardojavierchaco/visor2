# -*- coding: utf-8 -*-

import re
from urllib.parse import urlencode

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone

from .forms import CefBusquedaDocenteForm, CefDocenteGrupoForm
from .models import (
    CefDocenteBnh,
    CefDocenteGrupo,
    CefGrupo,
    PADRON_DB_ALIAS,
    docentes_grupo_tiene_duplicados_activos,
    validar_docente_grupo_activo,
)
from .permisos import cef_required
from .views_contexto import contexto_base, redirect_con_contexto
from .views_profesores import (
    MSG_BANCO_DOCENTES_PENDIENTE,
    _asegurar_docente_banco,
    _docente_row,
    _url_carga_profesor,
)


def _solo_digitos(valor):
    return re.sub(r"\D", "", str(valor or ""))


def _is_ajax(request):
    return request.headers.get("x-requested-with") == "XMLHttpRequest"


def _grupo_seguro(grupo_id, cef_context):
    return get_object_or_404(
        CefGrupo.objects.filter(
            cueanexo=cef_context["cueanexo"],
            ciclo=cef_context["ciclo"],
        )
        .select_related("actividad", "turno", "nivel", "rango_etario")
        .prefetch_related("dias_funcionamiento__dia_semana"),
        pk=grupo_id,
    )


def _dias_texto(grupo):
    return ", ".join(
        str(item.dia_semana) for item in grupo.dias_funcionamiento.all()
    )


def _grupo_rotulo(grupo):
    return f"Grupo {grupo.actividad} Nro. {grupo.numero}"


def _asignacion_docente_activa(grupo, cuil):
    if not cuil:
        return None

    return (
        CefDocenteGrupo.objects.filter(
            grupo=grupo,
            docente_cuil=cuil,
            estado=CefDocenteGrupo.Estado.ACTIVO,
        )
        .first()
    )


def _docentes_grupo(grupo):
    return (
        CefDocenteGrupo.objects.filter(grupo=grupo)
        .order_by("estado", "rol", "docente_nombre_snapshot", "docente_cuil")
    )


def _buscar_docente(cuil):
    return (
        CefDocenteBnh.objects.using(PADRON_DB_ALIAS)
        .filter(cuil=cuil)
        .first()
    )


def _url_modal_grupo(grupo, cef_context, cuil=""):
    params = {}
    if cef_context.get("cueanexo"):
        params["cueanexo"] = cef_context["cueanexo"]
    if cef_context.get("ciclo"):
        params["ciclo"] = cef_context["ciclo"].pk
    params["abrir_modal_docente"] = "1"
    if cuil:
        params["cuil"] = cuil
    return f"{reverse('cef:docentes_grupo', kwargs={'grupo_id': grupo.pk})}?{urlencode(params)}"


def _url_docentes_grupo(grupo, cef_context):
    params = {}
    if cef_context.get("cueanexo"):
        params["cueanexo"] = cef_context["cueanexo"]
    if cef_context.get("ciclo"):
        params["ciclo"] = cef_context["ciclo"].pk
    querystring = urlencode(params)
    url = reverse("cef:docentes_grupo", kwargs={"grupo_id": grupo.pk})
    return f"{url}?{querystring}" if querystring else url


def _url_gestionar_grupo(grupo, cef_context):
    params = {}
    if cef_context.get("cueanexo"):
        params["cueanexo"] = cef_context["cueanexo"]
    if cef_context.get("ciclo"):
        params["ciclo"] = cef_context["ciclo"].pk
    querystring = urlencode(params)
    url = reverse("cef:gestionar_grupo", kwargs={"grupo_id": grupo.pk})
    return f"{url}?{querystring}" if querystring else url


def _errores_form(form):
    return " ".join(error for errors in form.errors.values() for error in errors)


def _ajax_docentes_grupo_response(request, context, ok, message):
    docentes = list(context.get("docentes") or [])
    context["docentes"] = docentes
    context["docentes_activos_count"] = len(
        [
            docente
            for docente in docentes
            if docente.estado == CefDocenteGrupo.Estado.ACTIVO
        ]
    )
    if context.get("grupo"):
        context["docentes_activos_duplicados"] = docentes_grupo_tiene_duplicados_activos(
            context["grupo"]
        )
    return JsonResponse(
        {
            "ok": ok,
            "message": message,
            "modal_html": render_to_string(
                "cef/modal_busqueda_docente_cef.html",
                context,
                request=request,
            ),
            "fragment_selector": "[data-cef-fragment='docentes-grupo']",
            "fragment_html": render_to_string(
                "cef/docentes_grupo_lista_cef.html",
                context,
                request=request,
            ),
            "close_modal": ok,
        }
    )


def dar_baja_docente_grupo(asignacion, user):
    if asignacion.estado != CefDocenteGrupo.Estado.ACTIVO:
        raise ValidationError("La asignación ya se encuentra dada de baja.")

    asignacion.estado = CefDocenteGrupo.Estado.BAJA
    if not asignacion.fecha_hasta:
        asignacion.fecha_hasta = timezone.localdate()
    asignacion.actualizado_por = user
    asignacion.save()
    return asignacion


def dar_alta_docente_grupo(asignacion, user):
    if asignacion.estado == CefDocenteGrupo.Estado.ACTIVO:
        raise ValidationError("La asignación ya se encuentra activa.")

    validar_docente_grupo_activo(
        asignacion.grupo,
        asignacion.docente_cuil,
        asignacion.rol,
    )

    try:
        with transaction.atomic():
            return CefDocenteGrupo.objects.create(
                grupo=asignacion.grupo,
                docente_cuil=asignacion.docente_cuil,
                rol=asignacion.rol,
                estado=CefDocenteGrupo.Estado.ACTIVO,
                fecha_desde=timezone.localdate(),
                creado_por=user,
                actualizado_por=user,
            )
    except IntegrityError:
        raise ValidationError("No se pudo reasignar el profesor. Verificá que no exista un docente o rol activo duplicado.")


def _baja_docente(request, grupo, cef_context):
    try:
        docente_grupo_id = int(request.POST.get("docente_grupo_id"))
    except (TypeError, ValueError):
        messages.error(request, "La asignación seleccionada no es válida.")
        return redirect(
            redirect_con_contexto(
                "cef:docentes_grupo",
                cef_context,
                grupo_id=grupo.pk,
            )
        )

    asignacion = get_object_or_404(
        CefDocenteGrupo.objects.filter(grupo=grupo),
        pk=docente_grupo_id,
    )
    try:
        dar_baja_docente_grupo(asignacion, request.user)
        ok = True
        message = "Profesor dado de baja del grupo correctamente."
    except ValidationError as exc:
        ok = False
        message = "; ".join(exc.messages)

    if _is_ajax(request):
        context = {
            "cef_context": cef_context,
            "grupo": grupo,
            "docentes": _docentes_grupo(grupo),
        }
        return _ajax_docentes_grupo_response(request, context, ok, message)

    if ok:
        messages.success(request, message)
    else:
        messages.error(request, message)
    return redirect(
        redirect_con_contexto(
            "cef:docentes_grupo",
            cef_context,
            grupo_id=grupo.pk,
        )
    )


def _alta_docente(request, grupo, cef_context):
    try:
        docente_grupo_id = int(request.POST.get("docente_grupo_id"))
    except (TypeError, ValueError):
        messages.error(request, "La asignación seleccionada no es válida.")
        return redirect(
            redirect_con_contexto(
                "cef:docentes_grupo",
                cef_context,
                grupo_id=grupo.pk,
            )
        )

    asignacion = get_object_or_404(
        CefDocenteGrupo.objects.filter(grupo=grupo),
        pk=docente_grupo_id,
    )
    try:
        dar_alta_docente_grupo(asignacion, request.user)
        ok = True
        message = "Profesor reasignado al grupo correctamente."
    except ValidationError as exc:
        ok = False
        message = "; ".join(exc.messages)

    if _is_ajax(request):
        context = {
            "cef_context": cef_context,
            "grupo": grupo,
            "docentes": _docentes_grupo(grupo),
        }
        return _ajax_docentes_grupo_response(request, context, ok, message)

    if ok:
        messages.success(request, message)
    else:
        messages.error(request, message)
    return redirect(
        redirect_con_contexto(
            "cef:docentes_grupo",
            cef_context,
            grupo_id=grupo.pk,
        )
    )


@cef_required
def docentes_grupo(request, grupo_id):
    context = contexto_base(request, "grupos", "Profesores del Grupo CEF")
    cef_context = context["cef_context"]

    if not cef_context["puede_operar"]:
        messages.warning(
            request,
            "Selecciona un CUE-Anexo y un ciclo lectivo para administrar profesores.",
        )
        return redirect(redirect_con_contexto("cef:carga_grupo", cef_context))

    grupo = _grupo_seguro(grupo_id, cef_context)
    docente = None
    cuil_buscado = ""
    cuil_error = ""
    docente_form = CefDocenteGrupoForm()
    abrir_modal = request.GET.get("abrir_modal_docente") == "1"
    ajax_ok = False
    ajax_message = ""

    if request.method == "POST" and request.POST.get("accion") == "baja":
        return _baja_docente(request, grupo, cef_context)
    if request.method == "POST" and request.POST.get("accion") == "alta":
        return _alta_docente(request, grupo, cef_context)

    if request.method == "POST":
        busqueda_form = CefBusquedaDocenteForm(request.POST)
        docente_form = CefDocenteGrupoForm(request.POST)
        abrir_modal = True

        if busqueda_form.is_valid():
            cuil_buscado = busqueda_form.cleaned_data["cuil"]
            docente = _buscar_docente(cuil_buscado)
        else:
            cuil_buscado = _solo_digitos(request.POST.get("cuil"))
            cuil_error = _errores_form(busqueda_form)

        if not docente:
            ajax_message = "Primero busca un profesor existente por CUIL."
            if not _is_ajax(request):
                messages.error(request, ajax_message)
        else:
            docente_form.instance.grupo = grupo
            docente_form.instance.docente_cuil = cuil_buscado

            if docente_form.is_valid():
                estado = docente_form.cleaned_data.get("estado")
                rol = docente_form.cleaned_data.get("rol")
                if estado == CefDocenteGrupo.Estado.ACTIVO:
                    try:
                        validar_docente_grupo_activo(grupo, cuil_buscado, rol)
                    except ValidationError as exc:
                        ajax_message = "; ".join(exc.messages)
                if ajax_message:
                    if not _is_ajax(request):
                        messages.error(request, ajax_message)
                else:
                    try:
                        _, _, banco_pendiente = _asegurar_docente_banco(
                            docente,
                            cef_context,
                            request.user,
                        )
                        if banco_pendiente:
                            if not _is_ajax(request):
                                messages.warning(request, MSG_BANCO_DOCENTES_PENDIENTE)
                    except (IntegrityError, ValidationError):
                        if not _is_ajax(request):
                            messages.warning(
                                request,
                                "No se pudo actualizar el banco de profesores CEF, pero se continuará con la asignación al grupo.",
                            )

                    try:
                        with transaction.atomic():
                            asignacion = docente_form.save(commit=False)
                            asignacion.grupo = grupo
                            asignacion.docente_cuil = cuil_buscado
                            asignacion.creado_por = request.user
                            asignacion.actualizado_por = request.user
                            asignacion.save()
                        if _is_ajax(request):
                            ajax_ok = True
                            ajax_message = f"Profesor asignado como {asignacion.get_rol_display().lower()}."
                        else:
                            messages.success(request, "Profesor asociado correctamente.")
                            return redirect(
                                redirect_con_contexto(
                                    "cef:docentes_grupo",
                                    cef_context,
                                    grupo_id=grupo.pk,
                                )
                            )
                    except ValidationError as exc:
                        ajax_message = "; ".join(exc.messages)
                        if not _is_ajax(request):
                            messages.error(request, ajax_message)
                    except IntegrityError:
                        ajax_message = "No se pudo asociar el profesor. Verifica que no exista ya un titular o suplente activo para este grupo."
                        if not _is_ajax(request):
                            messages.error(request, ajax_message)
            else:
                ajax_message = _errores_form(docente_form) or "Revisá los datos de la asignación al grupo."
                if not _is_ajax(request):
                    messages.error(request, ajax_message)
    else:
        busqueda_form = CefBusquedaDocenteForm(
            request.GET if request.GET.get("cuil") else None
        )

        if busqueda_form.is_valid():
            cuil_buscado = busqueda_form.cleaned_data["cuil"]
            docente = _buscar_docente(cuil_buscado)
        elif request.GET.get("cuil"):
            cuil_buscado = _solo_digitos(request.GET.get("cuil"))
            cuil_error = _errores_form(busqueda_form)

    next_url = _url_modal_grupo(grupo, cef_context, cuil_buscado)
    context.update(
        {
            "grupo": grupo,
            "grupo_rotulo": _grupo_rotulo(grupo),
            "grupo_dias_texto": _dias_texto(grupo),
            "docentes": _docentes_grupo(grupo),
            "docentes_activos_count": len(
                [
                    item
                    for item in _docentes_grupo(grupo)
                    if item.estado == CefDocenteGrupo.Estado.ACTIVO
                ]
            ),
            "docentes_activos_duplicados": docentes_grupo_tiene_duplicados_activos(grupo),
            "busqueda_form": busqueda_form,
            "docente_form": docente_form,
            "docente": docente,
            "docente_row": _docente_row(docente),
            "docente_asignacion_activa": (
                _asignacion_docente_activa(grupo, cuil_buscado)
                if docente and len(cuil_buscado) == 11
                else None
            ),
            "cuil_buscado": cuil_buscado,
            "cuil_error": cuil_error,
            "url_carga_profesor": _url_carga_profesor(cuil_buscado, next_url),
            "url_editar_profesor": _url_carga_profesor(cuil_buscado, next_url),
            "modal_docente_abierto": abrir_modal,
            "modal_action_url": _url_modal_grupo(grupo, cef_context),
            "modal_tiene_grupo": True,
            "modal_volver_url": _url_docentes_grupo(grupo, cef_context),
            "modal_feedback": ajax_message,
            "modal_feedback_level": "success" if ajax_ok else "error",
        }
    )
    if request.method == "POST" and _is_ajax(request):
        return _ajax_docentes_grupo_response(request, context, ajax_ok, ajax_message)
    return render(request, "cef/docentes_grupo_cef.html", context)


@cef_required
def editar_docente_grupo(request, grupo_id, docente_grupo_id):
    context = contexto_base(request, "grupos", "Editar profesor del grupo CEF")
    cef_context = context["cef_context"]

    if not cef_context["puede_operar"]:
        messages.warning(
            request,
            "Selecciona un CUE-Anexo y un ciclo lectivo para administrar profesores.",
        )
        return redirect(redirect_con_contexto("cef:carga_grupo", cef_context))

    grupo = _grupo_seguro(grupo_id, cef_context)
    volver_gestionar = (
        request.GET.get("volver") == "gestionar"
        or request.POST.get("volver") == "gestionar"
    )
    volver_url = (
        _url_gestionar_grupo(grupo, cef_context)
        if volver_gestionar
        else _url_docentes_grupo(grupo, cef_context)
    )
    asignacion = get_object_or_404(
        CefDocenteGrupo.objects.filter(grupo=grupo),
        pk=docente_grupo_id,
    )
    docente_cuil = asignacion.docente_cuil

    if request.method == "POST":
        form = CefDocenteGrupoForm(request.POST, instance=asignacion)
        form.instance.grupo = grupo
        form.instance.docente_cuil = docente_cuil

        if form.is_valid():
            try:
                if form.cleaned_data.get("estado") == CefDocenteGrupo.Estado.ACTIVO:
                    validar_docente_grupo_activo(
                        grupo,
                        docente_cuil,
                        form.cleaned_data.get("rol"),
                        excluir_pk=asignacion.pk,
                    )
                try:
                    asignacion = form.save(commit=False)
                    asignacion.grupo = grupo
                    asignacion.docente_cuil = docente_cuil
                    asignacion.actualizado_por = request.user
                    asignacion.save()
                    messages.success(request, "Asignación del profesor actualizada correctamente.")
                    return redirect(volver_url)
                except ValidationError as exc:
                    messages.error(request, "; ".join(exc.messages))
                except IntegrityError:
                    messages.error(
                        request,
                        "No se pudo actualizar la asignación. Verifica que no exista ya un titular, suplente o profesor activo duplicado para este grupo.",
                    )
            except ValidationError as exc:
                messages.error(request, "; ".join(exc.messages))
        else:
            messages.error(
                request,
                _errores_form(form) or "Revisá los datos de la asignación.",
            )
    else:
        form = CefDocenteGrupoForm(instance=asignacion)

    context.update(
        {
            "grupo": grupo,
            "grupo_rotulo": _grupo_rotulo(grupo),
            "grupo_dias_texto": _dias_texto(grupo),
            "asignacion": asignacion,
            "form": form,
            "volver_url": volver_url,
            "volver_gestionar": volver_gestionar,
        }
    )
    return render(request, "cef/docente_grupo_form_cef.html", context)
