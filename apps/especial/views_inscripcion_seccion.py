# apps/especial/views_inscripcion_seccion.py
# -*- coding: utf-8 -*-

import re
from urllib.parse import urlencode

from django.apps import apps
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import NoReverseMatch, reverse

from .forms import EspecialBusquedaAlumnoForm
from .models import SeccionEspecial, AlumnoSeccion
from .permisos import especial_required
from .views_contexto import contexto_base, redirect_con_contexto


ESTADOS_INSCRIPCION_ABIERTA = [
    AlumnoSeccion.Estado.ACTIVO,
    AlumnoSeccion.Estado.INACTIVO,
]


def _solo_digitos(valor):
    return re.sub(r"\D", "", str(valor or ""))


def _alumno_model():
    return apps.get_model("bnhalumnos", "Alumno")


def _seccion_segura(seccion_id, especial_context):
    """Obtiene una sección validando permisos."""
    return get_object_or_404(
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
        ),
        pk=seccion_id,
    )


def _inscripciones_seccion(seccion):
    """QuerySet de inscripciones de una sección."""
    return (
        AlumnoSeccion.objects.filter(seccion=seccion)
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


def _url_carga_alumno(cuil, next_url, return_label="Volver a la sección"):
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


def _url_modal_seccion(seccion, especial_context, cuil=""):
    params = {}
    if especial_context.get("cueanexo"):
        params["cueanexo"] = especial_context["cueanexo"]
    if especial_context.get("ciclo"):
        params["ciclo"] = especial_context["ciclo"].pk
    params["abrir_modal_alumno"] = "1"
    if cuil:
        params["cuil"] = cuil
    return f"{reverse('especial:inscripcion_seccion', kwargs={'seccion_id': seccion.pk})}?{urlencode(params)}"


def _url_inscripcion_seccion(seccion, especial_context):
    params = {}
    if especial_context.get("cueanexo"):
        params["cueanexo"] = especial_context["cueanexo"]
    if especial_context.get("ciclo"):
        params["ciclo"] = especial_context["ciclo"].pk
    querystring = urlencode(params)
    url = reverse("especial:inscripcion_seccion", kwargs={"seccion_id": seccion.pk})
    return f"{url}?{querystring}" if querystring else url


def _errores_form(form):
    return " ".join(error for errors in form.errors.values() for error in errors)


@especial_required
def inscripcion_seccion(request, seccion_id):
    """Vista de inscripción de alumnos a una sección."""
    context = contexto_base(request, "secciones", "Inscripción de alumnos Educación Especial")
    especial_context = context["especial_context"]

    if not especial_context["puede_operar"]:
        messages.warning(
            request,
            "Seleccioná un CUE-Anexo y un ciclo lectivo para administrar inscripciones.",
        )
        return redirect(redirect_con_contexto("especial:carga_seccion", especial_context))

    seccion = _seccion_segura(seccion_id, especial_context)
    alumno = None
    inscripcion_abierta = None
    cuil_buscado = ""
    cuil_error = ""
    abrir_modal = request.GET.get("abrir_modal_alumno") == "1"

    if request.method == "POST":
        busqueda_form = EspecialBusquedaAlumnoForm(request.POST)
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
            inscripcion_abierta = AlumnoSeccion.objects.filter(
                seccion=seccion,
                alumno=alumno,
                estado__in=ESTADOS_INSCRIPCION_ABIERTA,
            ).first()

            if inscripcion_abierta:
                pass
            else:
                try:
                    with transaction.atomic():
                        AlumnoSeccion.objects.create(
                            seccion=seccion,
                            alumno=alumno,
                            estado=AlumnoSeccion.Estado.ACTIVO,
                            creado_por=request.user,
                            actualizado_por=request.user,
                        )
                    messages.success(request, "Alumno inscripto correctamente.")
                    return redirect(
                        redirect_con_contexto(
                            "especial:inscripcion_seccion",
                            especial_context,
                            seccion_id=seccion.pk,
                        )
                    )
                except (IntegrityError, ValidationError):
                    messages.error(
                        request,
                        "No se pudo crear la inscripción. Verificá que no exista una inscripción activa.",
                    )
    else:
        busqueda_form = EspecialBusquedaAlumnoForm(
            request.GET if request.GET.get("cuil") else None
        )

        if busqueda_form.is_valid():
            cuil_buscado = busqueda_form.cleaned_data["cuil"]
            alumno = _buscar_alumno(cuil_buscado)
            if alumno:
                inscripcion_abierta = AlumnoSeccion.objects.filter(
                    seccion=seccion,
                    alumno=alumno,
                    estado__in=ESTADOS_INSCRIPCION_ABIERTA,
                ).first()
        elif request.GET.get("cuil"):
            cuil_buscado = _solo_digitos(request.GET.get("cuil"))
            cuil_error = _errores_form(busqueda_form)

    next_url = _url_modal_seccion(seccion, especial_context, cuil_buscado)
    context.update(
        {
            "seccion": seccion,
            "inscripciones": _inscripciones_seccion(seccion),
            "busqueda_form": busqueda_form,
            "alumno": alumno,
            "alumno_row": _alumno_row(alumno),
            "cuil_buscado": cuil_buscado,
            "cuil_error": cuil_error,
            "inscripcion_abierta": inscripcion_abierta,
            "url_carga_alumno": _url_carga_alumno(cuil_buscado, next_url),
            "url_editar_alumno": _url_carga_alumno(cuil_buscado, next_url),
            "modal_alumno_abierto": abrir_modal,
            "modal_action_url": _url_modal_seccion(seccion, especial_context),
            "modal_tiene_seccion": True,
            "modal_volver_url": _url_inscripcion_seccion(seccion, especial_context),
        }
    )
    return render(request, "especial/inscripcion_seccion_especial.html", context)