# apps/especial/views_alumnos.py
# -*- coding: utf-8 -*-
import logging
import re
from urllib.parse import urlencode
from django.apps import apps
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.db.utils import OperationalError, ProgrammingError
from django.db.models import Count, Q
from django.http import Http404, HttpResponseNotAllowed, JsonResponse
from django.urls import NoReverseMatch, reverse
from django.shortcuts import get_object_or_404, redirect, render
from .forms import (
    EspecialBajaMotivoForm,
    EspecialBusquedaAlumnoForm,
    EspecialMatriculaCompartidaForm,
)
from .models import (
    PADRON_DB_ALIAS,
    AlumnoSeccion,
    EspecialAlumnoBanco,
    EspecialPadronOferta,
    SeccionEspecial,
    cueanexo_tiene_oferta_matricula_compartida,
    normalizar_cueanexo,
)
from .permisos import especial_required
from .services.alumnos import (
    actualizar_matricula_compartida,
    asegurar_alumno_banco,
    dar_baja_alumno_banco,
)
from .views_contexto import contexto_base, render_especial
from .views_inscripcion_seccion import crear_inscripcion_activa

logger = logging.getLogger(__name__)

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


def _matricula_compartida_habilitada(especial_context):
    if not especial_context.get("puede_operar"):
        return False
    try:
        return cueanexo_tiene_oferta_matricula_compartida(
            especial_context.get("cueanexo")
        )
    except (OperationalError, ProgrammingError):
        logger.exception(
            "No se pudo verificar la oferta de matrícula compartida para el CUE-Anexo %s.",
            especial_context.get("cueanexo"),
        )
        return None


def _matricula_compartida_form(data, especial_context, habilitada):
    return EspecialMatriculaCompartidaForm(
        data,
        cueanexo_actual=especial_context.get("cueanexo"),
        matricula_compartida_habilitada=habilitada,
    )


def _validar_matricula_compartida_form(form):
    """Valida el formulario sin exponer fallos técnicos del padrón."""
    try:
        if form.is_valid():
            return True, ""
    except (OperationalError, ProgrammingError):
        logger.exception("No se pudo validar la matrícula compartida contra Padrón.")
        return False, "No se pudo consultar el padrón en este momento."
    return False, _errores_form(form)


def _pk_post(valor):
    try:
        return int(valor or "")
    except (TypeError, ValueError):
        return None


def _alumno_banco_seguro(alumno_banco_id, especial_context, for_update=False):
    alumno_banco_id = _pk_post(alumno_banco_id)
    if not especial_context["puede_operar"] or not alumno_banco_id:
        raise Http404("El alumno seleccionado no es válido.")
    queryset = _alumnos_banco_queryset(especial_context).select_related("alumno")
    if for_update:
        queryset = queryset.select_for_update()
    return get_object_or_404(
        queryset,
        pk=alumno_banco_id,
    )


def _preparar_alumno_baja(alumno_banco, especial_context):
    alumno_banco.inscripciones_activas = list(
        AlumnoSeccion.objects.filter(
            alumno_id=alumno_banco.alumno_id,
            seccion__cueanexo=especial_context["cueanexo"],
            seccion__ciclo=especial_context["ciclo"],
            estado=AlumnoSeccion.Estado.ACTIVO,
        )
        .select_related("seccion", "seccion__cd_tipo_seccion", "seccion__turno")
        .order_by("seccion__nombre_seccion")
    )
    return alumno_banco


def _alumno_baja_modal(especial_context, alumno_banco_id):
    if not especial_context["puede_operar"] or not alumno_banco_id:
        return None
    return _preparar_alumno_baja(
        _alumno_banco_seguro(alumno_banco_id, especial_context),
        especial_context,
    )


def _dar_baja_alumno_especial(request, especial_context):
    alumno_banco = _preparar_alumno_baja(
        _alumno_banco_seguro(request.POST.get("alumno_banco_id"), especial_context),
        especial_context,
    )
    baja_form = EspecialBajaMotivoForm(request.POST)
    if alumno_banco.estado != EspecialAlumnoBanco.Estado.ACTIVO:
        return (
            False,
            "El alumno ya no se encuentra activo en este establecimiento y ciclo.",
            alumno_banco,
            baja_form,
        )
    if alumno_banco.inscripciones_activas:
        return (
            False,
            "No se puede dar de baja al alumno del banco porque posee inscripciones activas.",
            alumno_banco,
            baja_form,
        )
    if not baja_form.is_valid():
        return False, _errores_form(baja_form), alumno_banco, baja_form

    try:
        dar_baja_alumno_banco(
            alumno_banco=alumno_banco,
            user=request.user,
            motivo_baja=baja_form.cleaned_data["motivo_baja"],
            alumno_banco_queryset=_alumnos_banco_queryset(especial_context),
        )
    except ValidationError as exc:
        alumno_banco = _preparar_alumno_baja(
            _alumno_banco_seguro(alumno_banco.pk, especial_context),
            especial_context,
        )
        return False, "; ".join(exc.messages), alumno_banco, baja_form
    return True, "Alumno dado de baja de Especial correctamente.", alumno_banco, baja_form


def _actualizar_matricula_compartida(request, especial_context, habilitada):
    """Valida el formulario y delega la actualización al servicio de dominio."""
    alumno_banco = _alumno_banco_seguro(
        request.POST.get("alumno_banco_id"),
        especial_context,
    )
    form = _matricula_compartida_form(request.POST, especial_context, habilitada)
    formulario_valido, formulario_error = _validar_matricula_compartida_form(form)
    if not formulario_valido:
        return False, formulario_error, alumno_banco

    try:
        alumno_banco = actualizar_matricula_compartida(
            alumno_banco=alumno_banco,
            user=request.user,
            matricula_compartida=form.cleaned_data["matricula_compartida"],
            alumno_banco_queryset=_alumnos_banco_queryset(especial_context),
            padron_queryset=form.padron_queryset,
        )
    except ValidationError as exc:
        return False, "; ".join(exc.messages), alumno_banco
    except (OperationalError, ProgrammingError):
        logger.exception("No se pudo actualizar la matrícula compartida.")
        return False, "No se pudo consultar el padrón en este momento.", alumno_banco
    except IntegrityError:
        logger.exception("No se pudo actualizar la matrícula compartida por integridad.")
        return (
            False,
            "No se pudo actualizar la matrícula compartida por un conflicto de integridad.",
            alumno_banco,
        )

    return True, "Matrícula compartida actualizada correctamente.", alumno_banco


def _serializar_cueanexos_matricula_compartida(request, especial_context):
    """Busca CUE-Anexos del padrón general, limitados y sin duplicar."""
    term = (request.GET.get("q") or "").strip()[:80]
    queryset = (
        EspecialPadronOferta.objects.using(PADRON_DB_ALIAS)
        .exclude(cueanexo=especial_context["cueanexo"])
        .exclude(cueanexo__isnull=True)
    )
    if term:
        term_digits = _solo_digitos(term)
        query = Q(nom_est__icontains=term)
        if term_digits:
            query |= Q(cueanexo__icontains=term_digits)
        queryset = queryset.filter(query)

    queryset = (
        queryset
        .order_by("cueanexo", "nom_est", "id")
        .distinct("cueanexo")
        .values("cueanexo", "nom_est")[:20]
    )
    resultados = []
    vistos = set()
    for item in queryset:
        cueanexo = normalizar_cueanexo(item.get("cueanexo"))
        if not cueanexo or cueanexo in vistos:
            continue
        vistos.add(cueanexo)
        nombre = str(item.get("nom_est") or "Establecimiento sin nombre").strip()
        resultados.append(
            {
                "id": cueanexo,
                "text": f"{cueanexo} — {nombre}",
            }
        )
    return resultados


@especial_required
def buscar_cueanexos_matricula_compartida(request):
    """Endpoint protegido de autocomplete contra el padrón general."""
    if request.method != "GET":
        return HttpResponseNotAllowed(["GET"])

    context = contexto_base(request, "alumnos")
    especial_context = context["especial_context"]
    if not especial_context["puede_operar"]:
        return JsonResponse({"results": []})
    matricula_compartida_habilitada = _matricula_compartida_habilitada(
        especial_context
    )
    if matricula_compartida_habilitada is None:
        return JsonResponse(
            {"detail": "No se pudo consultar el padrón en este momento."},
            status=503,
        )
    if not matricula_compartida_habilitada:
        return JsonResponse(
            {"detail": "La matrícula compartida no está habilitada para este CUE-Anexo."},
            status=403,
        )

    try:
        resultados = _serializar_cueanexos_matricula_compartida(
            request,
            especial_context,
        )
    except (OperationalError, ProgrammingError):
        logger.exception(
            "No se pudo buscar CUE-Anexos de matrícula compartida en el padrón."
        )
        return JsonResponse(
            {"detail": "No se pudo consultar el padrón en este momento."},
            status=503,
        )
    return JsonResponse({"results": resultados, "pagination": {"more": False}})


def _inscribir_alumno_desde_banco(request, especial_context):
    """Inscribe un alumno activo del banco en una seccion del contexto."""
    if not especial_context["puede_operar"]:
        messages.error(
            request,
            "Seleccioná un CUE-Anexo y un ciclo lectivo para inscribir alumnos.",
        )
        return

    alumno_banco_id = _pk_post(request.POST.get("alumno_banco_id"))
    seccion_id = _pk_post(request.POST.get("seccion_id"))
    if not alumno_banco_id or not seccion_id:
        messages.error(request, "No se pudo identificar el alumno o la sección.")
        return

    alumno_banco_queryset = _alumnos_banco_queryset(especial_context)
    alumno_banco = (
        alumno_banco_queryset.filter(
            pk=alumno_banco_id,
            estado=EspecialAlumnoBanco.Estado.ACTIVO,
        )
        .select_related("alumno")
        .first()
    )
    if not alumno_banco:
        messages.error(
            request,
            "El alumno no está activo en el banco de este establecimiento y ciclo.",
        )
        return

    seccion = SeccionEspecial.objects.filter(
        pk=seccion_id,
        cueanexo=especial_context["cueanexo"],
        ciclo=especial_context["ciclo"],
        estado=SeccionEspecial.Estado.ACTIVO,
    ).first()
    if not seccion:
        messages.error(
            request,
            "La sección no corresponde al establecimiento y ciclo seleccionados.",
        )
        return

    try:
        _, creada = crear_inscripcion_activa(
            seccion=seccion,
            alumno=alumno_banco.alumno,
            user=request.user,
            seccion_queryset=SeccionEspecial.objects.filter(
                cueanexo=especial_context["cueanexo"],
                ciclo=especial_context["ciclo"],
            ),
            alumno_banco_queryset=alumno_banco_queryset,
        )
    except ValidationError as exc:
        messages.error(request, "; ".join(exc.messages))
    except IntegrityError:
        messages.error(
            request,
            "No se pudo crear la inscripción. Verificá que no exista una inscripción activa.",
        )
    else:
        messages.success(
            request,
            "Alumno inscripto correctamente."
            if creada
            else "La inscripción del alumno fue reactivada correctamente.",
        )


def _alumnos_banco_queryset(especial_context):
    if not especial_context["puede_operar"]:
        return EspecialAlumnoBanco.objects.none()
    return EspecialAlumnoBanco.objects.filter(
        cueanexo=especial_context["cueanexo"],
        ciclo=especial_context["ciclo"],
    )


def _alumnos_banco(especial_context):
    if not especial_context["puede_consultar"]:
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
            estado=AlumnoSeccion.Estado.ACTIVO,
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
        .annotate(
            alumnos_activos=Count(
                "alumnos",
                filter=Q(alumnos__estado=AlumnoSeccion.Estado.ACTIVO),
            )
        )
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


def _asegurar_alumno_banco(
    alumno,
    especial_context,
    user,
    matricula_compartida=None,
):
    """Compatibilidad local que delega el alta en el servicio transaccional."""
    if not alumno or not especial_context["puede_operar"]:
        return None, False, False
    try:
        banco, creado = asegurar_alumno_banco(
            alumno=alumno,
            cueanexo=especial_context["cueanexo"],
            ciclo=especial_context["ciclo"],
            user=user,
            matricula_compartida=matricula_compartida,
        )
        return banco, creado, False
    except (OperationalError, ProgrammingError):
        return None, False, True

@especial_required
def alumnos(request):
    context = contexto_base(request, "alumnos")
    especial_context = context["especial_context"]

    if request.method == "POST" and especial_context.get("ciclo_cerrado"):
        messages.error(
            request,
            "El ciclo seleccionado está cerrado y sólo puede consultarse.",
        )
        return redirect(request.get_full_path())
    
    alumno = None
    cuil_buscado = ""
    cuil_error = ""
    alumno_en_banco = False
    alumno_banco_actual = None
    matricula_compartida_habilitada = _matricula_compartida_habilitada(especial_context)
    matricula_compartida_error = ""
    matricula_compartida_cueanexo = ""
    matricula_compartida_posted = False
    abrir_modal = request.GET.get("abrir_modal_alumno") == "1"
    abrir_modal_baja = request.GET.get("abrir_modal_baja") == "1"
    baja_modal_alumno = None
    baja_form = EspecialBajaMotivoForm()
    baja_error = ""
    busqueda_form = EspecialBusquedaAlumnoForm()

    if request.method == "POST" and request.POST.get("accion") == "baja_especial":
        if not especial_context["puede_operar"]:
            messages.error(
                request,
                "Seleccioná un CUE-Anexo y un ciclo lectivo para dar de baja alumnos.",
            )
            return redirect(_url_alumnos(especial_context))
        baja_ok, baja_message, baja_modal_alumno, baja_form = _dar_baja_alumno_especial(
            request,
            especial_context,
        )
        if baja_ok:
            messages.success(request, baja_message)
            return redirect(_url_alumnos(especial_context))
        baja_error = baja_message
    elif request.method == "POST" and request.POST.get("accion") == "actualizar_matricula_compartida":
        abrir_modal = True
        ok, matricula_message, alumno_banco_actual = _actualizar_matricula_compartida(
            request,
            especial_context,
            matricula_compartida_habilitada,
        )
        alumno = alumno_banco_actual.alumno
        cuil_buscado = _solo_digitos(getattr(alumno, "cuil", ""))
        alumno_en_banco = True
        matricula_compartida_posted = True
        matricula_compartida_cueanexo = request.POST.get(
            "cueanexo_matricula_compartida",
            "",
        )
        if ok:
            messages.success(request, matricula_message)
            return redirect(_url_alumnos(especial_context))
        matricula_compartida_error = matricula_message
    elif request.method == "POST":
        if request.POST.get("accion") == "inscribir_seccion":
            _inscribir_alumno_desde_banco(request, especial_context)
            return redirect(_url_alumnos(especial_context))

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
            matricula_form = _matricula_compartida_form(
                request.POST,
                especial_context,
                matricula_compartida_habilitada,
            )
            matricula_compartida_posted = "cueanexo_matricula_compartida" in request.POST
            matricula_compartida_cueanexo = request.POST.get(
                "cueanexo_matricula_compartida",
                "",
            )
            formulario_valido, formulario_error = _validar_matricula_compartida_form(
                matricula_form
            )
            if not formulario_valido:
                matricula_compartida_error = formulario_error
            else:
                matricula_compartida = matricula_form.cleaned_data["matricula_compartida"]
                try:
                    banco, creado = asegurar_alumno_banco(
                        alumno=alumno,
                        cueanexo=especial_context["cueanexo"],
                        ciclo=especial_context["ciclo"],
                        user=request.user,
                        matricula_compartida=matricula_compartida,
                        padron_queryset=matricula_form.padron_queryset,
                    )
                    alumno_banco_actual = banco
                    alumno_en_banco = bool(banco)
                    if creado:
                        messages.success(request, "Alumno agregado al banco de Educación Especial.")
                        return redirect(_url_alumnos(especial_context))
                    else:
                        messages.info(
                            request,
                            "Ese alumno ya está activo en el banco de este establecimiento y ciclo.",
                        )
                except ValidationError as exc:
                    messages.error(request, "; ".join(exc.messages))
                except (OperationalError, ProgrammingError):
                    logger.exception("No se pudo crear el banco de alumnos Especial.")
                    messages.error(request, MSG_BANCO_ALUMNOS_PENDIENTE)
                except IntegrityError:
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

        if abrir_modal_baja:
            baja_modal_alumno = _alumno_baja_modal(
                especial_context,
                request.GET.get("alumno_banco_id"),
            )

    next_url = _url_modal_alumnos(especial_context, cuil_buscado)
    url_alumnos = _url_alumnos(especial_context)
    
    alumnos_banco_tabla_pendiente = False
    try:
        alumnos_banco = list(_alumnos_banco(especial_context))
        if alumno and not alumno_banco_actual:
            alumno_banco_actual = next(
                (
                    item
                    for item in alumnos_banco
                    if item.alumno_id == alumno.pk
                    and item.estado == EspecialAlumnoBanco.Estado.ACTIVO
                ),
                None,
            )
        alumno_en_banco = bool(alumno_banco_actual)
    except (OperationalError, ProgrammingError):
        alumnos_banco = []
        alumnos_banco_tabla_pendiente = True

    if alumno_banco_actual and not matricula_compartida_posted:
        matricula_compartida_cueanexo = alumno_banco_actual.matricula_compartida or ""

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
        secciones_activas_ids = {
            inscripcion.seccion_id for inscripcion in item.inscripciones_seccion
        }
        item.secciones_asignables = [
            sec
            for sec in secciones_disponibles
            if sec.pk not in secciones_activas_ids
            and sec.alumnos_activos < sec.capacidad_total
        ]
        item.secciones_bloqueadas = item.inscripciones_seccion
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
            "alumno_banco_actual": alumno_banco_actual,
            "cuil_buscado": cuil_buscado,
            "cuil_error": cuil_error,
            "url_carga_alumno": _url_carga_alumno(cuil_buscado, next_url),
            "url_editar_alumno": _url_carga_alumno(cuil_buscado, next_url),
            "modal_alumno_abierto": abrir_modal,
            "modal_action_url": _url_modal_alumnos(especial_context),
            "modal_volver_url": url_alumnos,
            "baja_action_url": url_alumnos,
            "baja_modal_alumno": baja_modal_alumno,
            "baja_form": baja_form,
            "baja_error": baja_error,
            "matricula_compartida_habilitada": matricula_compartida_habilitada,
            "matricula_compartida_busqueda_url": reverse(
                "especial:buscar_cueanexos_matricula_compartida"
            ),
            "matricula_compartida_error": matricula_compartida_error,
            "matricula_compartida_cueanexo": matricula_compartida_cueanexo,
        }
    )
    return render_especial(
        request,
        "especial/alumnos_especial.html",
        context,
        "especial/partials/alumnos_fragmento_especial.html",
    )
