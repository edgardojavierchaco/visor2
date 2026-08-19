# apps/especial/views_carga_seccion.py
# -*- coding: utf-8 -*-

import re

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.utils import OperationalError, ProgrammingError
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render

from django.http import JsonResponse
from django.template.loader import render_to_string

from .forms import (
    EspecialBusquedaAlumnoForm,
    EspecialBusquedaDocenteForm,
    EspecialDocenteSeccionForm,
    EspecialSeccionForm,
)
from .models import (
    AlumnoSeccion,
    DocenteSeccion,
    EspecialAlumnoBanco,
    EspecialDocenteBanco,
    SeccionEspecial,
    cueanexo_tiene_oferta_matricula_compartida,
)
from .permisos import especial_required
from .views_contexto import contexto_base, redirect_con_contexto, render_especial
from .services.docentes_seccion import dar_alta_docente_seccion, dar_baja_docente_seccion
from .views_inscripcion_seccion import (
    _alumno_row,
    _buscar_alumno,
    crear_inscripcion_activa,
    dar_alta_inscripcion_seccion,
    dar_baja_inscripcion_seccion,
)
from .views_docentes import _buscar_docente, _docente_row

def _is_ajax(request):
    return request.headers.get("x-requested-with") == "XMLHttpRequest"


def _errores_form(form):
    return " ".join(
        str(error)
        for errors in form.errors.values()
        for error in errors
    )


def _solo_digitos(valor):
    return re.sub(r"\D", "", str(valor or ""))


def _preparar_modales_gestionar(request, seccion, especial_context):
    """Prepara búsqueda y formularios para los modales dentro de la sección."""
    cuil_buscado = _solo_digitos(request.GET.get("cuil", ""))
    cuil_alumno = cuil_buscado if request.GET.get("abrir_modal_alumno") == "1" else ""
    alumno = _buscar_alumno(cuil_alumno) if cuil_alumno else None
    alumno_form = EspecialBusquedaAlumnoForm(
        {"cuil": cuil_alumno} if cuil_alumno else None
    )
    alumno_error = _errores_form(alumno_form) if cuil_alumno and not alumno_form.is_valid() else ""
    alumno_en_banco = bool(
        alumno
        and EspecialAlumnoBanco.objects.filter(
            alumno=alumno,
            cueanexo=seccion.cueanexo,
            ciclo=seccion.ciclo,
            estado=EspecialAlumnoBanco.Estado.ACTIVO,
        ).exists()
    )
    alumno_en_seccion = bool(
        alumno
        and AlumnoSeccion.objects.filter(
            seccion=seccion,
            alumno=alumno,
            estado=AlumnoSeccion.Estado.ACTIVO,
        ).exists()
    )

    cuil_docente = cuil_buscado if request.GET.get("abrir_modal_docente") == "1" else ""
    docente = _buscar_docente(cuil_docente) if cuil_docente else None
    docente_form = EspecialDocenteSeccionForm()
    docente_error = ""
    if cuil_docente:
        busqueda_docente = EspecialBusquedaDocenteForm({"cuil": cuil_docente})
        if not busqueda_docente.is_valid():
            docente_error = _errores_form(busqueda_docente)
    docente_en_banco = False
    if docente:
        docente_en_banco = EspecialDocenteBanco.objects.filter(
            docente_cuil=docente.cuil,
            cueanexo=seccion.cueanexo,
            ciclo=seccion.ciclo,
            estado=EspecialDocenteBanco.Estado.ACTIVO,
        ).exists()

    asignacion_activa = None
    if docente:
        asignacion_activa = (
            DocenteSeccion.objects
            .filter(
                seccion=seccion,
                docente_cuil=docente.cuil,
                estado=DocenteSeccion.Estado.ACTIVO,
            )
            .first()
        )

    gestionar_url = redirect_con_contexto(
        "especial:gestionar_seccion",
        especial_context,
        seccion_id=seccion.pk,
    )
    return {
        "modal_alumno_abierto": request.GET.get("abrir_modal_alumno") == "1",
        "modal_docente_abierto": request.GET.get("abrir_modal_docente") == "1",
        "modal_action_url": gestionar_url,
        "modal_volver_url": gestionar_url,
        "cuil_buscado": cuil_buscado,
        "cuil_error": docente_error if cuil_docente else alumno_error,
        "alumno": alumno,
        "alumno_row": _alumno_row(alumno),
        "alumno_en_banco": alumno_en_banco,
        "alumno_en_seccion": alumno_en_seccion,
        "matricula_compartida_habilitada": False,
        "modal_tiene_seccion": True,
        "docente": docente,
        "docente_row": _docente_row(docente),
        "docente_en_banco": docente_en_banco,
        "cuil_error_docente": docente_error,
        "modal_tiene_grupo": True,
        "docente_form": docente_form,
        "docente_asignacion_activa": asignacion_activa,
        "url_editar_docente": "",
        "url_carga_profesor": "",
    }



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
                filter=Q(alumnos__estado=AlumnoSeccion.Estado.ACTIVO),
                distinct=True,
            ),
            docentes_activos=Count(
                "docentes",
                filter=Q(docentes__estado=DocenteSeccion.Estado.ACTIVO),
                distinct=True,
            ),
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
    context = contexto_base(request, "secciones")
    especial_context = context["especial_context"]

    if request.GET.get("accion") == "agregar":
        return redirect(redirect_con_contexto("especial:carga_seccion_nueva", especial_context))

    secciones = (
        list(_secciones_queryset(especial_context))
        if especial_context["puede_consultar"]
        else []
    )

    context.update(
        {
            "secciones": secciones,
            "total_secciones": len(secciones),
        }
    )
    return render_especial(
        request,
        "especial/carga_seccion_especial.html",
        context,
        "especial/partials/secciones_fragmento_especial.html",
    )


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
    context = contexto_base(request, "secciones")
    especial_context = context["especial_context"]

    if request.method == "POST" and especial_context.get("ciclo_cerrado"):
        messages.error(
            request,
            "El ciclo seleccionado está cerrado y sólo puede consultarse.",
        )
        return redirect(request.get_full_path())

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
        DocenteSeccion.objects.filter(seccion=seccion)
        .order_by("estado", "rol", "docente_nombre_snapshot", "docente_cuil")
    )


def _gestionar_fragment_context(seccion, especial_context):
    inscripciones = list(_inscripciones_seccion(seccion))
    inscripciones_activas = [
        inscripcion
        for inscripcion in inscripciones
        if inscripcion.estado == AlumnoSeccion.Estado.ACTIVO
    ]
    docentes = list(_docentes_seccion(seccion))
    alumnos_ids = [inscripcion.alumno_id for inscripcion in inscripciones]
    try:
        bancos_por_alumno = {
            banco.alumno_id: banco
            for banco in EspecialAlumnoBanco.objects.filter(
                cueanexo=seccion.cueanexo,
                ciclo=seccion.ciclo,
                alumno_id__in=alumnos_ids,
                estado=EspecialAlumnoBanco.Estado.ACTIVO,
            )
        } if alumnos_ids else {}
    except (OperationalError, ProgrammingError):
        bancos_por_alumno = {}
    for inscripcion in inscripciones:
        banco = bancos_por_alumno.get(inscripcion.alumno_id)
        inscripcion.cueanexo_matricula_compartida = (
            banco.matricula_compartida if banco else ""
        )
    try:
        mostrar_cueanexo_matricula = cueanexo_tiene_oferta_matricula_compartida(
            seccion.cueanexo
        )
    except (OperationalError, ProgrammingError):
        mostrar_cueanexo_matricula = False
    docentes_activos = [
        docente for docente in docentes if docente.estado == DocenteSeccion.Estado.ACTIVO
    ]
    return {
        "especial_context": especial_context,
        "seccion": seccion,
        "inscripciones": inscripciones,
        "inscripciones_activas": inscripciones_activas,
        "docentes": docentes,
        "docentes_activos": docentes_activos,
        "gestionar_seccion_modo": True,
        "gestionar_seccion_url": redirect_con_contexto("especial:gestionar_seccion", especial_context, seccion_id=seccion.pk),
        "docentes_activos_count": len(docentes_activos),
        "mostrar_cueanexo_matricula": mostrar_cueanexo_matricula,
    }


def _ajax_gestionar_fragment_response(
    request,
    seccion,
    especial_context,
    ok,
    message,
    reload_page=False,
):
    # Renderizar siempre con la instancia y las relaciones recién consultadas.
    seccion.refresh_from_db()
    context = _gestionar_fragment_context(seccion, especial_context)
    inscripciones_html = render_to_string(
        "especial/inscripciones_seccion_lista_especial.html",
        context,
        request=request,
    )
    return JsonResponse(
        {
            "ok": ok,
            "message": message,
            "reload_page": reload_page and ok,
            "fragment_selector": "[data-cef-fragment='inscripciones-seccion']",
            "fragment_html": inscripciones_html,
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
                    "html": inscripciones_html,
                },
                {
                    "selector": "[data-cef-fragment='docentes-seccion']",
                    "html": render_to_string(
                        "especial/docentes_seccion_lista_especial.html",
                        context,
                        request=request,
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
        dar_alta_inscripcion_seccion(
            inscripcion,
            request.user,
            seccion_queryset=SeccionEspecial.objects.filter(
                cueanexo=seccion.cueanexo,
                ciclo=seccion.ciclo,
            ),
            alumno_banco_queryset=EspecialAlumnoBanco.objects.filter(
                cueanexo=seccion.cueanexo,
                ciclo=seccion.ciclo,
            ),
        )
        return True, "Alumno reinscripto correctamente."
    except ValidationError as exc:
        return False, "; ".join(exc.messages)


def _baja_docente_gestionar(request, seccion):
    try:
        docente_grupo_id = int(request.POST.get("docente_grupo_id"))
    except (TypeError, ValueError):
        return False, "La asignación seleccionada no es válida."

    try:
        with transaction.atomic():
            asignacion = (
                DocenteSeccion.objects
                .select_for_update()
                .filter(pk=docente_grupo_id, seccion_id=seccion.pk)
                .first()
            )
            if asignacion is None:
                return False, "La asignación seleccionada no pertenece a esta sección."
            if asignacion.estado != DocenteSeccion.Estado.ACTIVO:
                return False, "La asignación seleccionada ya no está activa."
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
        DocenteSeccion.objects.filter(seccion=seccion),
        pk=docente_grupo_id,
    )
    try:
        dar_alta_docente_seccion(asignacion, request.user)
        return True, "Profesor reasignado a la sección correctamente."
    except ValidationError as exc:
        return False, "; ".join(exc.messages)


def _alta_docente_nuevo_gestionar(request, seccion):
    """Create a new DocenteSeccion assignment for a docente identified by CUIL.
    Expected POST fields: cuil, rol, estado, fecha_desde, fecha_hasta, observaciones.
    """
    cuil = request.POST.get("cuil")
    if not cuil:
        return False, "CUIL del docente no proporcionado."
    # Create a new assignment instance
    asignacion = DocenteSeccion(seccion=seccion, docente_cuil=cuil)
    form = EspecialDocenteSeccionForm(request.POST, instance=asignacion)
    if form.is_valid():
        asignacion = form.save(commit=False)
        asignacion.seccion = seccion
        asignacion.creado_por = request.user
        asignacion.actualizado_por = request.user
        try:
            with transaction.atomic():
                asignacion.save()
            return True, "Profesor asignado a la sección correctamente."
        except ValidationError as exc:
            return False, "; ".join(exc.messages)
        except IntegrityError:
            return False, "No se pudo asignar el profesor porque ya existe una asignación compatible."
    else:
        return False, _errores_form(form)


@especial_required
def gestionar_seccion(request, seccion_id):
    """Vista de gestión integral de una sección."""
    context = contexto_base(request, "secciones", "Gestionar sección")
    especial_context = context["especial_context"]

    if request.method == "POST" and especial_context.get("ciclo_cerrado"):
        messages.error(
            request,
            "El ciclo seleccionado está cerrado y sólo puede consultarse.",
        )
        return redirect(request.get_full_path())

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
            docente_grupo_id = request.POST.get("docente_grupo_id")
            if docente_grupo_id:
                ok, message = _alta_docente_gestionar(request, seccion)
            else:
                ok, message = _alta_docente_nuevo_gestionar(request, seccion)
            if _is_ajax(request):
                return _ajax_gestionar_fragment_response(
                    request,
                    seccion,
                    especial_context,
                    ok,
                    message,
                )
        elif accion == "asignar_seccion":
            # Assign a docente to the section using CUIL (new assignment)
            ok, message = _alta_docente_nuevo_gestionar(request, seccion)
            if _is_ajax(request):
                return _ajax_gestionar_fragment_response(
                    request,
                    seccion,
                    especial_context,
                    ok,
                    message,
                )
        elif accion == "inscribir_alumno":
            cuil = _solo_digitos(request.POST.get("cuil"))
            alumno = _buscar_alumno(cuil)
            if not alumno:
                ok, message = False, "No se encontró el alumno indicado."
            else:
                try:
                    _, creada = crear_inscripcion_activa(
                        seccion=seccion,
                        alumno=alumno,
                        user=request.user,
                        seccion_queryset=SeccionEspecial.objects.filter(
                            cueanexo=seccion.cueanexo,
                            ciclo=seccion.ciclo,
                        ),
                        alumno_banco_queryset=EspecialAlumnoBanco.objects.filter(
                            cueanexo=seccion.cueanexo,
                            ciclo=seccion.ciclo,
                        ),
                    )
                    ok = True
                    message = (
                        "Alumno inscripto correctamente."
                        if creada
                        else "La inscripción del alumno fue reactivada correctamente."
                    )
                except ValidationError as exc:
                    ok, message = False, "; ".join(exc.messages)
                except IntegrityError:
                    ok, message = False, "No se pudo crear la inscripción."
            if _is_ajax(request):
                return _ajax_gestionar_fragment_response(
                    request,
                    seccion,
                    especial_context,
                    ok,
                    message,
                    reload_page=True,
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
    context.update(_preparar_modales_gestionar(request, seccion, especial_context))
    return render(request, "especial/gestionar_seccion_especial.html", context)
