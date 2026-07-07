# -*- coding: utf-8 -*-

import re
from urllib.parse import urlencode

from django.apps import apps
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import NoReverseMatch, reverse

from .forms import CefBusquedaAlumnoForm, CefInscripcionForm
from .models import CefGrupo, CefInscripcion
from .permisos import cef_required
from .views_alumnos import MSG_BANCO_ALUMNOS_PENDIENTE, _asegurar_alumno_banco
from .views_contexto import contexto_base, redirect_con_contexto


ESTADOS_INSCRIPCION_ABIERTA = [
    CefInscripcion.Estado.ACTIVO,
]


def _solo_digitos(valor):
    return re.sub(r"\D", "", str(valor or ""))


def _alumno_model():
    return apps.get_model("bnhalumnos", "Alumno")


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


def _inscripciones_grupo(grupo):
    return (
        CefInscripcion.objects.filter(grupo=grupo)
        .select_related("alumno", "alumno__sexo")
        .order_by("alumno__apellidos", "alumno__nombres")
    )


def _buscar_alumno(cuil):
    return _alumno_model().objects.filter(cuil=cuil).first()


def _texto(valor):
    if valor is None:
        return ""
    return str(valor)


def _alumno_row(alumno):
    if not alumno:
        return None
    return {
        "apellidos": getattr(alumno, "apellidos", "") or "",
        "nombres": getattr(alumno, "nombres", "") or "",
        "tipo_doc": _texto(getattr(alumno, "tipo_doc", "")),
        "nro_doc": getattr(alumno, "nro_doc", "") or "",
        "cuil": getattr(alumno, "cuil", "") or "",
        "fecha_nac": getattr(alumno, "fecha_nacimiento", None),
        "sexo": _texto(getattr(alumno, "sexo", "")),
        "lugar_nac": (
            _texto(getattr(alumno, "loc_nacimiento", ""))
            or getattr(alumno, "lugar_nacimiento", "")
            or ""
        ),
    }


def _url_carga_alumno(cuil, next_url, return_label="Volver al curso"):
    try:
        base = reverse("bnhalumnos:carga_alumno")
    except NoReverseMatch:
        return ""

    params = {}
    if cuil:
        params["cuil"] = cuil
    if next_url:
        params["next"] = next_url
    if return_label:
        params["return_label"] = return_label
    return f"{base}?{urlencode(params)}" if params else base


def _url_modal_grupo(grupo, cef_context, cuil=""):
    params = {}
    if cef_context.get("cueanexo"):
        params["cueanexo"] = cef_context["cueanexo"]
    if cef_context.get("ciclo"):
        params["ciclo"] = cef_context["ciclo"].pk
    params["abrir_modal_alumno"] = "1"
    if cuil:
        params["cuil"] = cuil
    return f"{reverse('cef:inscripcion_grupo', kwargs={'grupo_id': grupo.pk})}?{urlencode(params)}"


def _url_inscripcion_grupo(grupo, cef_context):
    params = {}
    if cef_context.get("cueanexo"):
        params["cueanexo"] = cef_context["cueanexo"]
    if cef_context.get("ciclo"):
        params["ciclo"] = cef_context["ciclo"].pk
    querystring = urlencode(params)
    url = reverse("cef:inscripcion_grupo", kwargs={"grupo_id": grupo.pk})
    return f"{url}?{querystring}" if querystring else url


def _errores_form(form):
    return " ".join(error for errors in form.errors.values() for error in errors)


@cef_required
def inscripcion_grupo(request, grupo_id):
    context = contexto_base(request, "grupos", "Inscripción de alumnos CEF")
    cef_context = context["cef_context"]

    if not cef_context["puede_operar"]:
        messages.warning(
            request,
            "Seleccioná un CUE-Anexo y un ciclo lectivo para administrar inscripciones.",
        )
        return redirect(redirect_con_contexto("cef:carga_grupo", cef_context))

    grupo = _grupo_seguro(grupo_id, cef_context)
    alumno = None
    inscripcion_abierta = None
    cuil_buscado = ""
    cuil_error = ""
    abrir_modal = request.GET.get("abrir_modal_alumno") == "1"

    if request.method == "POST":
        busqueda_form = CefBusquedaAlumnoForm(request.POST)
        abrir_modal = True

        if busqueda_form.is_valid():
            cuil_buscado = busqueda_form.cleaned_data["cuil"]
            alumno = _buscar_alumno(cuil_buscado)
        else:
            cuil_buscado = _solo_digitos(request.POST.get("cuil"))
            cuil_error = _errores_form(busqueda_form)

        if not alumno:
            messages.error(request, "Primero buscá un alumno existente por CUIL.")
        else:
            inscripcion_abierta = CefInscripcion.objects.filter(
                grupo=grupo,
                alumno=alumno,
                estado__in=ESTADOS_INSCRIPCION_ABIERTA,
            ).first()

            if inscripcion_abierta:
                pass
            else:
                try:
                    _, _, banco_pendiente = _asegurar_alumno_banco(
                        alumno,
                        cef_context,
                        request.user,
                    )
                    if banco_pendiente:
                        messages.warning(request, MSG_BANCO_ALUMNOS_PENDIENTE)
                except (IntegrityError, ValidationError):
                    messages.warning(
                        request,
                        "No se pudo actualizar el banco de alumnos CEF, pero se continuará con la inscripción al grupo.",
                    )

                try:
                    with transaction.atomic():
                        CefInscripcion.objects.create(
                            grupo=grupo,
                            alumno=alumno,
                            estado=CefInscripcion.Estado.ACTIVO,
                            creado_por=request.user,
                            actualizado_por=request.user,
                        )
                    messages.success(request, "Alumno inscripto correctamente.")
                    return redirect(
                        redirect_con_contexto(
                            "cef:inscripcion_grupo",
                            cef_context,
                            grupo_id=grupo.pk,
                        )
                    )
                except (IntegrityError, ValidationError):
                    messages.error(
                        request,
                        "No se pudo crear la inscripción. Verificá que no exista una inscripción activa.",
                    )
    else:
        busqueda_form = CefBusquedaAlumnoForm(
            request.GET if request.GET.get("cuil") else None
        )

        if busqueda_form.is_valid():
            cuil_buscado = busqueda_form.cleaned_data["cuil"]
            alumno = _buscar_alumno(cuil_buscado)
            if alumno:
                inscripcion_abierta = CefInscripcion.objects.filter(
                    grupo=grupo,
                    alumno=alumno,
                    estado__in=ESTADOS_INSCRIPCION_ABIERTA,
                ).first()
        elif request.GET.get("cuil"):
            cuil_buscado = _solo_digitos(request.GET.get("cuil"))
            cuil_error = _errores_form(busqueda_form)

    next_url = _url_modal_grupo(grupo, cef_context, cuil_buscado)
    context.update(
        {
            "grupo": grupo,
            "grupo_dias_texto": _dias_texto(grupo),
            "inscripciones": _inscripciones_grupo(grupo),
            "busqueda_form": busqueda_form,
            "alumno": alumno,
            "alumno_row": _alumno_row(alumno),
            "cuil_buscado": cuil_buscado,
            "cuil_error": cuil_error,
            "inscripcion_abierta": inscripcion_abierta,
            "url_carga_alumno": _url_carga_alumno(cuil_buscado, next_url),
            "url_editar_alumno": _url_carga_alumno(cuil_buscado, next_url),
            "modal_alumno_abierto": abrir_modal,
            "modal_action_url": _url_modal_grupo(grupo, cef_context),
            "modal_tiene_grupo": True,
            "modal_volver_url": _url_inscripcion_grupo(grupo, cef_context),
        }
    )
    return render(request, "cef/inscripcion_grupo_cef.html", context)


@cef_required
def editar_inscripcion_grupo(request, grupo_id, inscripcion_id):
    context = contexto_base(request, "grupos", "Editar inscripción CEF")
    cef_context = context["cef_context"]

    if not cef_context["puede_operar"]:
        messages.warning(
            request,
            "Seleccioná un CUE-Anexo y un ciclo lectivo para administrar inscripciones.",
        )
        return redirect(redirect_con_contexto("cef:carga_grupo", cef_context))

    grupo = _grupo_seguro(grupo_id, cef_context)
    inscripcion = get_object_or_404(
        CefInscripcion.objects.filter(
            grupo=grupo,
            grupo__cueanexo=cef_context["cueanexo"],
            grupo__ciclo=cef_context["ciclo"],
        ).select_related("alumno", "alumno__sexo"),
        pk=inscripcion_id,
    )

    if request.method == "POST":
        form = CefInscripcionForm(request.POST, instance=inscripcion)
        if form.is_valid():
            inscripcion = form.save(commit=False)
            inscripcion.actualizado_por = request.user
            inscripcion.save()
            messages.success(request, "Inscripción actualizada correctamente.")
            return redirect(_url_inscripcion_grupo(grupo, cef_context))

        messages.error(request, "Revisá los datos de la inscripción.")
    else:
        form = CefInscripcionForm(instance=inscripcion)

    context.update(
        {
            "grupo": grupo,
            "grupo_dias_texto": _dias_texto(grupo),
            "inscripcion": inscripcion,
            "form": form,
            "volver_url": _url_inscripcion_grupo(grupo, cef_context),
        }
    )
    return render(request, "cef/inscripcion_grupo_form_cef.html", context)
