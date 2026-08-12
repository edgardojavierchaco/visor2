# -*- coding: utf-8 -*-

import re
from urllib.parse import urlencode

from django.apps import apps
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.utils import OperationalError, ProgrammingError
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.urls import NoReverseMatch, reverse

from .forms import CefBajaMotivoForm, CefBusquedaAlumnoForm, CefInscripcionForm
from .models import CefGrupo, CefInscripcion
from .permisos import cef_required
from .services import (
    asegurar_alumno_banco_activo,
    crear_inscripcion_activa,
    dar_baja_inscripcion,
    reinscribir_alumno,
    validar_ciclo_escribible,
)
from .views_alumnos import MSG_BANCO_ALUMNOS_PENDIENTE, _calcular_edad
from .views_contexto import (
    contexto_base,
    normalizar_vista_cef,
    redirect_con_contexto,
    resolver_origen_gestion_grupo,
)


ESTADOS_INSCRIPCION_ABIERTA = [
    CefInscripcion.Estado.ACTIVO,
]

ORIGENES_INSCRIPCION = {"alumnos", "cursos"}


def _solo_digitos(valor):
    return re.sub(r"\D", "", str(valor or ""))


def _origen_inscripcion(valor):
    return valor if valor in ORIGENES_INSCRIPCION else "cursos"


def _is_ajax(request):
    return request.headers.get("x-requested-with") == "XMLHttpRequest"


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
    inscripciones = list(
        CefInscripcion.objects.filter(grupo=grupo)
        .select_related("alumno", "alumno__sexo")
        .order_by("alumno__apellidos", "alumno__nombres")
    )
    for inscripcion in inscripciones:
        inscripcion.edad = _calcular_edad(
            getattr(inscripcion.alumno, "fecha_nacimiento", None)
        )
    return inscripciones


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


def _url_carga_alumno(cuil, next_url, return_label="Volver al grupo"):
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


def _url_modal_grupo(
    grupo,
    cef_context,
    cuil="",
    origen="cursos",
    destino="",
    *,
    vista_alumnos="actuales",
    vista_docentes="actuales",
):
    params = {}
    if cef_context.get("cueanexo"):
        params["cueanexo"] = cef_context["cueanexo"]
    if cef_context.get("ciclo"):
        params["ciclo"] = cef_context["ciclo"].pk
    params["origen"] = (
        resolver_origen_gestion_grupo(origen)
        if destino == "gestionar"
        else _origen_inscripcion(origen)
    )
    if destino == "gestionar":
        params["destino"] = "gestionar"
        params["vista_alumnos"] = normalizar_vista_cef(vista_alumnos)
        params["vista_docentes"] = normalizar_vista_cef(vista_docentes)
    params["abrir_modal_alumno"] = "1"
    if cuil:
        params["cuil"] = cuil
    return f"{reverse('cef:inscripcion_grupo', kwargs={'grupo_id': grupo.pk})}?{urlencode(params)}"


def _url_inscripcion_grupo(grupo, cef_context, origen="cursos"):
    params = {}
    if cef_context.get("cueanexo"):
        params["cueanexo"] = cef_context["cueanexo"]
    if cef_context.get("ciclo"):
        params["ciclo"] = cef_context["ciclo"].pk
    params["origen"] = _origen_inscripcion(origen)
    querystring = urlencode(params)
    url = reverse("cef:inscripcion_grupo", kwargs={"grupo_id": grupo.pk})
    return f"{url}?{querystring}" if querystring else url


def _url_gestionar_grupo(
    grupo,
    cef_context,
    origen="grupos",
    ancla="",
    *,
    vista_alumnos="actuales",
    vista_docentes="actuales",
):
    params = {}
    if cef_context.get("cueanexo"):
        params["cueanexo"] = cef_context["cueanexo"]
    if cef_context.get("ciclo"):
        params["ciclo"] = cef_context["ciclo"].pk
    params["origen"] = resolver_origen_gestion_grupo(origen)
    params["vista_alumnos"] = normalizar_vista_cef(vista_alumnos)
    params["vista_docentes"] = normalizar_vista_cef(vista_docentes)
    querystring = urlencode(params)
    url = reverse("cef:gestionar_grupo", kwargs={"grupo_id": grupo.pk})
    url = f"{url}?{querystring}" if querystring else url
    return f"{url}#{ancla}" if ancla else url


def _errores_form(form):
    return " ".join(error for errors in form.errors.values() for error in errors)


def _ajax_inscripcion_response(request, context, ok, message):
    return JsonResponse(
        {
            "ok": ok,
            "message": message,
            "modal_html": render_to_string(
                "cef/modal_busqueda_alumno_cef.html",
                context,
                request=request,
            ),
            "fragment_selector": "[data-cef-fragment='inscripciones-grupo']",
            "fragment_html": render_to_string(
                "cef/inscripciones_grupo_lista_cef.html",
                context,
                request=request,
            ),
        }
    )


def _ajax_inscripciones_fragment_response(request, context, ok, message):
    return JsonResponse(
        {
            "ok": ok,
            "message": message,
            "fragment_selector": "[data-cef-fragment='inscripciones-grupo']",
            "fragment_html": render_to_string(
                "cef/inscripciones_grupo_lista_cef.html",
                context,
                request=request,
            ),
            "close_modal": ok,
        }
    )


def _baja_alumno_grupo(request, grupo, cef_context):
    baja_form = CefBajaMotivoForm(request.POST)
    if not baja_form.is_valid():
        return False, _errores_form(baja_form)

    try:
        inscripcion_id = int(request.POST.get("inscripcion_id"))
    except (TypeError, ValueError):
        return False, "La inscripción seleccionada no es válida."

    inscripcion = get_object_or_404(
        CefInscripcion.objects.filter(
            grupo=grupo,
            grupo__cueanexo=cef_context["cueanexo"],
            grupo__ciclo=cef_context["ciclo"],
        ),
        pk=inscripcion_id,
    )
    try:
        dar_baja_inscripcion(
            inscripcion,
            request.user,
            baja_form.cleaned_data["motivo_baja"],
        )
        return True, "Alumno dado de baja del grupo correctamente."
    except ValidationError as exc:
        return False, "; ".join(exc.messages)


def _alta_alumno_grupo(request, grupo, cef_context):
    try:
        inscripcion_id = int(request.POST.get("inscripcion_id"))
    except (TypeError, ValueError):
        return False, "La inscripción seleccionada no es válida."

    inscripcion = get_object_or_404(
        CefInscripcion.objects.filter(
            grupo=grupo,
            grupo__cueanexo=cef_context["cueanexo"],
            grupo__ciclo=cef_context["ciclo"],
        ),
        pk=inscripcion_id,
    )
    try:
        reinscribir_alumno(inscripcion, request.user)
        return True, "Alumno reinscripto correctamente."
    except ValidationError as exc:
        return False, "; ".join(exc.messages)


@cef_required
def inscripcion_grupo(request, grupo_id):
    context = contexto_base(request, "grupos", "Inscripción de alumnos CEF")
    cef_context = context["cef_context"]
    destino_gestionar = (
        request.GET.get("destino") or request.POST.get("destino")
    ) == "gestionar"
    origen_solicitado = request.GET.get("origen") or request.POST.get("origen")
    vista_alumnos = normalizar_vista_cef(
        request.GET.get("vista_alumnos") or request.POST.get("vista_alumnos")
    )
    vista_docentes = normalizar_vista_cef(
        request.GET.get("vista_docentes") or request.POST.get("vista_docentes")
    )
    origen = (
        resolver_origen_gestion_grupo(origen_solicitado)
        if destino_gestionar
        else _origen_inscripcion(origen_solicitado)
    )

    if not cef_context["puede_consultar"]:
        messages.warning(
            request,
            "Seleccioná un CUE-Anexo y un ciclo lectivo para administrar inscripciones.",
        )
        return redirect(redirect_con_contexto("cef:carga_grupo", cef_context))

    grupo = _grupo_seguro(grupo_id, cef_context)
    if request.method == "POST" and not cef_context["puede_operar"]:
        mensaje = "El ciclo está cerrado. La información se encuentra en modo sólo lectura."
        if _is_ajax(request):
            return JsonResponse({"ok": False, "message": mensaje})
        messages.error(request, mensaje)
        return redirect(
            _url_gestionar_grupo(
                grupo,
                cef_context,
                origen,
                vista_alumnos=vista_alumnos,
                vista_docentes=vista_docentes,
            )
        )
    if request.method == "POST" and grupo.estado != CefGrupo.Estado.ACTIVO:
        mensaje = "El grupo está dado de baja y solo puede consultarse."
        if _is_ajax(request):
            return JsonResponse({"ok": False, "message": mensaje})
        messages.error(request, mensaje)
        return redirect(
            _url_gestionar_grupo(
                grupo,
                cef_context,
                origen,
                vista_alumnos=vista_alumnos,
                vista_docentes=vista_docentes,
            )
        )
    inscripcion_grupo_url = _url_inscripcion_grupo(grupo, cef_context, origen)
    gestionar_grupo_url = _url_gestionar_grupo(
        grupo,
        cef_context,
        origen,
        "alumnos-curso",
        vista_alumnos=vista_alumnos,
        vista_docentes=vista_docentes,
    )
    context.update(
        {
            "origen": origen,
            "inscripcion_grupo_url": inscripcion_grupo_url,
            "volver_url": redirect_con_contexto(
                "cef:alumnos" if origen == "alumnos" else "cef:carga_grupo",
                cef_context,
            ),
            "volver_label": (
                "Volver a alumnos" if origen == "alumnos" else "Volver a Grupos"
            ),
        }
    )
    alumno = None
    inscripcion_abierta = None
    cuil_buscado = ""
    cuil_error = ""
    abrir_modal = request.GET.get("abrir_modal_alumno") == "1"
    ajax_ok = False
    ajax_message = ""

    if request.method == "POST" and request.POST.get("accion") in {"baja_alumno", "alta_alumno"}:
        if request.POST.get("accion") == "alta_alumno":
            ajax_ok, ajax_message = _alta_alumno_grupo(request, grupo, cef_context)
        else:
            ajax_ok, ajax_message = _baja_alumno_grupo(request, grupo, cef_context)
        if not _is_ajax(request):
            if ajax_ok:
                messages.success(request, ajax_message)
            else:
                messages.error(request, ajax_message)
            return redirect(inscripcion_grupo_url)

        context.update(
            {
                "grupo": grupo,
                "grupo_dias_texto": _dias_texto(grupo),
                "inscripciones": _inscripciones_grupo(grupo),
            }
        )
        return _ajax_inscripciones_fragment_response(
            request,
            context,
            ajax_ok,
            ajax_message,
        )

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
            ajax_message = "Primero buscá un alumno existente por CUIL."
            if not _is_ajax(request):
                messages.error(request, ajax_message)
        else:
            inscripcion_abierta = CefInscripcion.objects.filter(
                grupo=grupo,
                alumno=alumno,
                estado__in=ESTADOS_INSCRIPCION_ABIERTA,
            ).first()

            if inscripcion_abierta:
                ajax_message = "El alumno ya se encuentra inscripto en ese grupo."
                if not _is_ajax(request):
                    messages.info(request, ajax_message)
            else:
                try:
                    asegurar_alumno_banco_activo(
                        alumno=alumno,
                        cueanexo=cef_context["cueanexo"],
                        ciclo=cef_context["ciclo"],
                        user=request.user,
                    )
                except (OperationalError, ProgrammingError):
                    if not _is_ajax(request):
                        messages.warning(request, MSG_BANCO_ALUMNOS_PENDIENTE)
                except (IntegrityError, ValidationError):
                    if not _is_ajax(request):
                        messages.warning(
                            request,
                            "No se pudo actualizar el banco de alumnos CEF, pero se continuará con la inscripción al grupo.",
                        )

                try:
                    crear_inscripcion_activa(
                        grupo=grupo,
                        alumno=alumno,
                        user=request.user,
                    )
                    if _is_ajax(request):
                        inscripcion_abierta = CefInscripcion.objects.filter(
                            grupo=grupo,
                            alumno=alumno,
                            estado__in=ESTADOS_INSCRIPCION_ABIERTA,
                        ).first()
                        ajax_ok = True
                        ajax_message = "Alumno inscripto correctamente."
                    else:
                        messages.success(request, "Alumno inscripto correctamente.")
                        return redirect(
                            gestionar_grupo_url
                            if destino_gestionar
                            else inscripcion_grupo_url
                        )
                except ValidationError as exc:
                    ajax_message = "; ".join(exc.messages)
                    if not _is_ajax(request):
                        messages.error(request, ajax_message)
                except IntegrityError:
                    ajax_message = "No se pudo crear la inscripción. Verificá que no exista una inscripción activa."
                    if not _is_ajax(request):
                        messages.error(request, ajax_message)
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

    next_url = _url_modal_grupo(
        grupo,
        cef_context,
        cuil_buscado,
        origen,
        "gestionar" if destino_gestionar else "",
        vista_alumnos=vista_alumnos,
        vista_docentes=vista_docentes,
    )
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
            "modal_action_url": _url_modal_grupo(
                grupo,
                cef_context,
                origen=origen,
                destino="gestionar" if destino_gestionar else "",
                vista_alumnos=vista_alumnos,
                vista_docentes=vista_docentes,
            ),
            "modal_tiene_grupo": True,
            "modal_volver_url": (
                gestionar_grupo_url
                if destino_gestionar
                else inscripcion_grupo_url
            ),
            "modal_feedback": ajax_message,
            "modal_feedback_level": "success" if ajax_ok else "error",
        }
    )
    if request.method == "POST" and _is_ajax(request):
        if destino_gestionar:
            from .views_carga_grupo import _ajax_gestionar_fragment_response

            return _ajax_gestionar_fragment_response(
                request,
                grupo,
                cef_context,
                ajax_ok,
                ajax_message,
                origen,
                "cef/modal_busqueda_alumno_cef.html",
                context,
            )
        return _ajax_inscripcion_response(request, context, ajax_ok, ajax_message)
    if request.method == "POST" and destino_gestionar:
        return redirect(gestionar_grupo_url)
    return render(request, "cef/inscripcion_grupo_cef.html", context)


@cef_required
def editar_inscripcion_grupo(request, grupo_id, inscripcion_id):
    context = contexto_base(request, "grupos", "Editar inscripción CEF")
    cef_context = context["cef_context"]

    if not cef_context["puede_operar"]:
        messages.warning(
            request,
            "El ciclo está cerrado. La información se encuentra en modo sólo lectura."
            if cef_context["ciclo_cerrado"]
            else "Seleccioná un CUE-Anexo y un ciclo lectivo para administrar inscripciones.",
        )
        return redirect(redirect_con_contexto("cef:carga_grupo", cef_context))

    grupo = _grupo_seguro(grupo_id, cef_context)
    volver_gestionar = (
        request.GET.get("volver") == "gestionar"
        or request.POST.get("volver") == "gestionar"
    )
    origen_solicitado = request.GET.get("origen") or request.POST.get("origen")
    vista_alumnos = normalizar_vista_cef(
        request.GET.get("vista_alumnos") or request.POST.get("vista_alumnos")
    )
    vista_docentes = normalizar_vista_cef(
        request.GET.get("vista_docentes") or request.POST.get("vista_docentes")
    )
    origen = (
        resolver_origen_gestion_grupo(origen_solicitado)
        if volver_gestionar
        else _origen_inscripcion(origen_solicitado)
    )
    volver_url = (
        _url_gestionar_grupo(
            grupo,
            cef_context,
            origen,
            "alumnos-curso",
            vista_alumnos=vista_alumnos,
            vista_docentes=vista_docentes,
        )
        if volver_gestionar
        else _url_inscripcion_grupo(grupo, cef_context, origen)
    )
    volver_label = (
        "Volver a Gestionar grupo"
        if volver_gestionar
        else "Volver a inscripción"
    )
    if grupo.estado != CefGrupo.Estado.ACTIVO:
        messages.error(request, "El grupo está dado de baja y no puede editarse.")
        return redirect(volver_url)
    inscripcion = get_object_or_404(
        CefInscripcion.objects.filter(
            grupo=grupo,
            grupo__cueanexo=cef_context["cueanexo"],
            grupo__ciclo=cef_context["ciclo"],
            estado=CefInscripcion.Estado.ACTIVO,
        ).select_related("alumno", "alumno__sexo"),
        pk=inscripcion_id,
    )

    if request.method == "POST":
        form = CefInscripcionForm(request.POST, instance=inscripcion)
        if form.is_valid():
            inscripcion = form.save(commit=False)
            inscripcion.actualizado_por = request.user
            try:
                with transaction.atomic():
                    validar_ciclo_escribible(grupo.ciclo_id)
                    inscripcion.save()
            except ValidationError as exc:
                form.add_error(None, "; ".join(exc.messages))
            else:
                messages.success(request, "Inscripción actualizada correctamente.")
                return redirect(volver_url)

        messages.error(request, "Revisá los datos de la inscripción.")
    else:
        form = CefInscripcionForm(instance=inscripcion)

    context.update(
        {
            "grupo": grupo,
            "grupo_dias_texto": _dias_texto(grupo),
            "inscripcion": inscripcion,
            "form": form,
            "volver_url": volver_url,
            "volver_label": volver_label,
            "volver_gestionar": volver_gestionar,
            "origen": origen,
            "vista_alumnos": vista_alumnos,
            "vista_docentes": vista_docentes,
        }
    )
    return render(request, "cef/inscripcion_grupo_form_cef.html", context)
