# -*- coding: utf-8 -*-

import re
from urllib.parse import urlencode

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.db.utils import OperationalError, ProgrammingError
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.template.loader import render_to_string
from django.urls import reverse
from django.views.decorators.http import require_GET

from .forms import CefBajaMotivoForm, CefBusquedaDocenteForm, CefDocenteGrupoForm
from .models import (
    CefDocenteBnh,
    CefDocenteCef,
    CefDocenteGrupo,
    CefGrupo,
    PADRON_DB_ALIAS,
)
from .permisos import cef_required
from .performance import perf_render, perf_start_view
from .services import (
    asegurar_docente_banco_activo,
    crear_asignacion_docente_activa,
    dar_baja_docente_banco,
)
from .views_contexto import (
    contexto_base,
    normalizar_vista_cef,
    render_fragmento_cef,
    resolver_contexto_operativo,
)


URL_CARGA_PROFESOR = "/bnh/carga-personal/"
MSG_BANCO_DOCENTES_PENDIENTE = (
    "El banco de profesores CEF está pendiente de creación en base de datos."
)


def _solo_digitos(valor):
    return re.sub(r"\D", "", str(valor or ""))


def _is_ajax(request):
    return request.headers.get("x-requested-with") == "XMLHttpRequest"


def _buscar_docente(cuil):
    return (
        CefDocenteBnh.objects.using(PADRON_DB_ALIAS)
        .filter(cuil=cuil)
        .first()
    )


def _docente_row(docente):
    if not docente:
        return None

    return {
        "apellido": docente.apellido or "",
        "nombre": docente.nombre or "",
        "nombre_completo": docente.nombre_completo,
        "cuil": docente.cuil or "",
        "dni": docente.dni or "",
        "estado": docente.estado or "",
    }


def _docentes_cef(cef_context):
    if not cef_context["puede_consultar"]:
        return CefDocenteCef.objects.none()

    return (
        CefDocenteCef.objects.filter(
            cueanexo=cef_context["cueanexo"],
            ciclo=cef_context["ciclo"],
        )
        .order_by(
            "docente_nombre_snapshot",
            "docente_cuil",
            "estado",
        )
    )


def _docentes_historial(cef_context):
    if not cef_context["puede_consultar"]:
        return CefDocenteCef.objects.none()
    return (
        CefDocenteCef.objects.filter(
            cueanexo=cef_context["cueanexo"],
            ciclo__anio__lt=cef_context["ciclo"].anio,
        )
        .select_related("ciclo")
        .order_by(
            "-ciclo__anio",
            "docente_nombre_snapshot",
            "docente_cuil",
            "-fecha_alta",
            "pk",
        )
    )


def _asignaciones_por_docente(cef_context, docentes_banco):
    cuiles = [item.docente_cuil for item in docentes_banco]
    if not cuiles:
        return {}

    asignaciones = (
        CefDocenteGrupo.objects.filter(
            grupo__cueanexo=cef_context["cueanexo"],
            grupo__ciclo=cef_context["ciclo"],
            docente_cuil__in=cuiles,
        )
        .select_related("grupo", "grupo__actividad", "grupo__turno")
        .order_by("grupo__actividad__nombre", "grupo__numero", "rol")
    )

    por_docente = {}
    for asignacion in asignaciones:
        por_docente.setdefault(asignacion.docente_cuil, []).append(asignacion)
    return por_docente


def _asignaciones_activas_docente(cef_context, docente_cuil):
    return list(
        CefDocenteGrupo.objects.filter(
            grupo__cueanexo=cef_context["cueanexo"],
            grupo__ciclo=cef_context["ciclo"],
            docente_cuil=docente_cuil,
            estado=CefDocenteGrupo.Estado.ACTIVO,
        )
        .select_related("grupo", "grupo__actividad", "grupo__turno")
        .order_by("grupo__actividad__nombre", "grupo__numero", "rol")
    )


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


def _profesores_listado_context(cef_context, vista="actuales"):
    vista = normalizar_vista_cef(vista)
    docentes_banco_tabla_pendiente = False
    if vista == "historial":
        try:
            docentes_historial = list(_docentes_historial(cef_context))
        except (OperationalError, ProgrammingError):
            docentes_historial = []
            docentes_banco_tabla_pendiente = True
        cuiles = {periodo.docente_cuil for periodo in docentes_historial}
        docentes_activos_actuales = set()
        asignaciones_activas_por_docente = {}
        grupos_disponibles = []
        if cef_context["puede_operar"] and cuiles:
            docentes_activos_actuales = set(
                CefDocenteCef.objects.filter(
                    cueanexo=cef_context["cueanexo"],
                    ciclo=cef_context["ciclo"],
                    docente_cuil__in=cuiles,
                    estado=CefDocenteCef.Estado.ACTIVO,
                ).values_list("docente_cuil", flat=True)
            )
            asignaciones_activas = (
                CefDocenteGrupo.objects.filter(
                    grupo__cueanexo=cef_context["cueanexo"],
                    grupo__ciclo=cef_context["ciclo"],
                    docente_cuil__in=cuiles,
                    estado=CefDocenteGrupo.Estado.ACTIVO,
                )
                .select_related("grupo", "grupo__actividad", "grupo__turno")
                .order_by("grupo__actividad__nombre", "grupo__numero", "rol")
            )
            for asignacion in asignaciones_activas:
                asignaciones_activas_por_docente.setdefault(
                    asignacion.docente_cuil,
                    [],
                ).append(asignacion)
            grupos_disponibles = list(_grupos_disponibles(cef_context))

        for periodo in docentes_historial:
            periodo.activo_banco_actual = (
                periodo.docente_cuil in docentes_activos_actuales
            )
            periodo.grupos_bloqueados = asignaciones_activas_por_docente.get(
                periodo.docente_cuil,
                [],
            )
            grupos_bloqueados_ids = {
                asignacion.grupo_id for asignacion in periodo.grupos_bloqueados
            }
            periodo.grupos_asignables = [
                grupo
                for grupo in grupos_disponibles
                if grupo.pk not in grupos_bloqueados_ids
            ]
        return {
            "vista": vista,
            "docentes_historial": docentes_historial,
            "grupos_disponibles": grupos_disponibles,
            "docentes_banco_tabla_pendiente": docentes_banco_tabla_pendiente,
        }

    try:
        docentes = list(_docentes_cef(cef_context))
    except (OperationalError, ProgrammingError):
        docentes = []
        docentes_banco_tabla_pendiente = True

    try:
        asignaciones_por_docente = _asignaciones_por_docente(
            cef_context,
            docentes,
        )
    except (OperationalError, ProgrammingError):
        asignaciones_por_docente = {}

    grupos_disponibles = list(_grupos_disponibles(cef_context))
    url_profesores = _url_profesores(cef_context, vista)

    for item in docentes:
        item.asignaciones_grupo = asignaciones_por_docente.get(
            item.docente_cuil,
            [],
        )
        asignaciones_activas = [
            asignacion
            for asignacion in item.asignaciones_grupo
            if asignacion.estado == CefDocenteGrupo.Estado.ACTIVO
        ]
        item.asignaciones_activas = asignaciones_activas
        grupos_activos_ids = {
            asignacion.grupo_id for asignacion in asignaciones_activas
        }
        item.grupos_asignables = [
            grupo
            for grupo in grupos_disponibles
            if grupo.pk not in grupos_activos_ids
        ]
        item.grupos_bloqueados = asignaciones_activas
        item.url_editar_profesor = _url_carga_profesor(
            item.docente_cuil,
            url_profesores,
            "Volver a Profesores CEF",
        )

    return {
        "vista": vista,
        "docentes": docentes,
        "grupos_disponibles": grupos_disponibles,
        "docentes_banco_tabla_pendiente": docentes_banco_tabla_pendiente,
        "baja_form_vacio": CefBajaMotivoForm(),
    }


def _docente_en_banco_activo(docente, cef_context):
    if not docente or not cef_context["puede_operar"]:
        return False

    return CefDocenteCef.objects.filter(
        cueanexo=cef_context["cueanexo"],
        ciclo=cef_context["ciclo"],
        docente_cuil=docente.cuil,
        estado=CefDocenteCef.Estado.ACTIVO,
    ).exists()


def _docente_cef_seguro(docente_banco_id, cef_context):
    try:
        docente_banco_id = int(docente_banco_id)
    except (TypeError, ValueError):
        raise Http404("El profesor seleccionado no es válido.")

    return get_object_or_404(
        CefDocenteCef.objects.filter(
            cueanexo=cef_context["cueanexo"],
            ciclo=cef_context["ciclo"],
        ),
        pk=docente_banco_id,
    )


def _preparar_docente_baja(docente_banco, cef_context):
    docente_banco.asignaciones_activas = _asignaciones_activas_docente(
        cef_context,
        docente_banco.docente_cuil,
    )
    return docente_banco


def _docente_baja_modal(cef_context, docente_banco_id):
    if not cef_context["puede_operar"] or not docente_banco_id:
        return None
    return _preparar_docente_baja(
        _docente_cef_seguro(docente_banco_id, cef_context),
        cef_context,
    )


def _dar_baja_docente_cef(request, cef_context):
    docente_banco = _preparar_docente_baja(
        _docente_cef_seguro(
            request.POST.get("docente_banco_id"),
            cef_context,
        ),
        cef_context,
    )
    baja_form = CefBajaMotivoForm(request.POST)

    if docente_banco.estado != CefDocenteCef.Estado.ACTIVO:
        return False, "El profesor ya no se encuentra activo en este CEF y ciclo.", docente_banco, baja_form
    if docente_banco.asignaciones_activas:
        return (
            False,
            "No se puede dar de baja al profesor del CEF porque posee asignaciones activas.",
            docente_banco,
            baja_form,
        )
    if not baja_form.is_valid():
        return False, _errores_form(baja_form), docente_banco, baja_form

    try:
        dar_baja_docente_banco(
            docente_banco,
            request.user,
            baja_form.cleaned_data["motivo_baja"],
        )
    except ValidationError as exc:
        docente_banco = _preparar_docente_baja(
            _docente_cef_seguro(docente_banco.pk, cef_context),
            cef_context,
        )
        return False, "; ".join(exc.messages), docente_banco, baja_form
    return True, "Profesor dado de baja del CEF correctamente.", docente_banco, baja_form


def _url_carga_profesor(cuil, next_url=None, return_label="Volver a CEF"):
    params = {}
    if cuil:
        params["cuil"] = cuil
    if next_url:
        params["next"] = next_url
    if return_label:
        params["return_label"] = return_label
    return f"{URL_CARGA_PROFESOR}?{urlencode(params)}" if params else URL_CARGA_PROFESOR


def _url_modal_profesores(cef_context, cuil=""):
    params = {}
    if cef_context.get("cueanexo"):
        params["cueanexo"] = cef_context["cueanexo"]
    if cef_context.get("ciclo"):
        params["ciclo"] = cef_context["ciclo"].pk
    params["abrir_modal_docente"] = "1"
    if cuil:
        params["cuil"] = cuil
    return f"{reverse('cef:profesores')}?{urlencode(params)}"


def _url_profesores(cef_context, vista="actuales"):
    params = {}
    if cef_context.get("cueanexo"):
        params["cueanexo"] = cef_context["cueanexo"]
    if cef_context.get("ciclo"):
        params["ciclo"] = cef_context["ciclo"].pk
    if normalizar_vista_cef(vista) == "historial":
        params["vista"] = "historial"
    querystring = urlencode(params)
    url = reverse("cef:profesores")
    return f"{url}?{querystring}" if querystring else url


def _errores_form(form):
    return " ".join(error for errors in form.errors.values() for error in errors)


def _mensaje_error_asignacion_form(form):
    errores = _errores_form(form)
    if errores:
        return errores

    campos = [
        form.fields[field].label or field
        for field in form.errors
        if field in form.fields
    ]
    if not campos:
        return "Revisá los datos de la asignación al grupo."
    if len(campos) == 1:
        return f"Revisá el campo {campos[0]}."
    return f"Revisá los campos: {', '.join(campos)}."


def _grupo_rotulo(grupo):
    return f"Grupo {grupo.actividad} Nro. {grupo.numero}"


def _grupo_profesores_seguro(grupo_id, cef_context):
    if not cef_context["puede_operar"]:
        return None
    try:
        grupo_id = int(grupo_id)
    except (TypeError, ValueError):
        return None

    return (
        CefGrupo.objects.filter(
            cueanexo=cef_context["cueanexo"],
            ciclo=cef_context["ciclo"],
            pk=grupo_id,
            estado=CefGrupo.Estado.ACTIVO,
        )
        .select_related("actividad", "turno")
        .first()
    )


def _asignar_docente_grupo(request, cef_context):
    form = CefDocenteGrupoForm(request.POST)
    cuil = _solo_digitos(request.POST.get("cuil"))
    grupo = _grupo_profesores_seguro(request.POST.get("grupo_id"), cef_context)
    docente = _buscar_docente(cuil)
    modal_error = ""

    if not cef_context["puede_operar"]:
        modal_error = "Seleccioná un CUE-Anexo y un ciclo lectivo para asignar profesores."
    elif not grupo:
        modal_error = "El grupo seleccionado no pertenece al CEF y ciclo actual."
    elif len(cuil) != 11 or not docente:
        modal_error = "Primero seleccioná un profesor válido por CUIL."
    else:
        form.instance.grupo = grupo
        form.instance.docente_cuil = cuil

    if not modal_error and grupo and len(cuil) == 11 and docente and form.is_valid():
        try:
            banco_pendiente = False
            try:
                asegurar_docente_banco_activo(
                    docente_cuil=cuil,
                    cueanexo=cef_context["cueanexo"],
                    ciclo=cef_context["ciclo"],
                    user=request.user,
                )
            except (OperationalError, ProgrammingError):
                banco_pendiente = True
            asignacion = crear_asignacion_docente_activa(
                grupo=grupo,
                docente_cuil=cuil,
                rol=form.cleaned_data.get("rol"),
                user=request.user,
                fecha_desde=form.cleaned_data.get("fecha_desde"),
                observaciones=form.cleaned_data.get("observaciones") or "",
            )
            if banco_pendiente and not _is_ajax(request):
                messages.warning(request, MSG_BANCO_DOCENTES_PENDIENTE)
            ajax_message = f"Profesor asignado como {asignacion.get_rol_display().lower()}."
            if _is_ajax(request):
                return None, form, grupo, cuil, modal_error, ajax_message
            messages.success(request, "Profesor asociado correctamente al grupo.")
            return redirect(_url_profesores(cef_context)), form, grupo, cuil, modal_error, ""
        except ValidationError as exc:
            modal_error = "; ".join(exc.messages)
        except IntegrityError:
            modal_error = "No se pudo asociar el profesor. Verificá que no exista ya activo en ese grupo o rol."
    elif not modal_error and grupo and len(cuil) == 11 and docente:
        modal_error = _mensaje_error_asignacion_form(form)

    return None, form, grupo, cuil, modal_error, ""


def _asignar_docente_grupo_desde_historial(request, cef_context):
    form = CefDocenteGrupoForm(request.POST)
    try:
        periodo_id = int(request.POST.get("periodo_historico_id") or "")
    except (TypeError, ValueError):
        periodo_id = None

    periodo = (
        CefDocenteCef.objects.filter(
            pk=periodo_id,
            cueanexo=cef_context["cueanexo"],
        ).first()
        if periodo_id
        else None
    )
    cuil = periodo.docente_cuil if periodo else ""
    grupo = _grupo_profesores_seguro(request.POST.get("grupo_id"), cef_context)
    docente = _buscar_docente(cuil) if cuil else None
    modal_error = ""

    if not cef_context["puede_operar"]:
        modal_error = "El ciclo está cerrado. La información se encuentra en modo sólo lectura."
    elif not periodo:
        modal_error = "El período histórico seleccionado no pertenece a este CEF."
    elif not CefDocenteCef.objects.filter(
        cueanexo=cef_context["cueanexo"],
        ciclo=cef_context["ciclo"],
        docente_cuil=cuil,
        estado=CefDocenteCef.Estado.ACTIVO,
    ).exists():
        modal_error = "El profesor debe reincorporarse primero al CEF."
    elif not grupo:
        modal_error = "El grupo seleccionado no pertenece al CEF y ciclo actual."
    elif len(cuil) != 11 or not docente:
        modal_error = "El profesor seleccionado no es válido."
    else:
        form.instance.grupo = grupo
        form.instance.docente_cuil = cuil

    if not modal_error and grupo and docente and form.is_valid():
        try:
            asignacion = crear_asignacion_docente_activa(
                grupo=grupo,
                docente_cuil=cuil,
                rol=form.cleaned_data.get("rol"),
                user=request.user,
                fecha_desde=form.cleaned_data.get("fecha_desde"),
                observaciones=form.cleaned_data.get("observaciones") or "",
            )
            mensaje = f"Profesor asignado como {asignacion.get_rol_display().lower()}."
            if _is_ajax(request):
                return None, form, grupo, cuil, modal_error, mensaje
            messages.success(request, "Profesor asociado correctamente al grupo actual.")
            return (
                redirect(_url_profesores(cef_context, "historial")),
                form,
                grupo,
                cuil,
                modal_error,
                "",
            )
        except ValidationError as exc:
            modal_error = "; ".join(exc.messages)
        except IntegrityError:
            modal_error = (
                "No se pudo crear la asignación. Verificá que no exista ya activo "
                "en ese grupo o rol."
            )
    elif not modal_error and grupo and docente:
        modal_error = _mensaje_error_asignacion_form(form)

    return None, form, grupo, cuil, modal_error, ""


@cef_required
def profesores(request):
    context = contexto_base(request, "profesores", "Profesores CEF")
    perf_start_view(request)
    cef_context = context["cef_context"]
    vista = normalizar_vista_cef(
        request.GET.get("vista") or request.POST.get("vista")
    )
    docente = None
    cuil_buscado = ""
    cuil_error = ""
    docente_en_banco = False
    abrir_modal = request.GET.get("abrir_modal_docente") == "1"
    docente_grupo_form = CefDocenteGrupoForm()
    asignacion_modal_abierto = False
    asignacion_grupo_seleccionado = None
    asignacion_docente_cuil = ""
    asignacion_periodo_historico_id = ""
    asignacion_docente_label = ""
    asignacion_modal_error = ""
    asignacion_ajax_ok = False
    asignacion_ajax_message = ""
    baja_modal_docente = None
    baja_form = CefBajaMotivoForm()

    accion = request.POST.get("accion")
    if (
        request.method == "POST"
        and vista == "historial"
        and accion != "asignar_grupo_historial"
    ):
        message = "Historial es una vista de sólo lectura."
        if _is_ajax(request):
            return JsonResponse({"ok": False, "message": message})
        messages.error(request, message)
        return redirect(_url_profesores(cef_context, "historial"))

    if (
        request.method == "POST"
        and vista != "historial"
        and accion == "asignar_grupo_historial"
    ):
        messages.error(request, "La acción histórica solicitada no es válida.")
        return redirect(_url_profesores(cef_context))

    if request.method == "POST" and not cef_context["puede_operar"]:
        message = (
            "El ciclo está cerrado. La información se encuentra en modo sólo lectura."
            if cef_context["ciclo_cerrado"]
            else "Seleccioná un CUE-Anexo y un ciclo lectivo para gestionar profesores."
        )
        if _is_ajax(request):
            return JsonResponse({"ok": False, "message": message})
        messages.error(request, message)
        return redirect(_url_profesores(cef_context, vista))

    if request.method == "POST" and request.POST.get("accion") == "baja_cef":
        baja_ok, baja_message, baja_modal_docente, baja_form = _dar_baja_docente_cef(
            request,
            cef_context,
        )
        if _is_ajax(request):
            baja_context = {
                "cef_context": cef_context,
                "baja_action_url": _url_profesores(cef_context),
                "baja_modal_docente": None if baja_ok else baja_modal_docente,
                "baja_form": baja_form,
            }
            baja_context.update(_profesores_listado_context(cef_context))
            return JsonResponse(
                {
                    "ok": baja_ok,
                    "message": baja_message,
                    "fragment_selector": "[data-cef-fragment='profesores-banco']",
                    "fragment_html": render_to_string(
                        "cef/profesores_lista_cef.html",
                        baja_context,
                        request=request,
                    ),
                    "modal_html": render_to_string(
                        "cef/profesor_baja_cef_modal.html",
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
        return redirect(_url_profesores(cef_context))

    if request.method == "POST" and accion in {
        "asignar_grupo",
        "asignar_grupo_historial",
    }:
        (
            asignacion_response,
            docente_grupo_form,
            asignacion_grupo_seleccionado,
            asignacion_docente_cuil,
            asignacion_modal_error,
            asignacion_ajax_message,
        ) = (
            _asignar_docente_grupo_desde_historial(request, cef_context)
            if accion == "asignar_grupo_historial"
            else _asignar_docente_grupo(request, cef_context)
        )
        asignacion_periodo_historico_id = request.POST.get(
            "periodo_historico_id",
            "",
        )
        if asignacion_response:
            return asignacion_response
        asignacion_ajax_ok = bool(asignacion_ajax_message)
        asignacion_modal_abierto = not asignacion_ajax_ok
        busqueda_form = CefBusquedaDocenteForm()
    elif request.method == "POST":
        busqueda_form = CefBusquedaDocenteForm(request.POST)
        abrir_modal = True

        if busqueda_form.is_valid():
            cuil_buscado = busqueda_form.cleaned_data["cuil"]
            docente = _buscar_docente(cuil_buscado)
        else:
            cuil_buscado = _solo_digitos(request.POST.get("cuil"))
            cuil_error = _errores_form(busqueda_form)

        if not docente:
            messages.error(request, "Primero buscá un profesor existente por CUIL.")
        elif not cef_context["puede_operar"]:
            messages.error(
                request,
                "Seleccioná un CUE-Anexo y un ciclo lectivo para agregar profesores al banco.",
            )
        else:
            try:
                try:
                    banco, creado = asegurar_docente_banco_activo(
                        docente_cuil=docente.cuil,
                        cueanexo=cef_context["cueanexo"],
                        ciclo=cef_context["ciclo"],
                        user=request.user,
                    )
                    tabla_pendiente = False
                except (OperationalError, ProgrammingError):
                    banco = None
                    creado = False
                    tabla_pendiente = True
                docente_en_banco = bool(banco)

                if tabla_pendiente:
                    messages.error(request, MSG_BANCO_DOCENTES_PENDIENTE)
                elif creado:
                    messages.success(request, "Profesor agregado al banco del CEF.")
                    return redirect(_url_profesores(cef_context))
                else:
                    messages.info(
                        request,
                        "Ese profesor ya está activo en el banco de este CEF y ciclo.",
                    )
            except ValidationError as exc:
                messages.error(request, "; ".join(exc.messages))
            except IntegrityError:
                messages.error(
                    request,
                    "No se pudo agregar el profesor al banco. Verificá que no exista ya activo para este CEF y ciclo.",
                )
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

        if request.GET.get("abrir_modal_asignacion") == "1":
            asignacion_modal_abierto = True
            asignacion_grupo_seleccionado = _grupo_profesores_seguro(
                request.GET.get("grupo_id"),
                cef_context,
            )
            periodo_historico = None
            if vista == "historial":
                try:
                    asignacion_periodo_historico_id = int(
                        request.GET.get("periodo_historico_id") or ""
                    )
                except (TypeError, ValueError):
                    asignacion_periodo_historico_id = ""
                if asignacion_periodo_historico_id:
                    periodo_historico = CefDocenteCef.objects.filter(
                        pk=asignacion_periodo_historico_id,
                        cueanexo=cef_context["cueanexo"],
                    ).first()
                asignacion_docente_cuil = (
                    periodo_historico.docente_cuil if periodo_historico else ""
                )
            else:
                asignacion_docente_cuil = _solo_digitos(request.GET.get("cuil"))
            docente_asignacion = (
                _buscar_docente(asignacion_docente_cuil)
                if asignacion_docente_cuil
                else None
            )

            if not asignacion_grupo_seleccionado:
                asignacion_modal_error = "El grupo seleccionado no pertenece al CEF y ciclo actual."
            elif vista == "historial" and not periodo_historico:
                asignacion_modal_error = "El período histórico seleccionado no pertenece a este CEF."
            elif vista == "historial" and not CefDocenteCef.objects.filter(
                cueanexo=cef_context["cueanexo"],
                ciclo=cef_context["ciclo"],
                docente_cuil=asignacion_docente_cuil,
                estado=CefDocenteCef.Estado.ACTIVO,
            ).exists():
                asignacion_modal_error = "El profesor debe reincorporarse primero al CEF."
            elif len(asignacion_docente_cuil) != 11 or not docente_asignacion:
                asignacion_modal_error = "El profesor seleccionado no es válido."
            else:
                asignacion_docente_label = (
                    f"Profesor: {docente_asignacion.nombre_completo} - "
                    f"CUIL {asignacion_docente_cuil}"
                )

        if request.GET.get("abrir_modal_baja") == "1":
            baja_modal_docente = _docente_baja_modal(
                cef_context,
                request.GET.get("docente_banco_id"),
            )

    if asignacion_docente_cuil and not asignacion_docente_label:
        docente_asignacion = _buscar_docente(asignacion_docente_cuil)
        nombre_asignacion = (
            docente_asignacion.nombre_completo if docente_asignacion else "Profesor"
        )
        asignacion_docente_label = (
            f"Profesor: {nombre_asignacion} - CUIL {asignacion_docente_cuil}"
        )

    next_url = _url_modal_profesores(cef_context, cuil_buscado)
    url_carga_profesor = _url_carga_profesor(cuil_buscado, next_url)
    url_profesores = _url_profesores(cef_context, vista)
    if docente and not docente_en_banco:
        try:
            docente_en_banco = _docente_en_banco_activo(docente, cef_context)
        except (OperationalError, ProgrammingError):
            docente_en_banco = False

    context.update(
        {
            "busqueda_form": busqueda_form,
            "docente": docente,
            "docente_row": _docente_row(docente),
            "docente_en_banco": docente_en_banco,
            "docente_grupo_form": docente_grupo_form,
            "asignacion_modal_abierto": asignacion_modal_abierto,
            "asignacion_grupo_seleccionado": asignacion_grupo_seleccionado,
            "asignacion_docente_cuil": asignacion_docente_cuil,
            "asignacion_periodo_historico_id": asignacion_periodo_historico_id,
            "asignacion_docente_label": asignacion_docente_label,
            "asignacion_modal_error": asignacion_modal_error,
            "asignacion_modal_feedback": asignacion_ajax_message,
            "asignacion_action_url": url_profesores,
            "asignacion_accion": (
                "asignar_grupo_historial"
                if vista == "historial"
                else "asignar_grupo"
            ),
            "baja_action_url": url_profesores,
            "baja_modal_docente": baja_modal_docente,
            "baja_form": baja_form,
            "cuil_buscado": cuil_buscado,
            "cuil_error": cuil_error,
            "url_carga_profesor": url_carga_profesor,
            "url_editar_profesor": url_carga_profesor,
            "modal_docente_abierto": abrir_modal,
            "modal_action_url": _url_modal_profesores(cef_context),
            "modal_tiene_grupo": False,
            "modal_puede_agregar_banco": cef_context["puede_operar"],
            "modal_volver_url": url_profesores,
        }
    )
    if request.method == "POST" and accion in {
        "asignar_grupo",
        "asignar_grupo_historial",
    } and _is_ajax(request):
        context.update(_profesores_listado_context(cef_context, vista))
        return JsonResponse(
            {
                "ok": asignacion_ajax_ok,
                "message": asignacion_ajax_message or asignacion_modal_error,
                "fragment_selector": "[data-cef-fragment='profesores-banco']",
                "fragment_html": render_to_string(
                    (
                        "cef/profesores_historial_lista_cef.html"
                        if vista == "historial"
                        else "cef/profesores_lista_cef.html"
                    ),
                    context,
                    request=request,
                ),
                "modal_html": render_to_string(
                    "cef/asignar_profesor_grupo_modal_cef.html",
                    context,
                    request=request,
                ),
                "close_modal": asignacion_ajax_ok,
            }
        )
    context.update(_profesores_listado_context(cef_context, vista))
    return perf_render(request, "cef/profesores_cef.html", context)


@cef_required
@require_GET
def profesores_fragmento(request):
    cef_context = resolver_contexto_operativo(request)
    vista = normalizar_vista_cef(request.GET.get("vista"))
    context = {
        "cef_context": cef_context,
        "cef_partial": True,
        "asignacion_action_url": _url_profesores(cef_context, vista),
        "asignacion_accion": (
            "asignar_grupo_historial"
            if vista == "historial"
            else "asignar_grupo"
        ),
        "asignacion_periodo_historico_id": "",
        "baja_action_url": _url_profesores(cef_context),
        "baja_modal_docente": (
            _docente_baja_modal(
                cef_context,
                request.GET.get("docente_banco_id"),
            )
            if vista == "actuales" and request.GET.get("abrir_modal_baja") == "1"
            else None
        ),
        "baja_form": CefBajaMotivoForm(),
        "docente_grupo_form": CefDocenteGrupoForm(),
        "modal_action_url": _url_modal_profesores(cef_context),
    }
    context.update(_profesores_listado_context(cef_context, vista))
    return render_fragmento_cef(request, "cef/profesores_seccion_cef.html", context)
