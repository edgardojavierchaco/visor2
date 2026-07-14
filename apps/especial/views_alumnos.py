# apps/especial/views_alumnos.py
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
from .forms import EspecialBusquedaAlumnoForm
from .models import EspecialAlumnoBanco, SeccionEspecial, AlumnoSeccion
from .permisos import especial_required
from .views_contexto import contexto_base

MSG_BANCO_ALUMNOS_PENDIENTE = (
    "El banco de alumnos de Educación Especial está pendiente de creación en base de datos."
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

def _alumnos_banco(especial_context):
    if not especial_context["puede_operar"]:
        return EspecialAlumnoBanco.objects.none()
    return (
        EspecialAlumnoBanco.objects.filter(
            cueanexo=especial_context["cueanexo"],
            ciclo=especial_context["ciclo"],
        )
        .select_related("alumno")
        .order_by("alumno_nombre_snapshot", "alumno_cuil_snapshot")
    )

def _inscripciones_por_alumno(especial_context, alumnos_banco):
    alumnos_ids = [item.alumno_id for item in alumnos_banco]
    if not alumnos_ids:
        return {}
    inscripciones = (
        AlumnoSeccion.objects.filter(
            seccion__cueanexo=especial_context["cueanexo"],
            seccion__ciclo=especial_context["ciclo"],
            alumno_id__in=alumnos_ids,
        )
        .select_related("seccion", "seccion__cd_tipo_seccion")
        .order_by("seccion__nombre_seccion")
    )
    por_alumno = {}
    for inscripcion in inscripciones:
        por_alumno.setdefault(inscripcion.alumno_id, []).append(inscripcion)
    return por_alumno

def _secciones_disponibles(especial_context):
    if not especial_context["puede_operar"]:
        return SeccionEspecial.objects.none()
    return (
        SeccionEspecial.objects.filter(
            cueanexo=especial_context["cueanexo"],
            ciclo=especial_context["ciclo"],
            estado=SeccionEspecial.Estado.ACTIVO,
        )
        .select_related("cd_tipo_seccion", "turno")
        .order_by("nombre_seccion")
    )

def _alumno_en_banco_activo(alumno, especial_context):
    if not alumno or not especial_context["puede_operar"]:
        return False
    return EspecialAlumnoBanco.objects.filter(
        cueanexo=especial_context["cueanexo"],
        ciclo=especial_context["ciclo"],
        alumno=alumno,
        estado=EspecialAlumnoBanco.Estado.ACTIVO,
    ).exists()

def _asegurar_alumno_banco(alumno, especial_context, user):
    if not alumno or not especial_context["puede_operar"]:
        return None, False, False
    try:
        existente = EspecialAlumnoBanco.objects.filter(
            cueanexo=especial_context["cueanexo"],
            ciclo=especial_context["ciclo"],
            alumno=alumno,
            estado=EspecialAlumnoBanco.Estado.ACTIVO,
        ).first()
        if existente:
            return existente, False, False
        with transaction.atomic():
            banco = EspecialAlumnoBanco.objects.create(
                cueanexo=especial_context["cueanexo"],
                ciclo=especial_context["ciclo"],
                alumno=alumno,
                estado=EspecialAlumnoBanco.Estado.ACTIVO,
                creado_por=user,
                actualizado_por=user,
            )
            return banco, True, False
    except (OperationalError, ProgrammingError):
        return None, False, True

@especial_required
def alumnos(request):
    context = contexto_base(request, "alumnos", "Alumnos Educación Especial")
    especial_context = context["especial_context"]
    
    alumno = None
    cuil_buscado = ""
    cuil_error = ""
    alumno_en_banco = False
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
        elif not especial_context["puede_operar"]:
            messages.error(
                request,
                "Seleccioná un CUE-Anexo y un ciclo lectivo para agregar alumnos al banco.",
            )
        else:
            try:
                banco, creado, tabla_pendiente = _asegurar_alumno_banco(
                    alumno,
                    especial_context,
                    request.user,
                )
                alumno_en_banco = bool(banco)
                if tabla_pendiente:
                    messages.error(request, MSG_BANCO_ALUMNOS_PENDIENTE)
                elif creado:
                    messages.success(request, "Alumno agregado al banco de Educación Especial.")
                    return redirect(_url_alumnos(especial_context))
                else:
                    messages.info(
                        request,
                        "Ese alumno ya está activo en el banco de este establecimiento y ciclo.",
                    )
            except (IntegrityError, ValidationError):
                messages.error(
                    request,
                    "No se pudo agregar el alumno al banco. Verificá que no exista ya activo.",
                )
    else:
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
    url_alumnos = _url_alumnos(especial_context)
    
    alumnos_banco_tabla_pendiente = False
    try:
        alumnos_banco = list(_alumnos_banco(especial_context))
        if alumno and not alumno_en_banco:
            alumno_en_banco = _alumno_en_banco_activo(alumno, especial_context)
    except (OperationalError, ProgrammingError):
        alumnos_banco = []
        alumnos_banco_tabla_pendiente = True

    try:
        inscripciones_por_alumno = _inscripciones_por_alumno(
            especial_context,
            alumnos_banco,
        )
    except (OperationalError, ProgrammingError):
        inscripciones_por_alumno = {}

    secciones_disponibles = list(_secciones_disponibles(especial_context))
    
    # Preparar datos para el template
    for item in alumnos_banco:
        item.inscripciones_seccion = inscripciones_por_alumno.get(item.alumno_id, [])
        inscripciones_activas = [
            inscripcion
            for inscripcion in item.inscripciones_seccion
            if inscripcion.estado == AlumnoSeccion.Estado.ACTIVO
        ]
        secciones_activas_ids = {inscripcion.seccion_id for inscripcion in inscripciones_activas}
        item.secciones_asignables = [
            sec for sec in secciones_disponibles if sec.pk not in secciones_activas_ids
        ]
        item.secciones_bloqueadas = inscripciones_activas
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
            "secciones_disponibles": secciones_disponibles,
            "alumnos_banco_tabla_pendiente": alumnos_banco_tabla_pendiente,
            "alumno_en_banco": alumno_en_banco,
            "cuil_buscado": cuil_buscado,
            "cuil_error": cuil_error,
            "url_carga_alumno": _url_carga_alumno(cuil_buscado, next_url),
            "url_editar_alumno": _url_carga_alumno(cuil_buscado, next_url),
            "modal_alumno_abierto": abrir_modal,
            "modal_action_url": _url_modal_alumnos(especial_context),
            "modal_volver_url": url_alumnos,
        }
    )
    return render(request, "especial/alumnos_especial.html", context)