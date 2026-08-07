# -*- coding: utf-8 -*-

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Count, Max, Prefetch, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.views.decorators.http import require_GET

from .forms import (
    CefBajaMotivoForm,
    CefDocenteGrupoForm,
    CefGrupoDiasForm,
    CefGrupoForm,
)
from .models import (
    CefAlumnoCef,
    CefDocenteGrupo,
    CefGrupo,
    CefGrupoDiaFuncionamiento,
    CefInscripcion,
    docentes_grupo_tiene_duplicados_activos,
)
from .permisos import cef_required
from .performance import perf_render, perf_start_view
from .services import (
    dar_baja_asignacion_docente,
    dar_baja_grupo,
    dar_baja_inscripcion,
    reactivar_grupo as reactivar_grupo_servicio,
    reasignar_docente_grupo,
    reinscribir_alumno,
    validar_ciclo_escribible,
    validar_conflictos_horarios_edicion_grupo,
)
from .views_contexto import (
    contexto_base,
    normalizar_vista_cef,
    redirect_con_contexto,
    render_fragmento_cef,
    resolver_contexto_operativo,
    resolver_origen_gestion_grupo,
)
from .views_docentes_grupo import _url_modal_grupo as _url_modal_docente_grupo
from .views_inscripcion_grupo import _url_modal_grupo as _url_modal_inscripcion_grupo


def _grupos_queryset(cef_context):
    return (
        CefGrupo.objects.filter(
            cueanexo=cef_context["cueanexo"],
            ciclo=cef_context["ciclo"],
        )
        .select_related(
            "actividad",
            "nivel",
            "rango_etario",
            "turno",
            "codigo_ra_override",
        )
        .prefetch_related(
            Prefetch(
                "dias_funcionamiento",
                queryset=CefGrupoDiaFuncionamiento.objects.select_related(
                    "dia_semana"
                ),
            )
        )
        .annotate(
            alumnos_activos=Count(
                "inscripciones",
                filter=Q(inscripciones__estado="activo"),
                distinct=True,
            ),
            docentes_activos=Count(
                "docentes",
                filter=Q(docentes__estado="activo"),
                distinct=True,
            )
        )
        .order_by("actividad__nombre", "numero", "nombre")
    )


def _grupos_historial_queryset(cef_context):
    if not cef_context["puede_consultar"]:
        return CefGrupo.objects.none()
    return (
        CefGrupo.objects.filter(
            cueanexo=cef_context["cueanexo"],
            ciclo__anio__lt=cef_context["ciclo"].anio,
        )
        .select_related("ciclo", "actividad", "nivel", "rango_etario", "turno")
        .prefetch_related(
            Prefetch(
                "dias_funcionamiento",
                queryset=CefGrupoDiaFuncionamiento.objects.select_related(
                    "dia_semana"
                ),
            )
        )
        .order_by("-ciclo__anio", "actividad__nombre", "numero", "nombre")
    )


def _grupo_seguro(grupo_id, cef_context):
    return get_object_or_404(
        CefGrupo.objects.filter(
            cueanexo=cef_context["cueanexo"],
            ciclo=cef_context["ciclo"],
        )
        .select_related("ciclo", "actividad", "turno", "nivel", "rango_etario")
        .prefetch_related("dias_funcionamiento__dia_semana"),
        pk=grupo_id,
    )


def _grupo_historico_seguro(grupo_id, cef_context):
    return get_object_or_404(
        CefGrupo.objects.filter(
            cueanexo=cef_context["cueanexo"],
            ciclo__anio__lt=cef_context["ciclo"].anio,
        )
        .select_related("ciclo", "actividad", "turno", "nivel", "rango_etario")
        .prefetch_related(
            "dias_funcionamiento__dia_semana",
            "movimientos_estado",
        ),
        pk=grupo_id,
    )


def _dias_texto(grupo):
    return ", ".join(
        str(item.dia_semana) for item in grupo.dias_funcionamiento.all()
    )


def _inscripciones_grupo(grupo):
    return (
        CefInscripcion.objects.filter(grupo=grupo)
        .select_related("alumno", "alumno__sexo")
        .order_by("estado", "alumno__apellidos", "alumno__nombres")
    )


def _docentes_grupo(grupo):
    return (
        CefDocenteGrupo.objects.filter(grupo=grupo)
        .order_by("estado", "rol", "docente_nombre_snapshot", "docente_cuil")
    )


def _docente_activo_por_rol(docentes, rol):
    return next(
        (
            docente
            for docente in docentes
            if docente.rol == rol and docente.estado == CefDocenteGrupo.Estado.ACTIVO
        ),
        None,
    )


def _url_gestionar_grupo(
    grupo,
    cef_context,
    origen="grupos",
    ancla="",
    *,
    modo_historial=False,
    vista_alumnos="actuales",
    vista_docentes="actuales",
):
    url = redirect_con_contexto(
        "cef:gestionar_grupo",
        cef_context,
        grupo_id=grupo.pk,
    )
    separador = "&" if "?" in url else "?"
    url = f"{url}{separador}origen={resolver_origen_gestion_grupo(origen)}"
    if modo_historial:
        url = f"{url}&modo=historial"
    return f"{url}#{ancla}" if ancla else url


def _is_ajax(request):
    return request.headers.get("x-requested-with") == "XMLHttpRequest"


def _gestionar_fragment_context(
    grupo,
    cef_context,
    origen="grupos",
    *,
    modo_historial=False,
    vista_alumnos="actuales",
    vista_docentes="actuales",
):
    origen = resolver_origen_gestion_grupo(origen)
    vista_alumnos = "actuales"
    vista_docentes = "actuales"
    inscripciones_todas = list(_inscripciones_grupo(grupo))
    docentes_todos = list(_docentes_grupo(grupo))
    inscripciones = inscripciones_todas
    docentes = docentes_todos
    docentes_activos = [
        docente
        for docente in docentes_todos
        if docente.estado == CefDocenteGrupo.Estado.ACTIVO
    ]
    solo_lectura = (
        modo_historial
        or grupo.estado != CefGrupo.Estado.ACTIVO
        or not cef_context["puede_operar"]
    )
    return {
        "cef_context": cef_context,
        "grupo": grupo,
        "inscripciones": inscripciones,
        "docentes": docentes,
        "docentes_activos": docentes_activos,
        "vista_alumnos": vista_alumnos,
        "vista_docentes": vista_docentes,
        "modo_historial": modo_historial,
        "gestionar_solo_lectura": solo_lectura,
        "inscripciones_solo_lectura": solo_lectura,
        "docentes_solo_lectura": solo_lectura,
        "inscripciones_permite_edicion": not solo_lectura,
        "inscripciones_permite_retorno": not solo_lectura,
        "docentes_permite_edicion": not solo_lectura,
        "docentes_permite_retorno": not solo_lectura,
        "movimientos_estado": (
            list(grupo.movimientos_estado.all()) if modo_historial else []
        ),
        "origen": origen,
        "gestionar_grupo_modo": True,
        "gestionar_grupo_url": _url_gestionar_grupo(
            grupo,
            cef_context,
            origen,
            modo_historial=modo_historial,
            vista_alumnos=vista_alumnos,
            vista_docentes=vista_docentes,
        ),
        "docente_titular": _docente_activo_por_rol(
            docentes_activos,
            CefDocenteGrupo.Rol.TITULAR,
        ),
        "docente_suplente": _docente_activo_por_rol(
            docentes_activos,
            CefDocenteGrupo.Rol.SUPLENTE,
        ),
        "grupo_dias_texto": _dias_texto(grupo),
        "docentes_activos_count": len(docentes_activos),
        "docentes_activos_duplicados": (
            not modo_historial
            and docentes_grupo_tiene_duplicados_activos(grupo)
        ),
    }


def _render_docente_activo_fragment(request, context, titulo, docente_activo, rol_texto):
    fragment_context = {
        **context,
        "titulo": titulo,
        "docente_activo": docente_activo,
        "rol_texto": rol_texto,
    }
    return render_to_string(
        "cef/gestionar_grupo_docente_activo_cef.html",
        fragment_context,
        request=request,
    )


def _ajax_gestionar_fragment_response(
    request,
    grupo,
    cef_context,
    ok,
    message,
    origen="grupos",
    modal_template=None,
    modal_context=None,
):
    context = _gestionar_fragment_context(
        grupo,
        cef_context,
        origen,
        vista_alumnos=request.GET.get("vista_alumnos"),
        vista_docentes=request.GET.get("vista_docentes"),
    )
    data = {
        "ok": ok,
        "message": message,
        "fragments": [
            {
                "selector": "[data-cef-fragment='gestion-resumen']",
                "html": render_to_string(
                    "cef/gestionar_grupo_resumen_cef.html",
                    context,
                    request=request,
                ),
            },
            {
                "selector": "[data-cef-fragment='inscripciones-grupo']",
                "html": render_to_string(
                    "cef/inscripciones_grupo_lista_cef.html",
                    context,
                    request=request,
                ),
            },
            {
                "selector": "[data-cef-fragment='docentes-grupo']",
                "html": render_to_string(
                    "cef/docentes_grupo_lista_cef.html",
                    context,
                    request=request,
                ),
            },
            {
                "selector": "[data-cef-fragment='docente-titular-activo']",
                "html": _render_docente_activo_fragment(
                    request,
                    context,
                    "Profesor titular activo",
                    context["docente_titular"],
                    "profesor titular",
                ),
            },
            {
                "selector": "[data-cef-fragment='docente-suplente-activo']",
                "html": _render_docente_activo_fragment(
                    request,
                    context,
                    "Profesor suplente activo",
                    context["docente_suplente"],
                    "profesor suplente",
                ),
            },
        ],
        "close_modal": ok,
    }
    if modal_template and modal_context is not None:
        data["modal_html"] = render_to_string(
            modal_template,
            modal_context,
            request=request,
        )
    return JsonResponse(data)


def _baja_alumno_gestionar(request, grupo):
    baja_form = CefBajaMotivoForm(request.POST)
    if not baja_form.is_valid():
        return False, " ".join(
            error for errors in baja_form.errors.values() for error in errors
        )

    try:
        inscripcion_id = int(request.POST.get("inscripcion_id"))
    except (TypeError, ValueError):
        return False, "La inscripción seleccionada no es válida."

    inscripcion = get_object_or_404(
        CefInscripcion.objects.filter(grupo=grupo),
        pk=inscripcion_id,
    )
    try:
        dar_baja_inscripcion(
            inscripcion,
            request.user,
            baja_form.cleaned_data["motivo_baja"],
        )
        return True, "Alumno dado de baja del curso correctamente."
    except ValidationError as exc:
        return False, "; ".join(exc.messages)


def _alta_alumno_gestionar(request, grupo):
    try:
        inscripcion_id = int(request.POST.get("inscripcion_id"))
    except (TypeError, ValueError):
        return False, "La inscripción seleccionada no es válida."

    inscripcion = get_object_or_404(
        CefInscripcion.objects.filter(grupo=grupo),
        pk=inscripcion_id,
    )
    try:
        reinscribir_alumno(inscripcion, request.user)
        return True, "Alumno reinscripto correctamente."
    except ValidationError as exc:
        return False, "; ".join(exc.messages)


def _baja_docente_gestionar(request, grupo):
    baja_form = CefBajaMotivoForm(request.POST)
    if not baja_form.is_valid():
        return False, " ".join(
            error for errors in baja_form.errors.values() for error in errors
        )

    try:
        docente_grupo_id = int(request.POST.get("docente_grupo_id"))
    except (TypeError, ValueError):
        return False, "La asignación seleccionada no es válida."

    asignacion = get_object_or_404(
        CefDocenteGrupo.objects.filter(grupo=grupo),
        pk=docente_grupo_id,
    )
    try:
        dar_baja_asignacion_docente(
            asignacion,
            request.user,
            baja_form.cleaned_data["motivo_baja"],
        )
        return True, "Profesor dado de baja del curso correctamente."
    except ValidationError as exc:
        return False, "; ".join(exc.messages)


def _alta_docente_gestionar(
    request,
    grupo,
):
    try:
        docente_grupo_id = int(request.POST.get("docente_grupo_id"))
    except (TypeError, ValueError):
        return False, "La asignación seleccionada no es válida."

    asignacion = get_object_or_404(
        CefDocenteGrupo.objects.filter(grupo=grupo),
        pk=docente_grupo_id,
    )
    try:
        reasignar_docente_grupo(asignacion, request.user)
        return True, "Profesor reasignado al curso correctamente."
    except ValidationError as exc:
        return False, "; ".join(exc.messages)


def _dias_iniciales(grupo):
    if not grupo:
        return []

    return list(
        grupo.dias_funcionamiento.values_list("dia_semana_id", flat=True)
    )


def _guardar_dias(grupo, dias, user):
    CefGrupoDiaFuncionamiento.objects.filter(grupo=grupo).exclude(
        dia_semana__in=dias
    ).delete()

    for dia in dias:
        obj, creado = CefGrupoDiaFuncionamiento.objects.get_or_create(
            grupo=grupo,
            dia_semana=dia,
            defaults={"creado_por": user, "actualizado_por": user},
        )
        if not creado:
            obj.actualizado_por = user
            obj.save(update_fields=["actualizado_por", "actualizado_en"])


def _preparar_grupos(grupos):
    for grupo in grupos:
        grupo.dias_texto = ", ".join(
            str(item.dia_semana) for item in grupo.dias_funcionamiento.all()
        )
    return grupos


def _grupos_listado_context(cef_context, vista="actuales"):
    vista = normalizar_vista_cef(vista)
    queryset = (
        _grupos_historial_queryset(cef_context)
        if vista == "historial"
        else _grupos_queryset(cef_context)
    )
    grupos = _preparar_grupos(list(queryset)) if cef_context["puede_consultar"] else []
    return {
        "grupos": grupos,
        "total_grupos": len(grupos),
        "vista": vista,
        "baja_form_vacio": CefBajaMotivoForm(),
    }


def _grupo_baja_modal(cef_context, grupo_id):
    if not cef_context["puede_operar"] or not grupo_id:
        return None
    try:
        grupo_id = int(grupo_id)
    except (TypeError, ValueError):
        return None
    return get_object_or_404(_grupos_queryset(cef_context), pk=grupo_id)


def _dar_baja_grupo(request, cef_context):
    grupo = _grupo_baja_modal(cef_context, request.POST.get("grupo_id"))
    baja_form = CefBajaMotivoForm(request.POST)
    if not grupo:
        return False, "Seleccioná un CEF y ciclo válidos para dar de baja el grupo.", None, baja_form
    if grupo.estado != CefGrupo.Estado.ACTIVO:
        return False, "El grupo ya se encuentra dado de baja.", grupo, baja_form
    if grupo.alumnos_activos or grupo.docentes_activos:
        return (
            False,
            "No se puede dar de baja el grupo mientras tenga alumnos o profesores activos.",
            grupo,
            baja_form,
        )
    if not baja_form.is_valid():
        mensaje = " ".join(
            error for errors in baja_form.errors.values() for error in errors
        )
        return False, mensaje, grupo, baja_form
    try:
        dar_baja_grupo(
            grupo,
            request.user,
            baja_form.cleaned_data["motivo_baja"],
        )
    except ValidationError as exc:
        grupo = _grupo_baja_modal(cef_context, grupo.pk)
        return False, "; ".join(exc.messages), grupo, baja_form
    return True, "Grupo dado de baja correctamente.", grupo, baja_form


def _reactivar_grupo(request, cef_context):
    grupo = _grupo_baja_modal(cef_context, request.POST.get("grupo_id"))
    if not grupo:
        return False, "Seleccioná un CEF y ciclo válidos para reactivar el grupo.", None
    if grupo.estado != CefGrupo.Estado.BAJA:
        return False, "El grupo ya se encuentra activo.", grupo
    try:
        reactivar_grupo_servicio(grupo, request.user)
    except ValidationError as exc:
        grupo = _grupo_baja_modal(cef_context, grupo.pk)
        return False, "; ".join(exc.messages), grupo
    return True, "Curso reactivado correctamente.", grupo


def _proximo_numero_grupo(grupo):
    queryset = CefGrupo.objects.filter(
        cueanexo=grupo.cueanexo,
        ciclo=grupo.ciclo,
        actividad=grupo.actividad,
    )

    if grupo.pk:
        queryset = queryset.exclude(pk=grupo.pk)

    mayor = queryset.aggregate(mayor=Max("numero"))["mayor"] or 0
    return mayor + 1


def _actividad_cambio(grupo):
    if not grupo.pk:
        return True

    actividad_anterior_id = (
        CefGrupo.objects
        .filter(pk=grupo.pk)
        .values_list("actividad_id", flat=True)
        .first()
    )
    return actividad_anterior_id != grupo.actividad_id


def _preparar_numero_nombre(grupo):
    if _actividad_cambio(grupo):
        grupo.numero = _proximo_numero_grupo(grupo)

    actividad_nombre = getattr(grupo.actividad, "nombre", "") or str(grupo.actividad)
    grupo.nombre = f"{actividad_nombre} {grupo.numero}".strip()


def _aplicar_contexto_grupo_form(form, cef_context):
    form.instance.cueanexo = cef_context["cueanexo"]
    form.instance.ciclo = cef_context["ciclo"]


@cef_required
def carga_grupo(request):
    context = contexto_base(request, "grupos", "Grupos / Cursos CEF")
    perf_start_view(request)
    cef_context = context["cef_context"]
    vista = normalizar_vista_cef(
        request.GET.get("vista") or request.POST.get("vista")
    )
    baja_modal_grupo = None
    reactivar_modal_grupo = None
    baja_form = CefBajaMotivoForm()

    if request.method == "POST" and vista == "historial":
        message = "Historial es una vista de sólo lectura."
        if _is_ajax(request):
            return JsonResponse({"ok": False, "message": message})
        messages.error(request, message)
        return redirect(
            f"{redirect_con_contexto('cef:carga_grupo', cef_context)}&vista=historial"
        )

    if request.method == "POST" and not cef_context["puede_operar"]:
        message = (
            "El ciclo está cerrado. La información se encuentra en modo sólo lectura."
            if cef_context["ciclo_cerrado"]
            else "Seleccioná un CUE-Anexo y un ciclo lectivo para gestionar cursos."
        )
        if _is_ajax(request):
            return JsonResponse({"ok": False, "message": message})
        messages.error(request, message)
        return redirect(redirect_con_contexto("cef:carga_grupo", cef_context))

    if request.method == "POST" and request.POST.get("accion") in {
        "baja_grupo",
        "reactivar_grupo",
    }:
        if request.POST.get("accion") == "baja_grupo":
            accion_ok, accion_message, baja_modal_grupo, baja_form = _dar_baja_grupo(
                request,
                cef_context,
            )
        else:
            accion_ok, accion_message, reactivar_modal_grupo = _reactivar_grupo(
                request,
                cef_context,
            )
        if _is_ajax(request):
            modal_context = {
                "cef_context": cef_context,
                "baja_action_url": redirect_con_contexto(
                    "cef:carga_grupo",
                    cef_context,
                ),
                "baja_modal_grupo": None if accion_ok else baja_modal_grupo,
                "reactivar_modal_grupo": (
                    None if accion_ok else reactivar_modal_grupo
                ),
                "reactivar_error": (
                    accion_message
                    if not accion_ok and reactivar_modal_grupo
                    else ""
                ),
                "baja_form": baja_form,
            }
            modal_context.update(_grupos_listado_context(cef_context))
            return JsonResponse(
                {
                    "ok": accion_ok,
                    "message": accion_message,
                    "fragment_selector": "[data-cef-fragment='grupos-lista']",
                    "fragment_html": render_to_string(
                        "cef/grupos_lista_cef.html",
                        modal_context,
                        request=request,
                    ),
                    "modal_html": render_to_string(
                        "cef/grupo_baja_cef_modal.html",
                        modal_context,
                        request=request,
                    ),
                    "close_modal": accion_ok,
                }
            )
        if accion_ok:
            messages.success(request, accion_message)
        else:
            messages.error(request, accion_message)
        return redirect(redirect_con_contexto("cef:carga_grupo", cef_context))

    if (
        vista == "actuales"
        and request.GET.get("accion") == "agregar"
        and cef_context["puede_operar"]
    ):
        return redirect(redirect_con_contexto("cef:carga_grupo_nuevo", cef_context))

    if vista == "actuales" and request.GET.get("abrir_modal_baja") == "1":
        baja_modal_grupo = _grupo_baja_modal(
            cef_context,
            request.GET.get("grupo_id"),
        )
    elif vista == "actuales" and request.GET.get("abrir_modal_reactivar") == "1":
        reactivar_modal_grupo = _grupo_baja_modal(
            cef_context,
            request.GET.get("grupo_id"),
        )

    context.update(
        {
            "baja_action_url": redirect_con_contexto("cef:carga_grupo", cef_context),
            "baja_modal_grupo": baja_modal_grupo,
            "reactivar_modal_grupo": reactivar_modal_grupo,
            "baja_form": baja_form,
        }
    )
    context.update(_grupos_listado_context(cef_context, vista))
    return perf_render(request, "cef/carga_grupo_cef.html", context)


@cef_required
@require_GET
def grupos_fragmento(request):
    cef_context = resolver_contexto_operativo(request)
    vista = normalizar_vista_cef(request.GET.get("vista"))
    context = {
        "cef_context": cef_context,
        "cef_partial": True,
        "baja_action_url": redirect_con_contexto("cef:carga_grupo", cef_context),
        "baja_modal_grupo": (
            _grupo_baja_modal(cef_context, request.GET.get("grupo_id"))
            if vista == "actuales" and request.GET.get("abrir_modal_baja") == "1"
            else None
        ),
        "reactivar_modal_grupo": (
            _grupo_baja_modal(cef_context, request.GET.get("grupo_id"))
            if vista == "actuales" and request.GET.get("abrir_modal_reactivar") == "1"
            else None
        ),
        "baja_form": CefBajaMotivoForm(),
    }
    context.update(_grupos_listado_context(cef_context, vista))
    return render_fragmento_cef(request, "cef/grupos_seccion_cef.html", context)


@cef_required
def gestionar_grupo(request, grupo_id):
    context = contexto_base(request, "grupos", "Gestionar curso CEF")
    cef_context = context["cef_context"]
    origen = resolver_origen_gestion_grupo(
        request.GET.get("origen") or request.POST.get("origen")
    )
    modo_historial = normalizar_vista_cef(
        request.GET.get("modo") or request.POST.get("modo")
    ) == "historial"
    vista_alumnos = "actuales"
    vista_docentes = "actuales"
    if modo_historial:
        cef_context["vista"] = "historial"

    if not cef_context["puede_consultar"]:
        messages.warning(
            request,
            "Seleccioná un CUE-Anexo y un ciclo lectivo para gestionar cursos.",
        )
        return redirect(redirect_con_contexto("cef:carga_grupo", cef_context))

    grupo = (
        _grupo_historico_seguro(grupo_id, cef_context)
        if modo_historial
        else _grupo_seguro(grupo_id, cef_context)
    )
    if request.method == "POST":
        accion = request.POST.get("accion")
        if modo_historial:
            message = "Historial es una vista de sólo lectura."
            if _is_ajax(request):
                return JsonResponse({"ok": False, "message": message})
            messages.error(request, message)
            return redirect(
                _url_gestionar_grupo(
                    grupo,
                    cef_context,
                    origen,
                    modo_historial=modo_historial,
                    vista_alumnos=vista_alumnos,
                    vista_docentes=vista_docentes,
                )
            )
        if not cef_context["puede_operar"]:
            message = "El ciclo está cerrado. La información se encuentra en modo sólo lectura."
            if _is_ajax(request):
                return JsonResponse({"ok": False, "message": message})
            messages.error(request, message)
            return redirect(
                _url_gestionar_grupo(
                    grupo,
                    cef_context,
                    origen,
                    vista_alumnos=vista_alumnos,
                    vista_docentes=vista_docentes,
                )
            )
        if grupo.estado != CefGrupo.Estado.ACTIVO:
            message = "El grupo está dado de baja y solo puede consultarse."
            if _is_ajax(request):
                return JsonResponse({"ok": False, "message": message})
            messages.error(request, message)
            return redirect(
                _url_gestionar_grupo(
                    grupo,
                    cef_context,
                    origen,
                    vista_alumnos=vista_alumnos,
                    vista_docentes=vista_docentes,
                )
            )

        accion = request.POST.get("accion")
        if accion == "baja_alumno":
            ok, message = _baja_alumno_gestionar(request, grupo)
            if _is_ajax(request):
                return _ajax_gestionar_fragment_response(
                    request,
                    grupo,
                    cef_context,
                    ok,
                    message,
                    origen,
                )
        elif accion == "alta_alumno":
            ok, message = _alta_alumno_gestionar(request, grupo)
            if _is_ajax(request):
                return _ajax_gestionar_fragment_response(
                    request,
                    grupo,
                    cef_context,
                    ok,
                    message,
                    origen,
                )
        elif accion == "baja_docente":
            ok, message = _baja_docente_gestionar(request, grupo)
            if _is_ajax(request):
                return _ajax_gestionar_fragment_response(
                    request,
                    grupo,
                    cef_context,
                    ok,
                    message,
                    origen,
                )
        elif accion == "alta_docente":
            ok, message = _alta_docente_gestionar(
                request,
                grupo,
            )
            if _is_ajax(request):
                return _ajax_gestionar_fragment_response(
                    request,
                    grupo,
                    cef_context,
                    ok,
                    message,
                    origen,
                )
        else:
            ok = False
            message = "La acción solicitada no es válida."
            if _is_ajax(request):
                return JsonResponse({"ok": False, "message": message}, status=400)
        if ok:
            messages.success(request, message)
        else:
            messages.error(request, message)
        return redirect(
            _url_gestionar_grupo(
                grupo,
                cef_context,
                origen,
                vista_alumnos=vista_alumnos,
                vista_docentes=vista_docentes,
            )
        )

    destinos_volver = {
        "alumnos": ("cef:alumnos", "Volver a Alumnos"),
        "profesores": ("cef:profesores", "Volver a Profesores"),
        "grupos": ("cef:carga_grupo", "Volver a Grupos / Cursos"),
    }
    volver_viewname, volver_label = destinos_volver[origen]
    gestionar_grupo_url = _url_gestionar_grupo(
        grupo,
        cef_context,
        origen,
        modo_historial=modo_historial,
        vista_alumnos=vista_alumnos,
        vista_docentes=vista_docentes,
    )
    context.update(
        _gestionar_fragment_context(
            grupo,
            cef_context,
            origen,
            modo_historial=modo_historial,
            vista_alumnos=vista_alumnos,
            vista_docentes=vista_docentes,
        )
    )
    context["grupo_dias_texto"] = _dias_texto(grupo)
    context.update(
        {
            "volver_url": (
                f"{redirect_con_contexto(volver_viewname, cef_context)}&vista=historial"
                if modo_historial
                else redirect_con_contexto(volver_viewname, cef_context)
            ),
            "volver_label": volver_label,
            "modal_alumno_action_url": _url_modal_inscripcion_grupo(
                grupo,
                cef_context,
                origen=origen,
                destino="gestionar",
                vista_alumnos=vista_alumnos,
                vista_docentes=vista_docentes,
            ),
            "modal_docente_action_url": _url_modal_docente_grupo(
                grupo,
                cef_context,
                origen=origen,
                destino="gestionar",
                vista_alumnos=vista_alumnos,
                vista_docentes=vista_docentes,
            ),
            "modal_alumno_abierto": (
                not modo_historial
                and request.GET.get("abrir_modal_alumno") == "1"
            ),
            "modal_docente_abierto": (
                not modo_historial
                and request.GET.get("abrir_modal_docente") == "1"
            ),
            "modal_volver_url": gestionar_grupo_url,
            "modal_tiene_grupo": True,
            "docente_form": CefDocenteGrupoForm(),
        }
    )
    return render(request, "cef/gestionar_grupo_cef.html", context)


def _guardar_grupo(form, dias_form, cef_context, user):
    grupo = form.save(commit=False)
    grupo.cueanexo = cef_context["cueanexo"]
    grupo.ciclo = cef_context["ciclo"]
    grupo.codigo_ra_override = None
    grupo.motivo_codigo_ra_override = ""
    dias = list(dias_form.cleaned_data["dias"])
    dias_ids = [dia.pk for dia in dias]

    with transaction.atomic():
        if grupo.pk:
            grupo_actual = CefGrupo.objects.select_for_update().get(pk=grupo.pk)
            validar_ciclo_escribible(grupo_actual.ciclo_id)
            if grupo_actual.estado != CefGrupo.Estado.ACTIVO:
                raise ValidationError(
                    "El grupo está dado de baja y no puede editarse."
                )

            dias_actuales_ids = set(
                CefGrupoDiaFuncionamiento.objects.filter(
                    grupo=grupo_actual,
                ).values_list("dia_semana_id", flat=True)
            )
            cambia_compatibilidad = (
                grupo_actual.actividad_id != grupo.actividad_id
                or grupo_actual.hora_inicio != grupo.hora_inicio
                or grupo_actual.hora_fin != grupo.hora_fin
                or dias_actuales_ids != set(dias_ids)
            )
            if cambia_compatibilidad:
                alumnos_ids = list(
                    CefInscripcion.objects.filter(
                        grupo=grupo_actual,
                        estado=CefInscripcion.Estado.ACTIVO,
                    )
                    .order_by("alumno_id")
                    .values_list("alumno_id", flat=True)
                    .distinct()
                )
                if alumnos_ids:
                    list(
                        CefAlumnoCef.objects.select_for_update()
                        .filter(
                            cueanexo=grupo_actual.cueanexo,
                            ciclo=grupo_actual.ciclo,
                            alumno_id__in=alumnos_ids,
                            estado=CefAlumnoCef.Estado.ACTIVO,
                        )
                        .order_by("alumno_id", "pk")
                        .values_list("pk", flat=True)
                    )
                    validar_conflictos_horarios_edicion_grupo(
                        grupo_actual,
                        actividad_id=grupo.actividad_id,
                        hora_inicio=grupo.hora_inicio,
                        hora_fin=grupo.hora_fin,
                        dias_ids=dias_ids,
                        alumnos_ids=alumnos_ids,
                    )

            grupo.estado = grupo_actual.estado
            grupo.fecha_baja = grupo_actual.fecha_baja
            grupo.motivo_baja = grupo_actual.motivo_baja
        else:
            validar_ciclo_escribible(cef_context["ciclo"])

        _preparar_numero_nombre(grupo)
        if not grupo.pk:
            grupo.creado_por = user
        grupo.actualizado_por = user
        grupo.save()
        _guardar_dias(grupo, dias, user)
    return grupo


@cef_required
def carga_grupo_form(request, grupo_id=None):
    context = contexto_base(request, "grupos", "Grupos / Cursos CEF")
    cef_context = context["cef_context"]

    if not cef_context["puede_operar"]:
        messages.error(
            request,
            "El ciclo está cerrado. La información se encuentra en modo sólo lectura."
            if cef_context["ciclo_cerrado"]
            else "Seleccioná un CUE-Anexo y un ciclo para cargar grupos.",
        )
        return redirect(redirect_con_contexto("cef:carga_grupo", cef_context))

    grupo_edicion = _grupo_seguro(grupo_id, cef_context) if grupo_id else None
    if grupo_edicion and grupo_edicion.estado != CefGrupo.Estado.ACTIVO:
        messages.error(request, "El grupo está dado de baja y no puede editarse.")
        return redirect(
            _url_gestionar_grupo(grupo_edicion, cef_context, "grupos")
        )

    if request.method == "POST":
        form = CefGrupoForm(
            request.POST,
            instance=grupo_edicion,
            ciclo=cef_context["ciclo"],
        )
        _aplicar_contexto_grupo_form(form, cef_context)
        dias_form = CefGrupoDiasForm(request.POST)

        if form.is_valid() and dias_form.is_valid():
            try:
                _guardar_grupo(form, dias_form, cef_context, request.user)
            except ValidationError as exc:
                mensaje = "; ".join(exc.messages)
                form.add_error(None, mensaje)
                messages.error(request, mensaje)
            else:
                messages.success(request, "Grupo guardado correctamente.")
                return redirect(redirect_con_contexto("cef:carga_grupo", cef_context))

        if not form.non_field_errors():
            messages.error(request, "Revisá los datos del formulario para guardar el grupo.")
    else:
        form = CefGrupoForm(instance=grupo_edicion, ciclo=cef_context["ciclo"])
        _aplicar_contexto_grupo_form(form, cef_context)
        dias_form = CefGrupoDiasForm(dias_iniciales=_dias_iniciales(grupo_edicion))

    context.update(
        {
            "form": form,
            "dias_form": dias_form,
            "grupo_edicion": grupo_edicion,
            "form_title": "Editar Sección" if grupo_edicion else "Agregar Sección",
        }
    )
    return render(request, "cef/form_grupo_cef.html", context)
