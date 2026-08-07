# -*- coding: utf-8 -*-

import re
from urllib.parse import urlencode

from django.apps import apps
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.db.utils import OperationalError, ProgrammingError
from django.urls import NoReverseMatch, reverse
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.template.loader import render_to_string
from django.views.decorators.http import require_GET

from .forms import CefBajaMotivoForm, CefBusquedaAlumnoForm
from .models import CefAlumnoCef, CefGrupo, CefInscripcion
from .permisos import cef_required
from .performance import perf_render, perf_start_view
from .services import (
    asegurar_alumno_banco_activo,
    crear_inscripcion_activa,
    dar_baja_alumno_banco,
)
from .views_contexto import (
    contexto_base,
    normalizar_vista_cef,
    render_fragmento_cef,
    resolver_contexto_operativo,
)


MSG_BANCO_ALUMNOS_PENDIENTE = (
    "El banco de alumnos CEF está pendiente de creación en base de datos."
)


def _solo_digitos(valor):
    return re.sub(r"\D", "", str(valor or ""))


def _is_ajax(request):
    return request.headers.get("x-requested-with") == "XMLHttpRequest"


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


def _url_alumnos(cef_context, vista="actuales"):
    params = {}
    if cef_context.get("cueanexo"):
        params["cueanexo"] = cef_context["cueanexo"]
    if cef_context.get("ciclo"):
        params["ciclo"] = cef_context["ciclo"].pk
    if normalizar_vista_cef(vista) == "historial":
        params["vista"] = "historial"
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
        estado=CefGrupo.Estado.ACTIVO,
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
        crear_inscripcion_activa(
            grupo=grupo,
            alumno=alumno_banco.alumno,
            user=request.user,
        )
        messages.success(request, "Alumno inscripto correctamente al grupo.")
    except ValidationError as exc:
        messages.error(request, "; ".join(exc.messages))
    except IntegrityError:
        messages.error(
            request,
            "No se pudo crear la inscripción. Verificá que no exista una inscripción activa.",
        )


def _inscribir_alumno_grupo_desde_historial(request, cef_context):
    if not cef_context["puede_operar"]:
        messages.error(
            request,
            "El ciclo está cerrado. La información se encuentra en modo sólo lectura.",
        )
        return

    periodo_id = _pk_post(request, "periodo_historico_id")
    grupo_id = _pk_post(request, "grupo_id")
    if not periodo_id or not grupo_id:
        messages.error(request, "No se pudo identificar el alumno o el grupo.")
        return

    periodo = get_object_or_404(
        CefAlumnoCef.objects.filter(cueanexo=cef_context["cueanexo"]).select_related(
            "alumno"
        ),
        pk=periodo_id,
    )
    alumno_activo_actual = CefAlumnoCef.objects.filter(
        cueanexo=cef_context["cueanexo"],
        ciclo=cef_context["ciclo"],
        alumno_id=periodo.alumno_id,
        estado=CefAlumnoCef.Estado.ACTIVO,
    ).exists()
    if not alumno_activo_actual:
        messages.error(request, "El alumno debe reincorporarse primero al CEF.")
        return

    grupo = CefGrupo.objects.filter(
        pk=grupo_id,
        cueanexo=cef_context["cueanexo"],
        ciclo=cef_context["ciclo"],
        estado=CefGrupo.Estado.ACTIVO,
    ).first()
    if not grupo:
        messages.error(request, "El grupo seleccionado no pertenece al CEF y ciclo actual.")
        return

    try:
        crear_inscripcion_activa(
            grupo=grupo,
            alumno=periodo.alumno,
            user=request.user,
        )
        messages.success(request, "Alumno inscripto correctamente al grupo actual.")
    except ValidationError as exc:
        messages.error(request, "; ".join(exc.messages))
    except IntegrityError:
        messages.error(
            request,
            "No se pudo crear la inscripción. Verificá que no exista una inscripción activa.",
        )


def _alumnos_banco(cef_context):
    if not cef_context["puede_consultar"]:
        return CefAlumnoCef.objects.none()

    return (
        CefAlumnoCef.objects.filter(
            cueanexo=cef_context["cueanexo"],
            ciclo=cef_context["ciclo"],
        )
        .select_related("alumno")
        .order_by("alumno_nombre_snapshot", "alumno_cuil_snapshot")
    )


def _alumnos_historial(cef_context):
    if not cef_context["puede_consultar"]:
        return CefAlumnoCef.objects.none()
    return (
        CefAlumnoCef.objects.filter(
            cueanexo=cef_context["cueanexo"],
            ciclo__anio__lt=cef_context["ciclo"].anio,
        )
        .select_related("ciclo")
        .order_by(
            "-ciclo__anio",
            "alumno_nombre_snapshot",
            "-fecha_alta",
            "pk",
        )
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
            estado=CefGrupo.Estado.ACTIVO,
        )
        .select_related("actividad", "turno")
        .order_by("actividad__nombre", "numero", "nombre")
    )


def _alumnos_listado_context(cef_context, vista="actuales"):
    vista = normalizar_vista_cef(vista)
    alumnos_banco_tabla_pendiente = False
    if vista == "historial":
        try:
            alumnos_historial = list(_alumnos_historial(cef_context))
        except (OperationalError, ProgrammingError):
            alumnos_historial = []
            alumnos_banco_tabla_pendiente = True
        alumnos_ids = {periodo.alumno_id for periodo in alumnos_historial}
        alumnos_activos_actuales = set()
        inscripciones_activas_por_alumno = {}
        grupos_disponibles = []
        if cef_context["puede_operar"] and alumnos_ids:
            alumnos_activos_actuales = set(
                CefAlumnoCef.objects.filter(
                    cueanexo=cef_context["cueanexo"],
                    ciclo=cef_context["ciclo"],
                    alumno_id__in=alumnos_ids,
                    estado=CefAlumnoCef.Estado.ACTIVO,
                ).values_list("alumno_id", flat=True)
            )
            inscripciones_activas = (
                CefInscripcion.objects.filter(
                    grupo__cueanexo=cef_context["cueanexo"],
                    grupo__ciclo=cef_context["ciclo"],
                    alumno_id__in=alumnos_ids,
                    estado=CefInscripcion.Estado.ACTIVO,
                )
                .select_related("grupo", "grupo__actividad", "grupo__turno")
                .order_by("grupo__actividad__nombre", "grupo__numero")
            )
            for inscripcion in inscripciones_activas:
                inscripciones_activas_por_alumno.setdefault(
                    inscripcion.alumno_id,
                    [],
                ).append(inscripcion)
            grupos_disponibles = list(_grupos_disponibles(cef_context))

        for periodo in alumnos_historial:
            periodo.activo_banco_actual = periodo.alumno_id in alumnos_activos_actuales
            periodo.grupos_bloqueados = inscripciones_activas_por_alumno.get(
                periodo.alumno_id,
                [],
            )
            grupos_bloqueados_ids = {
                inscripcion.grupo_id for inscripcion in periodo.grupos_bloqueados
            }
            periodo.grupos_asignables = [
                grupo
                for grupo in grupos_disponibles
                if grupo.pk not in grupos_bloqueados_ids
            ]
        return {
            "vista": vista,
            "alumnos_historial": alumnos_historial,
            "grupos_disponibles": grupos_disponibles,
            "alumnos_banco_tabla_pendiente": alumnos_banco_tabla_pendiente,
        }

    try:
        alumnos_banco = list(_alumnos_banco(cef_context))
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
    url_alumnos = _url_alumnos(cef_context)

    for item in alumnos_banco:
        item.inscripciones_grupo = inscripciones_por_alumno.get(
            item.alumno_id,
            [],
        )
        inscripciones_activas = [
            inscripcion
            for inscripcion in item.inscripciones_grupo
            if inscripcion.estado == CefInscripcion.Estado.ACTIVO
        ]
        item.inscripciones_activas = inscripciones_activas
        grupos_activos_ids = {
            inscripcion.grupo_id for inscripcion in inscripciones_activas
        }
        item.grupos_asignables = [
            grupo
            for grupo in grupos_disponibles
            if grupo.pk not in grupos_activos_ids
        ]
        item.grupos_bloqueados = inscripciones_activas
        item.url_editar_alumno = _url_carga_alumno(
            item.alumno_cuil_snapshot or getattr(item.alumno, "cuil", ""),
            url_alumnos,
        )

    return {
        "vista": vista,
        "alumnos": alumnos_banco,
        "grupos_disponibles": grupos_disponibles,
        "alumnos_banco_tabla_pendiente": alumnos_banco_tabla_pendiente,
        "baja_form_vacio": CefBajaMotivoForm(),
    }


def _alumno_cef_seguro(alumno_banco_id, cef_context):
    try:
        alumno_banco_id = int(alumno_banco_id)
    except (TypeError, ValueError):
        raise Http404("El alumno seleccionado no es válido.")

    return get_object_or_404(
        CefAlumnoCef.objects.filter(
            cueanexo=cef_context["cueanexo"],
            ciclo=cef_context["ciclo"],
        ).select_related("alumno"),
        pk=alumno_banco_id,
    )


def _preparar_alumno_baja(alumno_banco, cef_context):
    alumno_banco.inscripciones_activas = list(
        CefInscripcion.objects.filter(
            alumno=alumno_banco.alumno,
            grupo__cueanexo=cef_context["cueanexo"],
            grupo__ciclo=cef_context["ciclo"],
            estado=CefInscripcion.Estado.ACTIVO,
        )
        .select_related("grupo", "grupo__actividad", "grupo__turno")
        .order_by("grupo__actividad__nombre", "grupo__numero")
    )
    return alumno_banco


def _alumno_baja_modal(cef_context, alumno_banco_id):
    if not cef_context["puede_operar"] or not alumno_banco_id:
        return None
    return _preparar_alumno_baja(
        _alumno_cef_seguro(alumno_banco_id, cef_context),
        cef_context,
    )


def _dar_baja_alumno_cef(request, cef_context):
    alumno_banco = _preparar_alumno_baja(
        _alumno_cef_seguro(request.POST.get("alumno_banco_id"), cef_context),
        cef_context,
    )
    baja_form = CefBajaMotivoForm(request.POST)
    if alumno_banco.estado != CefAlumnoCef.Estado.ACTIVO:
        return False, "El alumno ya no se encuentra activo en este CEF y ciclo.", alumno_banco, baja_form
    if alumno_banco.inscripciones_activas:
        return (
            False,
            "No se puede dar de baja al alumno del CEF porque posee inscripciones activas.",
            alumno_banco,
            baja_form,
        )
    if not baja_form.is_valid():
        return False, _errores_form(baja_form), alumno_banco, baja_form

    try:
        dar_baja_alumno_banco(
            alumno_banco,
            request.user,
            baja_form.cleaned_data["motivo_baja"],
        )
    except ValidationError as exc:
        alumno_banco = _preparar_alumno_baja(
            _alumno_cef_seguro(alumno_banco.pk, cef_context),
            cef_context,
        )
        return False, "; ".join(exc.messages), alumno_banco, baja_form
    return True, "Alumno dado de baja del CEF correctamente.", alumno_banco, baja_form


def _alumno_en_banco_activo(alumno, cef_context):
    if not alumno or not cef_context["puede_operar"]:
        return False

    return CefAlumnoCef.objects.filter(
        cueanexo=cef_context["cueanexo"],
        ciclo=cef_context["ciclo"],
        alumno=alumno,
        estado=CefAlumnoCef.Estado.ACTIVO,
    ).exists()


@cef_required
def alumnos(request):
    context = contexto_base(request, "alumnos", "Alumnos CEF")
    perf_start_view(request)
    cef_context = context["cef_context"]
    vista = normalizar_vista_cef(
        request.GET.get("vista") or request.POST.get("vista")
    )
    alumno = None
    cuil_buscado = ""
    cuil_error = ""
    alumno_en_banco = False
    abrir_modal = request.GET.get("abrir_modal_alumno") == "1"
    baja_modal_alumno = None
    baja_form = CefBajaMotivoForm()

    if request.method == "POST":
        accion = request.POST.get("accion")
        if vista == "historial" and accion != "inscribir_grupo_historial":
            message = "Historial es una vista de sólo lectura."
            if _is_ajax(request):
                return JsonResponse({"ok": False, "message": message})
            messages.error(request, message)
            return redirect(_url_alumnos(cef_context, "historial"))
        if not cef_context["puede_operar"]:
            message = (
                "El ciclo está cerrado. La información se encuentra en modo sólo lectura."
                if cef_context["ciclo_cerrado"]
                else "Seleccioná un CUE-Anexo y un ciclo lectivo para gestionar alumnos."
            )
            if _is_ajax(request):
                return JsonResponse({"ok": False, "message": message})
            messages.error(request, message)
            return redirect(_url_alumnos(cef_context, vista))
        if accion == "inscribir_grupo_historial":
            if vista != "historial":
                messages.error(request, "La acción histórica solicitada no es válida.")
                return redirect(_url_alumnos(cef_context))
            _inscribir_alumno_grupo_desde_historial(request, cef_context)
            return redirect(_url_alumnos(cef_context, "historial"))
        if request.POST.get("accion") == "baja_cef":
            baja_ok, baja_message, baja_modal_alumno, baja_form = _dar_baja_alumno_cef(
                request,
                cef_context,
            )
            if _is_ajax(request):
                baja_context = {
                    "cef_context": cef_context,
                    "baja_action_url": _url_alumnos(cef_context),
                    "baja_modal_alumno": None if baja_ok else baja_modal_alumno,
                    "baja_form": baja_form,
                }
                baja_context.update(_alumnos_listado_context(cef_context))
                return JsonResponse(
                    {
                        "ok": baja_ok,
                        "message": baja_message,
                        "fragment_selector": "[data-cef-fragment='alumnos-banco']",
                        "fragment_html": render_to_string(
                            "cef/alumnos_lista_cef.html",
                            baja_context,
                            request=request,
                        ),
                        "modal_html": render_to_string(
                            "cef/alumno_baja_cef_modal.html",
                            baja_context,
                            request=request,
                        ),
                        "close_modal": baja_ok,
                    }
                )
            if baja_ok:
                messages.success(request, baja_message)
            else:
                messages.error(request, baja_message)
            return redirect(_url_alumnos(cef_context))

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
                try:
                    banco, creado = asegurar_alumno_banco_activo(
                        alumno=alumno,
                        cueanexo=cef_context["cueanexo"],
                        ciclo=cef_context["ciclo"],
                        user=request.user,
                    )
                    tabla_pendiente = False
                except (OperationalError, ProgrammingError):
                    banco = None
                    creado = False
                    tabla_pendiente = True
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

        if request.GET.get("abrir_modal_baja") == "1":
            baja_modal_alumno = _alumno_baja_modal(
                cef_context,
                request.GET.get("alumno_banco_id"),
            )

    next_url = _url_modal_alumnos(cef_context, cuil_buscado)
    url_alumnos = _url_alumnos(cef_context)
    if alumno and not alumno_en_banco:
        try:
            alumno_en_banco = _alumno_en_banco_activo(alumno, cef_context)
        except (OperationalError, ProgrammingError):
            alumno_en_banco = False

    context.update(
        {
            "busqueda_form": busqueda_form,
            "alumno": alumno,
            "alumno_row": _alumno_row(alumno),
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
            "baja_action_url": url_alumnos,
            "baja_modal_alumno": baja_modal_alumno,
            "baja_form": baja_form,
        }
    )
    context.update(_alumnos_listado_context(cef_context, vista))
    return perf_render(request, "cef/alumnos_cef.html", context)


@cef_required
@require_GET
def alumnos_fragmento(request):
    cef_context = resolver_contexto_operativo(request)
    vista = normalizar_vista_cef(request.GET.get("vista"))
    context = {
        "cef_context": cef_context,
        "cef_partial": True,
        "modal_action_url": _url_modal_alumnos(cef_context),
        "baja_action_url": _url_alumnos(cef_context),
        "baja_modal_alumno": (
            _alumno_baja_modal(
                cef_context,
                request.GET.get("alumno_banco_id"),
            )
            if vista == "actuales" and request.GET.get("abrir_modal_baja") == "1"
            else None
        ),
        "baja_form": CefBajaMotivoForm(),
    }
    context.update(_alumnos_listado_context(cef_context, vista))
    return render_fragmento_cef(request, "cef/alumnos_seccion_cef.html", context)
