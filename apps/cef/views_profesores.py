# -*- coding: utf-8 -*-

import re
from urllib.parse import urlencode

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.utils import OperationalError, ProgrammingError
from django.shortcuts import redirect, render
from django.urls import reverse

from .forms import CefBusquedaDocenteForm, CefDocenteGrupoForm
from .models import (
    CefDocenteBnh,
    CefDocenteCef,
    CefDocenteGrupo,
    CefGrupo,
    PADRON_DB_ALIAS,
)
from .permisos import cef_required
from .views_contexto import contexto_base


URL_CARGA_PROFESOR = "/bnh/carga-personal/"
MSG_BANCO_DOCENTES_PENDIENTE = (
    "El banco de profesores CEF está pendiente de creación en base de datos."
)


def _solo_digitos(valor):
    return re.sub(r"\D", "", str(valor or ""))


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
        existente = CefDocenteCef.objects.filter(
            cueanexo=cef_context["cueanexo"],
            ciclo=cef_context["ciclo"],
            docente_cuil=docente.cuil,
            estado=CefDocenteCef.Estado.ACTIVO,
        ).first()
        if existente:
            return existente, False, False

        with transaction.atomic():
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


def _asignacion_docente_activa(grupo, cuil):
    return (
        CefDocenteGrupo.objects.filter(
            grupo=grupo,
            docente_cuil=cuil,
            estado=CefDocenteGrupo.Estado.ACTIVO,
        )
        .select_related("grupo", "grupo__actividad")
        .first()
    )


def _asignacion_rol_activa(grupo, rol, cuil):
    if not rol:
        return None

    return (
        CefDocenteGrupo.objects.filter(
            grupo=grupo,
            rol=rol,
            estado=CefDocenteGrupo.Estado.ACTIVO,
        )
        .exclude(docente_cuil=cuil)
        .first()
    )


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

    asignacion_activa = _asignacion_docente_activa(grupo, cuil) if grupo and len(cuil) == 11 else None
    if not modal_error and asignacion_activa:
        modal_error = f"Este profesor ya está asignado a {_grupo_rotulo(grupo)} como {asignacion_activa.get_rol_display()}."
    elif not modal_error and grupo and len(cuil) == 11 and docente and form.is_valid():
        rol_ocupado = _asignacion_rol_activa(
            grupo,
            form.cleaned_data.get("rol"),
            cuil,
        )
        if rol_ocupado:
            modal_error = f"El grupo ya tiene un {rol_ocupado.get_rol_display()} activo."
            return None, form, grupo, cuil, modal_error

        try:
            _, _, banco_pendiente = _asegurar_docente_banco(
                docente,
                cef_context,
                request.user,
            )
            if banco_pendiente:
                messages.warning(request, MSG_BANCO_DOCENTES_PENDIENTE)
        except (IntegrityError, ValidationError):
            messages.warning(
                request,
                "No se pudo actualizar el banco de profesores CEF, pero se continuará con la asignación al grupo.",
            )

        try:
            with transaction.atomic():
                asignacion = form.save(commit=False)
                asignacion.grupo = grupo
                asignacion.docente_cuil = cuil
                asignacion.creado_por = request.user
                asignacion.actualizado_por = request.user
                asignacion.save()
            messages.success(request, "Profesor asociado correctamente al grupo.")
            return redirect(_url_profesores(cef_context)), form, grupo, cuil, modal_error
        except (IntegrityError, ValidationError):
            modal_error = "No se pudo asociar el profesor. Verificá que no exista ya activo en ese grupo o rol."
    elif not modal_error and grupo and len(cuil) == 11 and docente:
        modal_error = _mensaje_error_asignacion_form(form)

    return None, form, grupo, cuil, modal_error


@cef_required
def profesores(request):
    context = contexto_base(request, "profesores", "Profesores CEF")
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
    asignacion_modal_error = ""

    if request.method == "POST" and request.POST.get("accion") == "asignar_grupo":
        (
            asignacion_response,
            docente_grupo_form,
            asignacion_grupo_seleccionado,
            asignacion_docente_cuil,
            asignacion_modal_error,
        ) = _asignar_docente_grupo(request, cef_context)
        if asignacion_response:
            return asignacion_response
        asignacion_modal_abierto = True
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
            except (IntegrityError, ValidationError):
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

    next_url = _url_modal_profesores(cef_context, cuil_buscado)
    url_carga_profesor = _url_carga_profesor(cuil_buscado, next_url)
    url_profesores = _url_profesores(cef_context)
    docentes_banco_tabla_pendiente = False

    try:
        docentes = list(_docentes_cef(cef_context))
        if docente and not docente_en_banco:
            docente_en_banco = _docente_en_banco_activo(docente, cef_context)
    except (OperationalError, ProgrammingError):
        docentes = []
        docentes_banco_tabla_pendiente = True

    try:
        asignaciones_por_docente = _asignaciones_por_docente(cef_context, docentes)
    except (OperationalError, ProgrammingError):
        asignaciones_por_docente = {}

    grupos_disponibles = list(_grupos_disponibles(cef_context))

    for item in docentes:
        item.asignaciones_grupo = asignaciones_por_docente.get(item.docente_cuil, [])
        asignaciones_activas = [
            asignacion
            for asignacion in item.asignaciones_grupo
            if asignacion.estado == CefDocenteGrupo.Estado.ACTIVO
        ]
        grupos_activos_ids = {asignacion.grupo_id for asignacion in asignaciones_activas}
        item.grupos_asignables = [
            grupo for grupo in grupos_disponibles if grupo.pk not in grupos_activos_ids
        ]
        item.grupos_bloqueados = asignaciones_activas
        item.url_editar_profesor = _url_carga_profesor(
            item.docente_cuil,
            url_profesores,
            "Volver a Profesores CEF",
        )

    context.update(
        {
            "busqueda_form": busqueda_form,
            "docente": docente,
            "docente_row": _docente_row(docente),
            "docentes": docentes,
            "grupos_disponibles": grupos_disponibles,
            "docentes_banco_tabla_pendiente": docentes_banco_tabla_pendiente,
            "docente_en_banco": docente_en_banco,
            "docente_grupo_form": docente_grupo_form,
            "asignacion_modal_abierto": asignacion_modal_abierto,
            "asignacion_grupo_seleccionado": asignacion_grupo_seleccionado,
            "asignacion_docente_cuil": asignacion_docente_cuil,
            "asignacion_modal_error": asignacion_modal_error,
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
    return render(request, "cef/profesores_cef.html", context)
