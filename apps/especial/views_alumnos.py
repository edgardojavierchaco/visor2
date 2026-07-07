# apps/especial/views_alumno.py
# -*- coding: utf-8 -*-

import re
from urllib.parse import urlencode

from django.apps import apps
from django.urls import NoReverseMatch, reverse
from django.shortcuts import render

from .forms import EspecialBusquedaAlumnoForm
from .permisos import especial_required
from .views_contexto import contexto_base


def _solo_digitos(valor):
    return re.sub(r"\D", "", str(valor or ""))


def _alumno_model():
    return apps.get_model("bnhalumnos", "Alumno")


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


def _url_carga_alumno(cuil, next_url, return_label="Volver a Alumnos"):
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


def _url_modal_alumnos(especial_context, cuil=""):
    params = {}
    if especial_context.get("cueanexo"):
        params["cueanexo"] = especial_context["cueanexo"]
    if especial_context.get("ciclo"):
        params["ciclo"] = especial_context["ciclo"].pk
    params["abrir_modal_alumno"] = "1"
    if cuil:
        params["cuil"] = cuil
    return f"{reverse('especial:alumnos')}?{urlencode(params)}"


def _url_alumnos(especial_context):
    params = {}
    if especial_context.get("cueanexo"):
        params["cueanexo"] = especial_context["cueanexo"]
    if especial_context.get("ciclo"):
        params["ciclo"] = especial_context["ciclo"].pk
    querystring = urlencode(params)
    url = reverse("especial:alumnos")
    return f"{url}?{querystring}" if querystring else url


def _errores_form(form):
    return " ".join(error for errors in form.errors.values() for error in errors)


@especial_required
def alumnos(request):
    """Vista de búsqueda y gestión de alumnos de Educación Especial."""
    context = contexto_base(request, "alumnos", "Alumnos Educación Especial")
    especial_context = context["especial_context"]
    alumno = None
    cuil_buscado = ""
    cuil_error = ""
    abrir_modal = request.GET.get("abrir_modal_alumno") == "1"
    busqueda_form = EspecialBusquedaAlumnoForm(
        request.GET if request.GET.get("cuil") else None
    )

    if busqueda_form.is_valid():
        cuil_buscado = busqueda_form.cleaned_data["cuil"]
        alumno = _buscar_alumno(cuil_buscado)
    elif request.GET.get("cuil"):
        cuil_buscado = _solo_digitos(request.GET.get("cuil"))
        cuil_error = _errores_form(busqueda_form)

    next_url = _url_modal_alumnos(especial_context, cuil_buscado)
    context.update(
        {
            "busqueda_form": busqueda_form,
            "alumno": alumno,
            "alumno_row": _alumno_row(alumno),
            "cuil_buscado": cuil_buscado,
            "cuil_error": cuil_error,
            "url_carga_alumno": _url_carga_alumno(cuil_buscado, next_url),
            "url_editar_alumno": _url_carga_alumno(cuil_buscado, next_url),
            "modal_alumno_abierto": abrir_modal,
            "modal_action_url": _url_modal_alumnos(especial_context),
            "modal_tiene_seccion": False,
            "modal_volver_url": _url_alumnos(especial_context),
        }
    )
    return render(request, "especial/alumnos_especial.html", context)