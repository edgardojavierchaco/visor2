# -*- coding: utf-8 -*-

from django.contrib import messages
from django.db import transaction
from django.db.models import Count, Max, Q
from django.shortcuts import get_object_or_404, redirect, render

from .forms import CefGrupoDiasForm, CefGrupoForm
from .models import (
    CefDocenteGrupo,
    CefGrupo,
    CefGrupoDiaFuncionamiento,
    CefInscripcion,
)
from .permisos import cef_required
from .views_contexto import contexto_base, redirect_con_contexto


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


def _inscripciones_abiertas_grupo(grupo):
    return (
        CefInscripcion.objects.filter(
            grupo=grupo,
            estado=CefInscripcion.Estado.ACTIVO,
        )
        .select_related("alumno", "alumno__sexo")
        .order_by("estado", "alumno__apellidos", "alumno__nombres")
    )


def _docentes_activos_grupo(grupo):
    return (
        CefDocenteGrupo.objects.filter(
            grupo=grupo,
            estado=CefDocenteGrupo.Estado.ACTIVO,
        )
        .order_by("rol", "docente_nombre_snapshot", "docente_cuil")
    )


def _docente_activo_por_rol(docentes, rol):
    return next((docente for docente in docentes if docente.rol == rol), None)


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
    inscripciones = list(_inscripciones_abiertas_grupo(grupo))
    docentes_activos = list(_docentes_activos_grupo(grupo))

    context.update(
        {
            "grupo": grupo,
            "grupo_dias_texto": _dias_texto(grupo),
            "inscripciones": inscripciones,
            "docentes_activos": docentes_activos,
            "docente_titular": _docente_activo_por_rol(
                docentes_activos,
                CefDocenteGrupo.Rol.TITULAR,
            ),
            "docente_suplente": _docente_activo_por_rol(
                docentes_activos,
                CefDocenteGrupo.Rol.SUPLENTE,
            ),
        }
    )
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
