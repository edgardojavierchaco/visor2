# apps/especial/views_carga_seccion.py
# -*- coding: utf-8 -*-

from django.contrib import messages
from django.db import transaction
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render

from django.http import JsonResponse
from django.template.loader import render_to_string

from .forms import EspecialSeccionForm
from .models import SeccionEspecial, AlumnoSeccion, DocenteSeccion
from .permisos import especial_required
from .views_contexto import contexto_base, redirect_con_contexto
from .views_docentes_seccion import dar_alta_docente_seccion, dar_baja_docente_seccion
from .views_inscripcion_seccion import dar_alta_inscripcion_seccion, dar_baja_inscripcion_seccion

def _is_ajax(request):
    return request.headers.get("x-requested-with") == "XMLHttpRequest"



def _secciones_queryset(especial_context):
    """QuerySet de secciones filtrado por CUE-Anexo y ciclo."""
    return (
        SeccionEspecial.objects.filter(
            cueanexo=especial_context["cueanexo"],
            ciclo=especial_context["ciclo"],
        )
        .select_related(
            "cd_tipo_seccion",
            "turno",
            "rango_etario",
            "modalidad",
            "tipo_estructura_especial",
        )
        .annotate(
            alumnos_activos=Count(
                "alumnos",
                filter=Q(alumnos__estado__in=["activo", "inactivo"]),
            )
        )
        .order_by("nombre_seccion")
    )


def _seccion_segura(seccion_id, especial_context):
    """Obtiene una sección validando que pertenezca al CUE-Anexo y ciclo actual."""
    return get_object_or_404(
        SeccionEspecial.objects.filter(
            cueanexo=especial_context["cueanexo"],
            ciclo=especial_context["ciclo"],
        ).select_related(
            "cd_tipo_seccion",
            "turno",
            "rango_etario",
            "modalidad",
            "tipo_estructura_especial",
        ),
        pk=seccion_id,
    )


@especial_required
def carga_seccion(request):
    """Vista principal de gestión de secciones."""
    context = contexto_base(request, "secciones", "Secciones Educación Especial")
    especial_context = context["especial_context"]

    if request.GET.get("accion") == "agregar":
        return redirect(redirect_con_contexto("especial:carga_seccion_nueva", especial_context))

    secciones = (
        list(_secciones_queryset(especial_context))
        if especial_context["puede_operar"]
        else []
    )

    context.update(
        {
            "secciones": secciones,
            "total_secciones": len(secciones),
        }
    )
    return render(request, "especial/carga_seccion_especial.html", context)


def _guardar_seccion(form, especial_context, user):
    """Guarda una sección asignando CUE-Anexo, ciclo y auditoría."""
    with transaction.atomic():
        seccion = form.save(commit=False)
        seccion.cueanexo = especial_context["cueanexo"]
        seccion.ciclo = especial_context["ciclo"]
        if not seccion.pk:
            seccion.creado_por = user
        seccion.actualizado_por = user
        seccion.save()
    return seccion


@especial_required
def carga_seccion_form(request, seccion_id=None):
    """Formulario de creación/edición de sección."""
    context = contexto_base(request, "secciones", "Secciones Educación Especial")
    especial_context = context["especial_context"]

    if not especial_context["puede_operar"]:
        messages.error(request, "Seleccioná un CUE-Anexo y un ciclo para cargar secciones.")
        return redirect(redirect_con_contexto("especial:carga_seccion", especial_context))

    seccion_edicion = _seccion_segura(seccion_id, especial_context) if seccion_id else None
    
    if not seccion_edicion:
        seccion_edicion = SeccionEspecial(
            cueanexo=especial_context["cueanexo"],
            ciclo=especial_context["ciclo"]
        )

    if request.method == "POST":
        form = EspecialSeccionForm(
            request.POST,
            instance=seccion_edicion,
            ciclo=especial_context["ciclo"],
        )

        if form.is_valid():
            _guardar_seccion(form, especial_context, request.user)
            messages.success(request, "Sección guardada correctamente.")
            return redirect(redirect_con_contexto("especial:carga_seccion", especial_context))

        messages.error(request, "Revisá los datos del formulario para guardar la sección.")
    else:
        form = EspecialSeccionForm(instance=seccion_edicion, ciclo=especial_context["ciclo"])

    context.update(
        {
            "form": form,
            "seccion_edicion": seccion_edicion,
            "form_title": "Editar Sección" if seccion_edicion else "Agregar Sección",
        }
    )
    return render(request, "especial/form_seccion_especial.html", context)


def _inscripciones_seccion(seccion):
    return (
        AlumnoSeccion.objects.filter(seccion=seccion)
        .select_related("alumno", "alumno__sexo")
        .order_by("estado", "alumno__apellidos", "alumno__nombres")
    )


def _docentes_seccion(seccion):
    return (
        DocenteSeccion.objects.filter(grupo=seccion)
        .order_by("estado", "rol", "docente_nombre_snapshot", "docente_cuil")
    )


def _docente_activo_por_rol(docentes, rol):
    return next(
        (
            docente
            for docente in docentes
            if docente.rol == rol and docente.estado == DocenteSeccion.Estado.ACTIVO
        ),
        None,
    )


def _gestionar_fragment_context(seccion, especial_context):
    inscripciones = list(_inscripciones_seccion(seccion))
    docentes = list(_docentes_seccion(seccion))
    docentes_activos = [
        docente for docente in docentes if docente.estado == DocenteSeccion.Estado.ACTIVO
    ]
    return {
        "especial_context": especial_context,
        "seccion": seccion,
        "inscripciones": inscripciones,
        "docentes": docentes,
        "docentes_activos": docentes_activos,
        "gestionar_seccion_modo": True,
        "gestionar_seccion_url": redirect_con_contexto("especial:gestionar_seccion", especial_context, seccion_id=seccion.pk),
        "docente_titular": _docente_activo_por_rol(
            docentes,
            DocenteSeccion.Rol.TITULAR,
        ),
        "docente_suplente": _docente_activo_por_rol(
            docentes,
            DocenteSeccion.Rol.SUPLENTE,
        ),
        "docentes_activos_count": len(docentes_activos),
    }


def _render_docente_activo_fragment(request, context, titulo, docente_activo, rol_texto):
    fragment_context = {
        **context,
        "titulo": titulo,
        "docente_activo": docente_activo,
        "rol_texto": rol_texto,
    }
    return render_to_string(
        "especial/gestionar_seccion_docente_activo_especial.html",
        fragment_context,
        request=request,
    )


def _ajax_gestionar_fragment_response(request, seccion, especial_context, ok, message):
    context = _gestionar_fragment_context(seccion, especial_context)
    return JsonResponse(
        {
            "ok": ok,
            "message": message,
            "fragments": [
                {
                    "selector": "[data-cef-fragment='gestion-resumen']",
                    "html": render_to_string(
                        "especial/gestionar_seccion_resumen_especial.html",
                        context,
                        request=request,
                    ),
                },
                {
                    "selector": "[data-cef-fragment='inscripciones-seccion']",
                    "html": render_to_string(
                        "especial/inscripciones_seccion_lista_especial.html",
                        context,
                        request=request,
                    ),
                },
                {
                    "selector": "[data-cef-fragment='docentes-seccion']",
                    "html": render_to_string(
                        "especial/docentes_seccion_lista_especial.html",
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


def _baja_alumno_gestionar(request, seccion):
    try:
        inscripcion_id = int(request.POST.get("inscripcion_id"))
    except (TypeError, ValueError):
        return False, "La inscripción seleccionada no es válida."

    inscripcion = get_object_or_404(
        AlumnoSeccion.objects.filter(seccion=seccion),
        pk=inscripcion_id,
    )
    try:
        dar_baja_inscripcion_seccion(inscripcion, request.user)
        return True, "Alumno dado de baja de la sección correctamente."
    except ValidationError as exc:
        return False, "; ".join(exc.messages)


def _alta_alumno_gestionar(request, seccion):
    try:
        inscripcion_id = int(request.POST.get("inscripcion_id"))
    except (TypeError, ValueError):
        return False, "La inscripción seleccionada no es válida."

    inscripcion = get_object_or_404(
        AlumnoSeccion.objects.filter(seccion=seccion),
        pk=inscripcion_id,
    )
    try:
        dar_alta_inscripcion_seccion(inscripcion, request.user)
        return True, "Alumno reinscripto correctamente."
    except ValidationError as exc:
        return False, "; ".join(exc.messages)


def _baja_docente_gestionar(request, seccion):
    try:
        docente_grupo_id = int(request.POST.get("docente_grupo_id"))
    except (TypeError, ValueError):
        return False, "La asignación seleccionada no es válida."

    asignacion = get_object_or_404(
        DocenteSeccion.objects.filter(grupo=seccion),
        pk=docente_grupo_id,
    )
    try:
        dar_baja_docente_seccion(asignacion, request.user)
        return True, "Profesor dado de baja de la sección correctamente."
    except ValidationError as exc:
        return False, "; ".join(exc.messages)


def _alta_docente_gestionar(request, seccion):
    try:
        docente_grupo_id = int(request.POST.get("docente_grupo_id"))
    except (TypeError, ValueError):
        return False, "La asignación seleccionada no es válida."

    asignacion = get_object_or_404(
        DocenteSeccion.objects.filter(grupo=seccion),
        pk=docente_grupo_id,
    )
    try:
        dar_alta_docente_seccion(asignacion, request.user)
        return True, "Profesor reasignado a la sección correctamente."
    except ValidationError as exc:
        return False, "; ".join(exc.messages)


@especial_required
def gestionar_seccion(request, seccion_id):
    """Vista de gestión integral de una sección."""
    context = contexto_base(request, "secciones", "Gestionar sección")
    especial_context = context["especial_context"]

    if not especial_context["puede_operar"]:
        messages.warning(
            request,
            "Seleccioná un CUE-Anexo y un ciclo lectivo para gestionar secciones.",
        )
        return redirect(redirect_con_contexto("especial:carga_seccion", especial_context))

    seccion = _seccion_segura(seccion_id, especial_context)
    if request.method == "POST":
        accion = request.POST.get("accion")
        if accion == "baja_alumno":
            ok, message = _baja_alumno_gestionar(request, seccion)
            if _is_ajax(request):
                return _ajax_gestionar_fragment_response(
                    request,
                    seccion,
                    especial_context,
                    ok,
                    message,
                )
        elif accion == "alta_alumno":
            ok, message = _alta_alumno_gestionar(request, seccion)
            if _is_ajax(request):
                return _ajax_gestionar_fragment_response(
                    request,
                    seccion,
                    especial_context,
                    ok,
                    message,
                )
        elif accion == "baja_docente":
            ok, message = _baja_docente_gestionar(request, seccion)
            if _is_ajax(request):
                return _ajax_gestionar_fragment_response(
                    request,
                    seccion,
                    especial_context,
                    ok,
                    message,
                )
        elif accion == "alta_docente":
            ok, message = _alta_docente_gestionar(request, seccion)
            if _is_ajax(request):
                return _ajax_gestionar_fragment_response(
                    request,
                    seccion,
                    especial_context,
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
        return redirect(redirect_con_contexto("especial:gestionar_seccion", especial_context, seccion_id=seccion.pk))

    context.update(_gestionar_fragment_context(seccion, especial_context))
    return render(request, "especial/gestionar_seccion_especial.html", context)