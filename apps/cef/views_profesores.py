# -*- coding: utf-8 -*-

import re
from urllib.parse import urlencode

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.utils import OperationalError, ProgrammingError
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_GET

from .forms import CefBusquedaDocenteForm, CefDocenteGrupoForm
from .models import (
    CefDocenteBnh,
    CefDocenteCef,
    CefDocenteGrupo,
    CefGrupo,
    PADRON_DB_ALIAS,
    validar_docente_grupo_activo,
)
from .permisos import cef_required
from .performance import perf_render, perf_start_view
from .views_contexto import (
    contexto_base,
    render_fragmento_cef,
    resolver_contexto_operativo,
)


URL_CARGA_PROFESOR = "/bnh/carga-personal/"
MSG_BANCO_DOCENTES_PENDIENTE = (
    "El banco de profesores CEF está pendiente de creación en base de datos."
)
MSG_DOCENTE_CEF_NO_ACTIVO = (
    "Este profesor no se encuentra activo en el banco de profesores "
    "de este CEF y ciclo."
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
    if not cef_context["puede_operar"]:
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
        )
        .select_related("actividad", "turno")
        .order_by("actividad__nombre", "numero", "nombre")
    )


def _profesores_listado_context(cef_context):
    docentes_banco_tabla_pendiente = False
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
    url_profesores = _url_profesores(cef_context)

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
        "docentes": docentes,
        "grupos_disponibles": grupos_disponibles,
        "docentes_banco_tabla_pendiente": docentes_banco_tabla_pendiente,
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


def _asegurar_docente_banco(docente, cef_context, user):
    if not docente or not cef_context["puede_operar"]:
        return None, False, False

    try:
        with transaction.atomic():
            existentes = list(
                CefDocenteCef.objects.select_for_update()
                .filter(
                    cueanexo=cef_context["cueanexo"],
                    ciclo=cef_context["ciclo"],
                    docente_cuil=docente.cuil,
                )
                .order_by("-pk")
            )
            existente_activo = next(
                (
                    item
                    for item in existentes
                    if item.estado == CefDocenteCef.Estado.ACTIVO
                ),
                None,
            )
            if existente_activo:
                return existente_activo, False, False
            if existentes:
                raise ValidationError(MSG_DOCENTE_CEF_NO_ACTIVO)

            banco = CefDocenteCef.objects.create(
                cueanexo=cef_context["cueanexo"],
                ciclo=cef_context["ciclo"],
                docente_cuil=docente.cuil,
                estado=CefDocenteCef.Estado.ACTIVO,
                creado_por=user,
                actualizado_por=user,
            )
        return banco, True, False
    except (OperationalError, ProgrammingError):
        return None, False, True


def _docente_cef_seguro(docente_banco_id, cef_context, bloquear=False):
    try:
        docente_banco_id = int(docente_banco_id)
    except (TypeError, ValueError):
        raise Http404("El profesor seleccionado no es válido.")

    queryset = CefDocenteCef.objects.filter(
        cueanexo=cef_context["cueanexo"],
        ciclo=cef_context["ciclo"],
    )
    if bloquear:
        queryset = queryset.select_for_update()
    return get_object_or_404(queryset, pk=docente_banco_id)


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
    with transaction.atomic():
        docente_banco = _docente_cef_seguro(
            request.POST.get("docente_banco_id"),
            cef_context,
            bloquear=True,
        )
        docente_banco = _preparar_docente_baja(docente_banco, cef_context)

        if docente_banco.estado != CefDocenteCef.Estado.ACTIVO:
            return (
                False,
                "El profesor ya no se encuentra activo en este CEF y ciclo.",
                docente_banco,
            )
        if docente_banco.asignaciones_activas:
            return (
                False,
                "No se puede dar de baja al profesor del CEF porque posee asignaciones activas.",
                docente_banco,
            )

        docente_banco.estado = CefDocenteCef.Estado.BAJA
        docente_banco.fecha_baja = timezone.localdate()
        docente_banco.actualizado_por = request.user
        docente_banco.save(
            update_fields=[
                "estado",
                "fecha_baja",
                "actualizado_por",
                "actualizado_en",
            ]
        )

    return True, "Profesor dado de baja del CEF correctamente.", docente_banco


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


def _url_profesores(cef_context):
    params = {}
    if cef_context.get("cueanexo"):
        params["cueanexo"] = cef_context["cueanexo"]
    if cef_context.get("ciclo"):
        params["ciclo"] = cef_context["ciclo"].pk
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
        if form.cleaned_data.get("estado") == CefDocenteGrupo.Estado.ACTIVO:
            try:
                validar_docente_grupo_activo(
                    grupo,
                    cuil,
                    form.cleaned_data.get("rol"),
                )
            except ValidationError as exc:
                modal_error = "; ".join(exc.messages)
                return None, form, grupo, cuil, modal_error, ""
        try:
            with transaction.atomic():
                _, _, banco_pendiente = _asegurar_docente_banco(
                    docente,
                    cef_context,
                    request.user,
                )
                asignacion = form.save(commit=False)
                asignacion.grupo = grupo
                asignacion.docente_cuil = cuil
                asignacion.creado_por = request.user
                asignacion.actualizado_por = request.user
                asignacion.save()
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


@cef_required
def profesores(request):
    context = contexto_base(request, "profesores", "Profesores CEF")
    perf_start_view(request)
    cef_context = context["cef_context"]
    docente = None
    cuil_buscado = ""
    cuil_error = ""
    docente_en_banco = False
    abrir_modal = request.GET.get("abrir_modal_docente") == "1"
    docente_grupo_form = CefDocenteGrupoForm()
    asignacion_modal_abierto = False
    asignacion_grupo_seleccionado = None
    asignacion_docente_cuil = ""
    asignacion_docente_label = ""
    asignacion_modal_error = ""
    asignacion_ajax_ok = False
    asignacion_ajax_message = ""
    baja_modal_docente = None

    if request.method == "POST" and request.POST.get("accion") == "baja_cef":
        baja_ok, baja_message, baja_modal_docente = _dar_baja_docente_cef(
            request,
            cef_context,
        )
        if _is_ajax(request):
            baja_context = {
                "cef_context": cef_context,
                "baja_action_url": _url_profesores(cef_context),
                "baja_modal_docente": None if baja_ok else baja_modal_docente,
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

    if request.method == "POST" and request.POST.get("accion") == "asignar_grupo":
        (
            asignacion_response,
            docente_grupo_form,
            asignacion_grupo_seleccionado,
            asignacion_docente_cuil,
            asignacion_modal_error,
            asignacion_ajax_message,
        ) = _asignar_docente_grupo(request, cef_context)
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
                banco, creado, tabla_pendiente = _asegurar_docente_banco(
                    docente,
                    cef_context,
                    request.user,
                )
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
            asignacion_docente_cuil = _solo_digitos(request.GET.get("cuil"))
            docente_asignacion = _buscar_docente(asignacion_docente_cuil)

            if not asignacion_grupo_seleccionado:
                asignacion_modal_error = "El grupo seleccionado no pertenece al CEF y ciclo actual."
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
    url_profesores = _url_profesores(cef_context)
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
            "asignacion_docente_label": asignacion_docente_label,
            "asignacion_modal_error": asignacion_modal_error,
            "asignacion_modal_feedback": asignacion_ajax_message,
            "asignacion_action_url": url_profesores,
            "baja_action_url": url_profesores,
            "baja_modal_docente": baja_modal_docente,
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
    if request.method == "POST" and request.POST.get("accion") == "asignar_grupo" and _is_ajax(request):
        context.update(_profesores_listado_context(cef_context))
        return JsonResponse(
            {
                "ok": asignacion_ajax_ok,
                "message": asignacion_ajax_message or asignacion_modal_error,
                "fragment_selector": "[data-cef-fragment='profesores-banco']",
                "fragment_html": render_to_string(
                    "cef/profesores_lista_cef.html",
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
    context.update(_profesores_listado_context(cef_context))
    return perf_render(request, "cef/profesores_cef.html", context)


@cef_required
@require_GET
def profesores_fragmento(request):
    cef_context = resolver_contexto_operativo(request)
    context = {
        "cef_context": cef_context,
        "cef_partial": True,
        "asignacion_action_url": _url_profesores(cef_context),
        "baja_action_url": _url_profesores(cef_context),
        "baja_modal_docente": (
            _docente_baja_modal(
                cef_context,
                request.GET.get("docente_banco_id"),
            )
            if request.GET.get("abrir_modal_baja") == "1"
            else None
        ),
        "docente_grupo_form": CefDocenteGrupoForm(),
        "modal_action_url": _url_modal_profesores(cef_context),
    }
    context.update(_profesores_listado_context(cef_context))
    return render_fragmento_cef(request, "cef/profesores_seccion_cef.html", context)
