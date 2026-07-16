# -*- coding: utf-8 -*-

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Count, Max, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string

from .forms import CefGrupoDiasForm, CefGrupoForm
from .models import (
    CefDocenteGrupo,
    CefGrupo,
    CefGrupoDiaFuncionamiento,
    CefInscripcion,
    docentes_grupo_tiene_duplicados_activos,
)
from .permisos import cef_required
from .views_contexto import contexto_base, redirect_con_contexto
from .views_docentes_grupo import dar_alta_docente_grupo, dar_baja_docente_grupo
from .views_inscripcion_grupo import dar_alta_inscripcion_grupo, dar_baja_inscripcion_grupo


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
        .prefetch_related("dias_funcionamiento__dia_semana")
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


def _url_gestionar_grupo(grupo, cef_context):
    return redirect_con_contexto("cef:gestionar_grupo", cef_context, grupo_id=grupo.pk)


def _is_ajax(request):
    return request.headers.get("x-requested-with") == "XMLHttpRequest"


def _gestionar_fragment_context(grupo, cef_context):
    inscripciones = list(_inscripciones_grupo(grupo))
    docentes = list(_docentes_grupo(grupo))
    docentes_activos = [
        docente for docente in docentes if docente.estado == CefDocenteGrupo.Estado.ACTIVO
    ]
    return {
        "cef_context": cef_context,
        "grupo": grupo,
        "inscripciones": inscripciones,
        "docentes": docentes,
        "docentes_activos": docentes_activos,
        "gestionar_grupo_modo": True,
        "gestionar_grupo_url": _url_gestionar_grupo(grupo, cef_context),
        "docente_titular": _docente_activo_por_rol(
            docentes,
            CefDocenteGrupo.Rol.TITULAR,
        ),
        "docente_suplente": _docente_activo_por_rol(
            docentes,
            CefDocenteGrupo.Rol.SUPLENTE,
        ),
        "grupo_dias_texto": _dias_texto(grupo),
        "docentes_activos_count": len(docentes_activos),
        "docentes_activos_duplicados": docentes_grupo_tiene_duplicados_activos(grupo),
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


def _ajax_gestionar_fragment_response(request, grupo, cef_context, ok, message):
    context = _gestionar_fragment_context(grupo, cef_context)
    return JsonResponse(
        {
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
    )


def _baja_alumno_gestionar(request, grupo):
    try:
        inscripcion_id = int(request.POST.get("inscripcion_id"))
    except (TypeError, ValueError):
        return False, "La inscripción seleccionada no es válida."

    inscripcion = get_object_or_404(
        CefInscripcion.objects.filter(grupo=grupo),
        pk=inscripcion_id,
    )
    try:
        dar_baja_inscripcion_grupo(inscripcion, request.user)
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
        dar_alta_inscripcion_grupo(inscripcion, request.user)
        return True, "Alumno reinscripto correctamente."
    except ValidationError as exc:
        return False, "; ".join(exc.messages)


def _baja_docente_gestionar(request, grupo):
    try:
        docente_grupo_id = int(request.POST.get("docente_grupo_id"))
    except (TypeError, ValueError):
        return False, "La asignación seleccionada no es válida."

    asignacion = get_object_or_404(
        CefDocenteGrupo.objects.filter(grupo=grupo),
        pk=docente_grupo_id,
    )
    try:
        dar_baja_docente_grupo(asignacion, request.user)
        return True, "Profesor dado de baja del curso correctamente."
    except ValidationError as exc:
        return False, "; ".join(exc.messages)


def _alta_docente_gestionar(request, grupo):
    try:
        docente_grupo_id = int(request.POST.get("docente_grupo_id"))
    except (TypeError, ValueError):
        return False, "La asignación seleccionada no es válida."

    asignacion = get_object_or_404(
        CefDocenteGrupo.objects.filter(grupo=grupo),
        pk=docente_grupo_id,
    )
    try:
        dar_alta_docente_grupo(asignacion, request.user)
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
    cef_context = context["cef_context"]

    if request.GET.get("accion") == "agregar":
        return redirect(redirect_con_contexto("cef:carga_grupo_nuevo", cef_context))

    grupos = (
        _preparar_grupos(list(_grupos_queryset(cef_context)))
        if cef_context["puede_operar"]
        else []
    )

    context.update(
        {
            "grupos": grupos,
            "total_grupos": len(grupos),
        }
    )
    return render(request, "cef/carga_grupo_cef.html", context)


@cef_required
def gestionar_grupo(request, grupo_id):
    context = contexto_base(request, "grupos", "Gestionar curso CEF")
    cef_context = context["cef_context"]

    if not cef_context["puede_operar"]:
        messages.warning(
            request,
            "Seleccioná un CUE-Anexo y un ciclo lectivo para gestionar cursos.",
        )
        return redirect(redirect_con_contexto("cef:carga_grupo", cef_context))

    grupo = _grupo_seguro(grupo_id, cef_context)
    if request.method == "POST":
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
                )
        elif accion == "alta_docente":
            ok, message = _alta_docente_gestionar(request, grupo)
            if _is_ajax(request):
                return _ajax_gestionar_fragment_response(
                    request,
                    grupo,
                    cef_context,
                    ok,
                    message,
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
        return redirect(_url_gestionar_grupo(grupo, cef_context))

    context.update(_gestionar_fragment_context(grupo, cef_context))
    context["grupo_dias_texto"] = _dias_texto(grupo)
    return render(request, "cef/gestionar_grupo_cef.html", context)


def _guardar_grupo(form, dias_form, cef_context, user):
    with transaction.atomic():
        grupo = form.save(commit=False)
        grupo.cueanexo = cef_context["cueanexo"]
        grupo.ciclo = cef_context["ciclo"]
        grupo.codigo_ra_override = None
        grupo.motivo_codigo_ra_override = ""
        _preparar_numero_nombre(grupo)
        if not grupo.pk:
            grupo.creado_por = user
        grupo.actualizado_por = user
        grupo.save()
        _guardar_dias(grupo, dias_form.cleaned_data["dias"], user)
    return grupo


@cef_required
def carga_grupo_form(request, grupo_id=None):
    context = contexto_base(request, "grupos", "Grupos / Cursos CEF")
    cef_context = context["cef_context"]

    if not cef_context["puede_operar"]:
        messages.error(request, "Seleccioná un CUE-Anexo y un ciclo para cargar grupos.")
        return redirect(redirect_con_contexto("cef:carga_grupo", cef_context))

    grupo_edicion = _grupo_seguro(grupo_id, cef_context) if grupo_id else None

    if request.method == "POST":
        form = CefGrupoForm(
            request.POST,
            instance=grupo_edicion,
            ciclo=cef_context["ciclo"],
        )
        _aplicar_contexto_grupo_form(form, cef_context)
        dias_form = CefGrupoDiasForm(request.POST)

        if form.is_valid() and dias_form.is_valid():
            _guardar_grupo(form, dias_form, cef_context, request.user)
            messages.success(request, "Grupo guardado correctamente.")
            return redirect(redirect_con_contexto("cef:carga_grupo", cef_context))

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
