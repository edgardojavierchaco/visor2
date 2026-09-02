# -*- coding: utf-8 -*-

import re
from urllib.parse import urlencode

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.utils import OperationalError, ProgrammingError
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.urls import reverse

from .forms import CefBajaMotivoForm, CefBusquedaDocenteForm, CefDocenteGrupoForm
from .models import (
    CefDocenteBnh,
    CefDocenteGrupo,
    CefGrupo,
    PADRON_DB_ALIAS,
    docentes_grupo_tiene_duplicados_activos,
    validar_docente_grupo_activo,
)
from .permisos import cef_required
from .services import (
    asegurar_docente_banco_activo,
    crear_asignacion_docente_activa,
    dar_baja_asignacion_docente,
    reasignar_docente_grupo,
    validar_ciclo_escribible,
)
from .views_contexto import (
    contexto_base,
    normalizar_vista_cef,
    redirect_con_contexto,
    resolver_origen_gestion_grupo,
)
from .views_profesores import (
    MSG_BANCO_DOCENTES_PENDIENTE,
    _docente_row,
    _url_carga_profesor,
)


def _solo_digitos(valor):
    return re.sub(r"\D", "", str(valor or ""))


def _is_ajax(request):
    return request.headers.get("x-requested-with") == "XMLHttpRequest"


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


def _grupo_rotulo(grupo):
    return f"Grupo {grupo.actividad} Nro. {grupo.numero}"


def _asignacion_docente_activa(grupo, cuil):
    if not cuil:
        return None

    return (
        CefDocenteGrupo.objects.filter(
            grupo=grupo,
            docente_cuil=cuil,
            estado=CefDocenteGrupo.Estado.ACTIVO,
        )
        .first()
    )


def _docentes_grupo(grupo):
    return (
        CefDocenteGrupo.objects.filter(grupo=grupo)
        .order_by("estado", "rol", "docente_nombre_snapshot", "docente_cuil")
    )


def _buscar_docente(cuil):
    return (
        CefDocenteBnh.objects.using(PADRON_DB_ALIAS)
        .filter(cuil=cuil)
        .first()
    )


def _url_modal_grupo(
    grupo,
    cef_context,
    cuil="",
    origen="grupos",
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
    if destino == "gestionar":
        params["origen"] = resolver_origen_gestion_grupo(origen)
        params["destino"] = "gestionar"
        params["vista_alumnos"] = normalizar_vista_cef(vista_alumnos)
        params["vista_docentes"] = normalizar_vista_cef(vista_docentes)
    params["abrir_modal_docente"] = "1"
    if cuil:
        params["cuil"] = cuil
    return f"{reverse('cef:docentes_grupo', kwargs={'grupo_id': grupo.pk})}?{urlencode(params)}"


def _url_docentes_grupo(grupo, cef_context):
    params = {}
    if cef_context.get("cueanexo"):
        params["cueanexo"] = cef_context["cueanexo"]
    if cef_context.get("ciclo"):
        params["ciclo"] = cef_context["ciclo"].pk
    querystring = urlencode(params)
    url = reverse("cef:docentes_grupo", kwargs={"grupo_id": grupo.pk})
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


def _ajax_docentes_grupo_response(request, context, ok, message):
    docentes = list(context.get("docentes") or [])
    context["docentes"] = docentes
    context["roles_docente"] = CefDocenteGrupo.Rol.choices
    context["docentes_activos_count"] = len(
        [
            docente
            for docente in docentes
            if docente.estado == CefDocenteGrupo.Estado.ACTIVO
        ]
    )
    if context.get("grupo"):
        context["docentes_activos_duplicados"] = docentes_grupo_tiene_duplicados_activos(
            context["grupo"]
        )
    return JsonResponse(
        {
            "ok": ok,
            "message": message,
            "modal_html": render_to_string(
                "cef/modal_busqueda_docente_cef.html",
                context,
                request=request,
            ),
            "fragment_selector": "[data-cef-fragment='docentes-grupo']",
            "fragment_html": render_to_string(
                "cef/docentes_grupo_lista_cef.html",
                context,
                request=request,
            ),
            "close_modal": ok,
        }
    )


def _baja_docente(request, grupo, cef_context):
    baja_form = CefBajaMotivoForm(request.POST)
    if not baja_form.is_valid():
        ok = False
        message = _errores_form(baja_form)
        if _is_ajax(request):
            context = {
                "cef_context": cef_context,
                "grupo": grupo,
                "docentes": _docentes_grupo(grupo),
            }
            return _ajax_docentes_grupo_response(request, context, ok, message)
        messages.error(request, message)
        return redirect(
            redirect_con_contexto(
                "cef:docentes_grupo",
                cef_context,
                grupo_id=grupo.pk,
            )
        )

    try:
        docente_grupo_id = int(request.POST.get("docente_grupo_id"))
    except (TypeError, ValueError):
        messages.error(request, "La asignación seleccionada no es válida.")
        return redirect(
            redirect_con_contexto(
                "cef:docentes_grupo",
                cef_context,
                grupo_id=grupo.pk,
            )
        )

    asignacion = get_object_or_404(
        CefDocenteGrupo.objects.filter(
            grupo=grupo,
            estado=CefDocenteGrupo.Estado.ACTIVO,
        ),
        pk=docente_grupo_id,
    )
    try:
        dar_baja_asignacion_docente(
            asignacion,
            request.user,
            baja_form.cleaned_data["motivo_baja"],
        )
        ok = True
        message = "Profesor dado de baja del grupo correctamente."
    except ValidationError as exc:
        ok = False
        message = "; ".join(exc.messages)

    if _is_ajax(request):
        context = {
            "cef_context": cef_context,
            "grupo": grupo,
            "docentes": _docentes_grupo(grupo),
        }
        return _ajax_docentes_grupo_response(request, context, ok, message)

    if ok:
        messages.success(request, message)
    else:
        messages.error(request, message)
    return redirect(
        redirect_con_contexto(
            "cef:docentes_grupo",
            cef_context,
            grupo_id=grupo.pk,
        )
    )


def _alta_docente(request, grupo, cef_context):
    try:
        docente_grupo_id = int(request.POST.get("docente_grupo_id"))
    except (TypeError, ValueError):
        messages.error(request, "La asignación seleccionada no es válida.")
        return redirect(
            redirect_con_contexto(
                "cef:docentes_grupo",
                cef_context,
                grupo_id=grupo.pk,
            )
        )

    asignacion = get_object_or_404(
        CefDocenteGrupo.objects.filter(grupo=grupo),
        pk=docente_grupo_id,
    )
    rol = request.POST.get("rol")
    roles_validos = {valor for valor, _ in CefDocenteGrupo.Rol.choices}
    if rol not in roles_validos:
        ok = False
        message = "Seleccioná si el profesor será titular o suplente."
    else:
        try:
            reasignar_docente_grupo(asignacion, request.user, rol=rol)
            ok = True
            message = "Profesor reasignado al grupo correctamente."
        except ValidationError as exc:
            ok = False
            message = "; ".join(exc.messages)

    if _is_ajax(request):
        context = {
            "cef_context": cef_context,
            "grupo": grupo,
            "docentes": _docentes_grupo(grupo),
        }
        return _ajax_docentes_grupo_response(request, context, ok, message)

    if ok:
        messages.success(request, message)
    else:
        messages.error(request, message)
    return redirect(
        redirect_con_contexto(
            "cef:docentes_grupo",
            cef_context,
            grupo_id=grupo.pk,
        )
    )


@cef_required
def docentes_grupo(request, grupo_id):
    context = contexto_base(request, "grupos", "Profesores del Grupo CEF")
    cef_context = context["cef_context"]
    destino_gestionar = (
        request.GET.get("destino") or request.POST.get("destino")
    ) == "gestionar"
    origen = resolver_origen_gestion_grupo(
        request.GET.get("origen") or request.POST.get("origen")
    )
    vista_alumnos = normalizar_vista_cef(
        request.GET.get("vista_alumnos") or request.POST.get("vista_alumnos")
    )
    vista_docentes = normalizar_vista_cef(
        request.GET.get("vista_docentes") or request.POST.get("vista_docentes")
    )

    if not cef_context["puede_consultar"]:
        messages.warning(
            request,
            "Selecciona un CUE-Anexo y un ciclo lectivo para administrar profesores.",
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
    gestionar_grupo_url = _url_gestionar_grupo(
        grupo,
        cef_context,
        origen,
        "profesores-curso",
        vista_alumnos=vista_alumnos,
        vista_docentes=vista_docentes,
    )
    docente = None
    cuil_buscado = ""
    cuil_error = ""
    docente_form = CefDocenteGrupoForm()
    abrir_modal = request.GET.get("abrir_modal_docente") == "1"
    ajax_ok = False
    ajax_message = ""

    if request.method == "POST" and request.POST.get("accion") == "baja":
        return _baja_docente(request, grupo, cef_context)
    if request.method == "POST" and request.POST.get("accion") == "alta":
        return _alta_docente(request, grupo, cef_context)

    if request.method == "POST":
        busqueda_form = CefBusquedaDocenteForm(request.POST)
        docente_form = CefDocenteGrupoForm(request.POST)
        abrir_modal = True

        if busqueda_form.is_valid():
            cuil_buscado = busqueda_form.cleaned_data["cuil"]
            docente = _buscar_docente(cuil_buscado)
        else:
            cuil_buscado = _solo_digitos(request.POST.get("cuil"))
            cuil_error = _errores_form(busqueda_form)

        if not docente:
            ajax_message = "Primero busca un profesor existente por CUIL."
            if not _is_ajax(request):
                messages.error(request, ajax_message)
        else:
            docente_form.instance.grupo = grupo
            docente_form.instance.docente_cuil = cuil_buscado

            if docente_form.is_valid():
                rol = docente_form.cleaned_data.get("rol")
                try:
                    banco_pendiente = False
                    try:
                        asegurar_docente_banco_activo(
                            docente_cuil=cuil_buscado,
                            cueanexo=cef_context["cueanexo"],
                            ciclo=cef_context["ciclo"],
                            user=request.user,
                        )
                    except (OperationalError, ProgrammingError):
                        banco_pendiente = True
                    asignacion = crear_asignacion_docente_activa(
                        grupo=grupo,
                        docente_cuil=cuil_buscado,
                        rol=rol,
                        user=request.user,
                        fecha_desde=docente_form.cleaned_data.get("fecha_desde"),
                        observaciones=(
                            docente_form.cleaned_data.get("observaciones") or ""
                        )
                    )
                    if banco_pendiente and not _is_ajax(request):
                        messages.warning(request, MSG_BANCO_DOCENTES_PENDIENTE)
                    if _is_ajax(request):
                        ajax_ok = True
                        ajax_message = f"Profesor asignado como {asignacion.get_rol_display().lower()}."
                    else:
                        messages.success(request, "Profesor asociado correctamente.")
                        return redirect(
                            gestionar_grupo_url
                            if destino_gestionar
                            else redirect_con_contexto(
                                "cef:docentes_grupo",
                                cef_context,
                                grupo_id=grupo.pk,
                            )
                        )
                except ValidationError as exc:
                    ajax_message = "; ".join(exc.messages)
                    if not _is_ajax(request):
                        messages.error(request, ajax_message)
                except IntegrityError:
                    ajax_message = "No se pudo asociar el profesor. Verifica que no exista ya un titular o suplente activo para este grupo."
                    if not _is_ajax(request):
                        messages.error(request, ajax_message)
            else:
                ajax_message = _errores_form(docente_form) or "Revisá los datos de la asignación al grupo."
                if not _is_ajax(request):
                    messages.error(request, ajax_message)
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
            "grupo_rotulo": _grupo_rotulo(grupo),
            "grupo_dias_texto": _dias_texto(grupo),
            "docentes": _docentes_grupo(grupo),
            "docentes_activos_count": len(
                [
                    item
                    for item in _docentes_grupo(grupo)
                    if item.estado == CefDocenteGrupo.Estado.ACTIVO
                ]
            ),
            "docentes_activos_duplicados": docentes_grupo_tiene_duplicados_activos(grupo),
            "roles_docente": CefDocenteGrupo.Rol.choices,
            "busqueda_form": busqueda_form,
            "docente_form": docente_form,
            "docente": docente,
            "docente_row": _docente_row(docente),
            "docente_asignacion_activa": (
                _asignacion_docente_activa(grupo, cuil_buscado)
                if docente and len(cuil_buscado) == 11
                else None
            ),
            "cuil_buscado": cuil_buscado,
            "cuil_error": cuil_error,
            "url_carga_profesor": _url_carga_profesor(cuil_buscado, next_url),
            "url_editar_profesor": _url_carga_profesor(cuil_buscado, next_url),
            "modal_docente_abierto": abrir_modal,
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
                else _url_docentes_grupo(grupo, cef_context)
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
                "cef/modal_busqueda_docente_cef.html",
                context,
            )
        return _ajax_docentes_grupo_response(request, context, ajax_ok, ajax_message)
    if request.method == "POST" and destino_gestionar:
        return redirect(gestionar_grupo_url)
    return render(request, "cef/docentes_grupo_cef.html", context)


@cef_required
def editar_docente_grupo(request, grupo_id, docente_grupo_id):
    context = contexto_base(request, "grupos", "Editar profesor del grupo CEF")
    cef_context = context["cef_context"]

    if not cef_context["puede_operar"]:
        messages.warning(
            request,
            "El ciclo está cerrado. La información se encuentra en modo sólo lectura."
            if cef_context["ciclo_cerrado"]
            else "Selecciona un CUE-Anexo y un ciclo lectivo para administrar profesores.",
        )
        return redirect(redirect_con_contexto("cef:carga_grupo", cef_context))

    grupo = _grupo_seguro(grupo_id, cef_context)
    volver_gestionar = (
        request.GET.get("volver") == "gestionar"
        or request.POST.get("volver") == "gestionar"
    )
    origen = resolver_origen_gestion_grupo(
        request.GET.get("origen") or request.POST.get("origen")
    )
    vista_alumnos = normalizar_vista_cef(
        request.GET.get("vista_alumnos") or request.POST.get("vista_alumnos")
    )
    vista_docentes = normalizar_vista_cef(
        request.GET.get("vista_docentes") or request.POST.get("vista_docentes")
    )
    volver_url = (
        _url_gestionar_grupo(
            grupo,
            cef_context,
            origen,
            "profesores-curso",
            vista_alumnos=vista_alumnos,
            vista_docentes=vista_docentes,
        )
        if volver_gestionar
        else _url_docentes_grupo(grupo, cef_context)
    )
    volver_label = (
        "Volver a Gestionar grupo"
        if volver_gestionar
        else "Volver a profesores"
    )
    if grupo.estado != CefGrupo.Estado.ACTIVO:
        messages.error(request, "El grupo está dado de baja y no puede editarse.")
        return redirect(volver_url)
    asignacion = get_object_or_404(
        CefDocenteGrupo.objects.filter(grupo=grupo),
        pk=docente_grupo_id,
    )
    docente_cuil = asignacion.docente_cuil

    if request.method == "POST":
        form = CefDocenteGrupoForm(request.POST, instance=asignacion)
        form.instance.grupo = grupo
        form.instance.docente_cuil = docente_cuil

        if form.is_valid():
            try:
                if asignacion.estado == CefDocenteGrupo.Estado.ACTIVO:
                    validar_docente_grupo_activo(
                        grupo,
                        docente_cuil,
                        form.cleaned_data.get("rol"),
                        excluir_pk=asignacion.pk,
                    )
                try:
                    with transaction.atomic():
                        if asignacion.estado == CefDocenteGrupo.Estado.ACTIVO:
                            docente = _buscar_docente(docente_cuil)
                            if not docente:
                                raise ValidationError("El profesor seleccionado no es válido.")
                            try:
                                asegurar_docente_banco_activo(
                                    docente_cuil=docente_cuil,
                                    cueanexo=cef_context["cueanexo"],
                                    ciclo=cef_context["ciclo"],
                                    user=request.user,
                                )
                            except (OperationalError, ProgrammingError):
                                pass
                        asignacion = form.save(commit=False)
                        asignacion.grupo = grupo
                        asignacion.docente_cuil = docente_cuil
                        asignacion.actualizado_por = request.user
                        validar_ciclo_escribible(grupo.ciclo_id)
                        asignacion.save()
                    messages.success(request, "Asignación del profesor actualizada correctamente.")
                    return redirect(volver_url)
                except ValidationError as exc:
                    messages.error(request, "; ".join(exc.messages))
                except IntegrityError:
                    messages.error(
                        request,
                        "No se pudo actualizar la asignación. Verifica que no exista ya un titular, suplente o profesor activo duplicado para este grupo.",
                    )
            except ValidationError as exc:
                messages.error(request, "; ".join(exc.messages))
        else:
            messages.error(
                request,
                _errores_form(form) or "Revisá los datos de la asignación.",
            )
    else:
        form = CefDocenteGrupoForm(instance=asignacion)

    context.update(
        {
            "grupo": grupo,
            "grupo_rotulo": _grupo_rotulo(grupo),
            "grupo_dias_texto": _dias_texto(grupo),
            "asignacion": asignacion,
            "form": form,
            "volver_url": volver_url,
            "volver_label": volver_label,
            "volver_gestionar": volver_gestionar,
            "origen": origen,
            "vista_alumnos": vista_alumnos,
            "vista_docentes": vista_docentes,
        }
    )
    return render(request, "cef/docente_grupo_form_cef.html", context)
