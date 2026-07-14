# -*- coding: utf-8 -*-

import re
from urllib.parse import urlencode

from django.apps import apps
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.utils import OperationalError, ProgrammingError
from django.urls import NoReverseMatch, reverse
from django.shortcuts import redirect, render

from .forms import CefBusquedaAlumnoForm
from .models import CefAlumnoCef, CefGrupo, CefInscripcion
from .permisos import cef_required
from .views_contexto import contexto_base


MSG_BANCO_ALUMNOS_PENDIENTE = (
    "El banco de alumnos CEF está pendiente de creación en base de datos."
)


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


def _url_modal_alumnos(cef_context, cuil=""):
    params = {}
    if cef_context.get("cueanexo"):
        params["cueanexo"] = cef_context["cueanexo"]
    if cef_context.get("ciclo"):
        params["ciclo"] = cef_context["ciclo"].pk
    params["abrir_modal_alumno"] = "1"
    if cuil:
        params["cuil"] = cuil
    return f"{reverse('cef:alumnos')}?{urlencode(params)}"


def _url_alumnos(cef_context):
    params = {}
    if cef_context.get("cueanexo"):
        params["cueanexo"] = cef_context["cueanexo"]
    if cef_context.get("ciclo"):
        params["ciclo"] = cef_context["ciclo"].pk
    querystring = urlencode(params)
    url = reverse("cef:alumnos")
    return f"{url}?{querystring}" if querystring else url


def _errores_form(form):
    return " ".join(error for errors in form.errors.values() for error in errors)


def _pk_post(request, campo):
    try:
        return int(request.POST.get(campo) or "")
    except (TypeError, ValueError):
        return None


def _inscribir_alumno_grupo_desde_banco(request, cef_context):
    if not cef_context["puede_operar"]:
        messages.error(
            request,
            "Seleccioná un CUE-Anexo y un ciclo lectivo para inscribir alumnos.",
        )
        return

    alumno_banco_id = _pk_post(request, "alumno_banco_id")
    grupo_id = _pk_post(request, "grupo_id")

    if not alumno_banco_id or not grupo_id:
        messages.error(request, "No se pudo identificar el alumno o el grupo.")
        return

    alumno_banco = (
        CefAlumnoCef.objects.filter(
            pk=alumno_banco_id,
            cueanexo=cef_context["cueanexo"],
            ciclo=cef_context["ciclo"],
            estado=CefAlumnoCef.Estado.ACTIVO,
        )
        .select_related("alumno")
        .first()
    )
    if not alumno_banco:
        messages.error(request, "El alumno no está activo en el banco de este CEF y ciclo.")
        return

    grupo = CefGrupo.objects.filter(
        pk=grupo_id,
        cueanexo=cef_context["cueanexo"],
        ciclo=cef_context["ciclo"],
    ).first()
    if not grupo:
        messages.error(request, "El grupo no corresponde al CEF y ciclo seleccionados.")
        return

    inscripcion_activa = CefInscripcion.objects.filter(
        grupo=grupo,
        alumno=alumno_banco.alumno,
        estado=CefInscripcion.Estado.ACTIVO,
    ).exists()
    if inscripcion_activa:
        messages.info(request, "El alumno ya se encuentra inscripto en ese grupo.")
        return

    try:
        with transaction.atomic():
            CefInscripcion.objects.create(
                grupo=grupo,
                alumno=alumno_banco.alumno,
                estado=CefInscripcion.Estado.ACTIVO,
                creado_por=request.user,
                actualizado_por=request.user,
            )
        messages.success(request, "Alumno inscripto correctamente al grupo.")
    except (IntegrityError, ValidationError):
        messages.error(
            request,
            "No se pudo crear la inscripción. Verificá que no exista una inscripción activa.",
        )


def _alumnos_banco(cef_context):
    if not cef_context["puede_operar"]:
        return CefAlumnoCef.objects.none()

    return (
        CefAlumnoCef.objects.filter(
            cueanexo=cef_context["cueanexo"],
            ciclo=cef_context["ciclo"],
        )
        .select_related("alumno")
        .order_by("alumno_nombre_snapshot", "alumno_cuil_snapshot")
    )


def _inscripciones_por_alumno(cef_context, alumnos_banco):
    alumnos_ids = [item.alumno_id for item in alumnos_banco]
    if not alumnos_ids:
        return {}

    inscripciones = (
        CefInscripcion.objects.filter(
            grupo__cueanexo=cef_context["cueanexo"],
            grupo__ciclo=cef_context["ciclo"],
            alumno_id__in=alumnos_ids,
        )
        .select_related("grupo", "grupo__actividad")
        .order_by("grupo__actividad__nombre", "grupo__numero")
    )

    por_alumno = {}
    for inscripcion in inscripciones:
        por_alumno.setdefault(inscripcion.alumno_id, []).append(inscripcion)
    return por_alumno


def _grupos_disponibles(cef_context):
    if not cef_context["puede_operar"]:
        return CefGrupo.objects.none()

    return (
        CefGrupo.objects.filter(
            cueanexo=cef_context["cueanexo"],
            ciclo=cef_context["ciclo"],
        )
        .select_related("actividad", "turno")
        .order_by("actividad__nombre", "numero", "nombre")
    )


def _alumno_en_banco_activo(alumno, cef_context):
    if not alumno or not cef_context["puede_operar"]:
        return False

    return CefAlumnoCef.objects.filter(
        cueanexo=cef_context["cueanexo"],
        ciclo=cef_context["ciclo"],
        alumno=alumno,
        estado=CefAlumnoCef.Estado.ACTIVO,
    ).exists()


def _asegurar_alumno_banco(alumno, cef_context, user):
    if not alumno or not cef_context["puede_operar"]:
        return None, False, False

    try:
        existente = CefAlumnoCef.objects.filter(
            cueanexo=cef_context["cueanexo"],
            ciclo=cef_context["ciclo"],
            alumno=alumno,
            estado=CefAlumnoCef.Estado.ACTIVO,
        ).first()
        if existente:
            return existente, False, False

        with transaction.atomic():
            banco = CefAlumnoCef.objects.create(
                cueanexo=cef_context["cueanexo"],
                ciclo=cef_context["ciclo"],
                alumno=alumno,
                estado=CefAlumnoCef.Estado.ACTIVO,
                creado_por=user,
                actualizado_por=user,
            )
        return banco, True, False
    except (OperationalError, ProgrammingError):
        return None, False, True


@cef_required
def alumnos(request):
    context = contexto_base(request, "alumnos", "Alumnos CEF")
    cef_context = context["cef_context"]
    alumno = None
    cuil_buscado = ""
    cuil_error = ""
    alumno_en_banco = False
    abrir_modal = request.GET.get("abrir_modal_alumno") == "1"

    if request.method == "POST":
        if request.POST.get("accion") == "inscribir_grupo":
            _inscribir_alumno_grupo_desde_banco(request, cef_context)
            return redirect(_url_alumnos(cef_context))

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
        elif not cef_context["puede_operar"]:
            messages.error(
                request,
                "Seleccioná un CUE-Anexo y un ciclo lectivo para agregar alumnos al banco.",
            )
        else:
            try:
                banco, creado, tabla_pendiente = _asegurar_alumno_banco(
                    alumno,
                    cef_context,
                    request.user,
                )
                alumno_en_banco = bool(banco)

                if tabla_pendiente:
                    messages.error(request, MSG_BANCO_ALUMNOS_PENDIENTE)
                elif creado:
                    messages.success(request, "Alumno agregado al banco del CEF.")
                    return redirect(_url_alumnos(cef_context))
                else:
                    messages.info(
                        request,
                        "Ese alumno ya está activo en el banco de este CEF y ciclo.",
                    )
            except (IntegrityError, ValidationError):
                messages.error(
                    request,
                    "No se pudo agregar el alumno al banco. Verificá que no exista ya activo para este CEF y ciclo.",
                )
    else:
        busqueda_form = CefBusquedaAlumnoForm(
            request.GET if request.GET.get("cuil") else None
        )

        if busqueda_form.is_valid():
            cuil_buscado = busqueda_form.cleaned_data["cuil"]
            alumno = _buscar_alumno(cuil_buscado)
        elif request.GET.get("cuil"):
            cuil_buscado = _solo_digitos(request.GET.get("cuil"))
            cuil_error = _errores_form(busqueda_form)

    next_url = _url_modal_alumnos(cef_context, cuil_buscado)
    url_alumnos = _url_alumnos(cef_context)
    alumnos_banco_tabla_pendiente = False

    try:
        alumnos_banco = list(_alumnos_banco(cef_context))
        if alumno and not alumno_en_banco:
            alumno_en_banco = _alumno_en_banco_activo(alumno, cef_context)
    except (OperationalError, ProgrammingError):
        alumnos_banco = []
        alumnos_banco_tabla_pendiente = True

    try:
        inscripciones_por_alumno = _inscripciones_por_alumno(
            cef_context,
            alumnos_banco,
        )
    except (OperationalError, ProgrammingError):
        inscripciones_por_alumno = {}

    grupos_disponibles = list(_grupos_disponibles(cef_context))

    for item in alumnos_banco:
        item.inscripciones_grupo = inscripciones_por_alumno.get(item.alumno_id, [])
        inscripciones_activas = [
            inscripcion
            for inscripcion in item.inscripciones_grupo
            if inscripcion.estado == CefInscripcion.Estado.ACTIVO
        ]
        grupos_activos_ids = {inscripcion.grupo_id for inscripcion in inscripciones_activas}
        item.grupos_asignables = [
            grupo for grupo in grupos_disponibles if grupo.pk not in grupos_activos_ids
        ]
        item.grupos_bloqueados = inscripciones_activas
        item.url_editar_alumno = _url_carga_alumno(
            item.alumno_cuil_snapshot or getattr(item.alumno, "cuil", ""),
            url_alumnos,
        )

    context.update(
        {
            "busqueda_form": busqueda_form,
            "alumno": alumno,
            "alumno_row": _alumno_row(alumno),
            "alumnos": alumnos_banco,
            "grupos_disponibles": grupos_disponibles,
            "alumnos_banco_tabla_pendiente": alumnos_banco_tabla_pendiente,
            "alumno_en_banco": alumno_en_banco,
            "cuil_buscado": cuil_buscado,
            "cuil_error": cuil_error,
            "url_carga_alumno": _url_carga_alumno(cuil_buscado, next_url),
            "url_editar_alumno": _url_carga_alumno(cuil_buscado, next_url),
            "modal_alumno_abierto": abrir_modal,
            "modal_action_url": _url_modal_alumnos(cef_context),
            "modal_tiene_grupo": False,
            "modal_puede_agregar_banco": cef_context["puede_operar"],
            "modal_volver_url": url_alumnos,
        }
    )
    return render(request, "cef/alumnos_cef.html", context)
