# -*- coding: utf-8 -*-

import re
from urllib.parse import urlencode

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

from .forms import CefBusquedaDocenteForm, CefDocenteGrupoForm
from .models import CefDocenteBnh, CefDocenteGrupo, CefGrupo, PADRON_DB_ALIAS
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


def _asignacion_rol_activa(grupo, rol, cuil):
    if not rol:
        return None

    return (
        CefDocenteGrupo.objects.filter(
            grupo=grupo,
            rol=rol,
            estado=CefDocenteGrupo.Estado.ACTIVO,
        )
        .exclude(docente_cuil=cuil)
        .first()
    )


def _docentes_grupo(grupo):
    return (
        CefDocenteGrupo.objects.filter(grupo=grupo)
        .order_by("rol", "estado", "docente_nombre_snapshot", "docente_cuil")
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


def _errores_form(form):
    return " ".join(error for errors in form.errors.values() for error in errors)


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
    asignacion.estado = CefDocenteGrupo.Estado.BAJA
    if not asignacion.fecha_hasta:
        asignacion.fecha_hasta = timezone.localdate()
    asignacion.actualizado_por = request.user
    asignacion.save()
    messages.success(request, "Profesor dado de baja del grupo correctamente.")
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

    if request.method == "POST" and request.POST.get("accion") == "baja":
        return _baja_docente(request, grupo, cef_context)

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
            messages.error(request, "Primero busca un profesor existente por CUIL.")
        else:
            docente_form.instance.grupo = grupo
            docente_form.instance.docente_cuil = cuil_buscado

            if docente_form.is_valid():
                estado = docente_form.cleaned_data.get("estado")
                rol = docente_form.cleaned_data.get("rol")
                rol_ocupado = (
                    _asignacion_rol_activa(grupo, rol, cuil_buscado)
                    if estado == CefDocenteGrupo.Estado.ACTIVO
                    else None
                )
                if (
                    estado == CefDocenteGrupo.Estado.ACTIVO
                    and CefDocenteGrupo.objects.filter(
                        grupo=grupo,
                        docente_cuil=cuil_buscado,
                        estado=CefDocenteGrupo.Estado.ACTIVO,
                    ).exists()
                ):
                    messages.error(
                        request,
                        "Ese profesor ya tiene una asignacion activa en este grupo.",
                    )
                elif rol_ocupado:
                    messages.error(
                        request,
                        f"El grupo ya tiene un {rol_ocupado.get_rol_display()} activo.",
                    )
                else:
                    try:
                        _, _, banco_pendiente = _asegurar_docente_banco(
                            docente,
                            cef_context,
                            request.user,
                        )
                        if banco_pendiente:
                            messages.warning(request, MSG_BANCO_DOCENTES_PENDIENTE)
                    except (IntegrityError, ValidationError):
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
                        messages.success(request, "Profesor asociado correctamente.")
                        return redirect(
                            redirect_con_contexto(
                                "cef:docentes_grupo",
                                cef_context,
                                grupo_id=grupo.pk,
                            )
                        )
                    except (IntegrityError, ValidationError):
                        messages.error(
                            request,
                            "No se pudo asociar el profesor. Verifica que no exista ya un titular o suplente activo para este grupo.",
                        )
            else:
                messages.error(request, "Revisá los datos de la asignación al grupo.")
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
            "busqueda_form": busqueda_form,
            "docente_form": docente_form,
            "docente": docente,
            "docente_row": _docente_row(docente),
            "cuil_buscado": cuil_buscado,
            "cuil_error": cuil_error,
            "url_carga_profesor": _url_carga_profesor(cuil_buscado, next_url),
            "url_editar_profesor": _url_carga_profesor(cuil_buscado, next_url),
            "modal_docente_abierto": abrir_modal,
            "modal_action_url": _url_modal_grupo(grupo, cef_context),
            "modal_tiene_grupo": True,
            "modal_volver_url": _url_docentes_grupo(grupo, cef_context),
        }
    )
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
            rol_ocupado = (
                _asignacion_rol_activa(
                    grupo,
                    form.cleaned_data.get("rol"),
                    docente_cuil,
                )
                if form.cleaned_data.get("estado") == CefDocenteGrupo.Estado.ACTIVO
                else None
            )
            if rol_ocupado:
                messages.error(
                    request,
                    f"El grupo ya tiene un {rol_ocupado.get_rol_display()} activo.",
                )
            else:
                try:
                    asignacion = form.save(commit=False)
                    asignacion.grupo = grupo
                    asignacion.docente_cuil = docente_cuil
                    asignacion.actualizado_por = request.user
                    asignacion.save()
                    messages.success(request, "Asignación del profesor actualizada correctamente.")
                    return redirect(_url_docentes_grupo(grupo, cef_context))
                except (IntegrityError, ValidationError):
                    messages.error(
                        request,
                        "No se pudo actualizar la asignación. Verifica que no exista ya un titular, suplente o profesor activo duplicado para este grupo.",
                    )
        else:
            messages.error(request, "Revisá los datos de la asignación.")
    else:
        form = CefDocenteGrupoForm(instance=asignacion)

    context.update(
        {
            "grupo": grupo,
            "grupo_rotulo": _grupo_rotulo(grupo),
            "grupo_dias_texto": _dias_texto(grupo),
            "asignacion": asignacion,
            "form": form,
            "volver_url": _url_docentes_grupo(grupo, cef_context),
        }
    )
    return render(request, "cef/docente_grupo_form_cef.html", context)
