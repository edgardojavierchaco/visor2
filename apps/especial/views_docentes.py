# apps/especial/views_docentes.py
# -*- coding: utf-8 -*-
from multiprocessing import context
import logging
import re
from urllib.parse import urlencode

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.utils import OperationalError, ProgrammingError
from django.http import Http404, JsonResponse
from django.shortcuts import redirect, render
from django.template.loader import render_to_string
from django.urls import reverse
from django.shortcuts import get_object_or_404 # Asegúrate de tener este import
from .forms import EspecialBajaDocenteForm, EspecialDocenteSeccionForm

from .forms import EspecialBusquedaDocenteForm
from .models import (
    EspecialDocenteBnh,
    EspecialDocenteBanco,
    DocenteSeccion,
    SeccionEspecial,
    PADRON_DB_ALIAS,
)
from .permisos import especial_required
from .services.docentes_seccion import dar_alta_docente_seccion, dar_baja_docente_seccion
from .services.baja_docentes import dar_baja_docente_banco, preparar_baja_docente
from .views_contexto import contexto_base, redirect_con_contexto, render_especial

URL_CARGA_DOCENTE = "/bnh/carga-personal/"
MSG_BANCO_DOCENTES_PENDIENTE = (
    "El banco de docentes de Educación Especial está pendiente de creación en base de datos."
)
logger = logging.getLogger(__name__)


def _solo_digitos(valor):
    return re.sub(r"\D", "", str(valor or ""))


def _is_ajax(request):
    return request.headers.get("x-requested-with") == "XMLHttpRequest"


def _buscar_docente(cuil):
    return (
        EspecialDocenteBnh.objects.using(PADRON_DB_ALIAS)
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


def _docentes_especial(especial_context):
    if not especial_context["puede_consultar"]:
        return EspecialDocenteBanco.objects.none()

    return (
        EspecialDocenteBanco.objects.filter(
            cueanexo=especial_context["cueanexo"],
            ciclo=especial_context["ciclo"],
        )
        .order_by(
            "docente_nombre_snapshot",
            "docente_cuil",
            "estado",
        )
    )


def _asignaciones_por_docente(especial_context, docentes_banco):
    cuiles = [item.docente_cuil for item in docentes_banco]
    if not cuiles:
        return {}

    asignaciones = (
        DocenteSeccion.objects.filter(
            seccion__cueanexo=especial_context["cueanexo"],
            seccion__ciclo=especial_context["ciclo"],
            docente_cuil__in=cuiles,
        )
        .select_related("seccion", "seccion__cd_tipo_seccion")
        .order_by("seccion__nombre_seccion", "rol")
    )

    por_docente = {}
    for asignacion in asignaciones:
        por_docente.setdefault(asignacion.docente_cuil, []).append(asignacion)
    return por_docente


def _secciones_disponibles(especial_context):
    if not especial_context["puede_operar"]:
        return SeccionEspecial.objects.none()

    return (
        SeccionEspecial.objects.filter(
            cueanexo=especial_context["cueanexo"],
            ciclo=especial_context["ciclo"],
            estado=SeccionEspecial.Estado.ACTIVO,
        )
        .select_related("cd_tipo_seccion", "turno")
        .order_by("nombre_seccion")
    )


def _docente_en_banco_activo(docente, especial_context):
    if not docente or not especial_context["puede_operar"]:
        return False

    return EspecialDocenteBanco.objects.filter(
        cueanexo=especial_context["cueanexo"],
        ciclo=especial_context["ciclo"],
        docente_cuil=docente.cuil,
        estado=EspecialDocenteBanco.Estado.ACTIVO,
    ).exists()


def _docente_banco_seguro(docente_banco_id, especial_context, for_update=False):
    try:
        docente_banco_id = int(docente_banco_id or "")
    except (TypeError, ValueError):
        raise Http404("El docente seleccionado no es válido.")
    if not especial_context["puede_operar"]:
        raise Http404("El docente seleccionado no es válido.")
    queryset = EspecialDocenteBanco.objects.filter(
        pk=docente_banco_id,
        cueanexo=especial_context["cueanexo"],
        ciclo=especial_context["ciclo"],
    )
    if for_update:
        queryset = queryset.select_for_update()
    return get_object_or_404(queryset)


def _preparar_docente_baja(docente_banco, especial_context):
    docente_banco.asignaciones_activas = preparar_baja_docente(
        docente_banco,
        especial_context["cueanexo"],
        especial_context["ciclo"],
    )
    return docente_banco


def _url_baja_docente(especial_context, docente_banco_id):
    params = {}
    if especial_context.get("cueanexo"):
        params["cueanexo"] = especial_context["cueanexo"]
    if especial_context.get("ciclo"):
        params["ciclo"] = especial_context["ciclo"].pk
    params["abrir_modal_baja_docente"] = "1"
    params["docente_banco_id"] = docente_banco_id
    return f"{reverse('especial:docentes')}?{urlencode(params)}"


def _asegurar_docente_banco(docente, especial_context, user):
    if not docente or not especial_context["puede_operar"]:
        return None, False, False

    try:
        existente = EspecialDocenteBanco.objects.filter(
            cueanexo=especial_context["cueanexo"],
            ciclo=especial_context["ciclo"],
            docente_cuil=docente.cuil,
            estado=EspecialDocenteBanco.Estado.ACTIVO,
        ).first()
        if existente:
            return existente, False, False

        with transaction.atomic():
            banco = EspecialDocenteBanco.objects.create(
                cueanexo=especial_context["cueanexo"],
                ciclo=especial_context["ciclo"],
                docente_cuil=docente.cuil,
                estado=EspecialDocenteBanco.Estado.ACTIVO,
                creado_por=user,
                actualizado_por=user,
            )
        return banco, True, False
    except (OperationalError, ProgrammingError):
        return None, False, True


def _url_carga_docente(cuil, next_url=None, return_label="Volver a Especial"):
    params = {}
    if cuil:
        params["cuil"] = cuil
    if next_url:
        params["next"] = next_url
    if return_label:
        params["return_label"] = return_label
    return f"{URL_CARGA_DOCENTE}?{urlencode(params)}" if params else URL_CARGA_DOCENTE


def _url_modal_docentes(especial_context, cuil=""):
    params = {}
    if especial_context.get("cueanexo"):
        params["cueanexo"] = especial_context["cueanexo"]
    if especial_context.get("ciclo"):
        params["ciclo"] = especial_context["ciclo"].pk
    params["abrir_modal_docente"] = "1"
    if cuil:
        params["cuil"] = cuil
    return f"{reverse('especial:docentes')}?{urlencode(params)}"


def _url_docentes(especial_context):
    params = {}
    if especial_context.get("cueanexo"):
        params["cueanexo"] = especial_context["cueanexo"]
    if especial_context.get("ciclo"):
        params["ciclo"] = especial_context["ciclo"].pk
    querystring = urlencode(params)
    url = reverse("especial:docentes")
    return f"{url}?{querystring}" if querystring else url


def _errores_form(form):
    return " ".join(error for errors in form.errors.values() for error in errors)


def _docentes_fragment_context(especial_context, url_docentes):
    """Arma el contexto mínimo para refrescar la tabla de Docentes."""
    docentes = list(_docentes_especial(especial_context))
    asignaciones_por_docente = _asignaciones_por_docente(especial_context, docentes)
    secciones_disponibles = list(_secciones_disponibles(especial_context))

    for item in docentes:
        item.asignaciones_seccion = asignaciones_por_docente.get(item.docente_cuil, [])
        asignaciones_activas = [
            asignacion
            for asignacion in item.asignaciones_seccion
            if asignacion.estado == DocenteSeccion.Estado.ACTIVO
        ]
        item.secciones_asignadas = [
            asignacion
            for asignacion in item.asignaciones_seccion
            if asignacion.estado in {
                DocenteSeccion.Estado.ACTIVO,
                DocenteSeccion.Estado.INACTIVO,
            }
        ]
        secciones_activas_ids = {asignacion.seccion_id for asignacion in asignaciones_activas}
        item.secciones_asignables = [
            seccion
            for seccion in secciones_disponibles
            if seccion.pk not in secciones_activas_ids
        ]
        item.secciones_bloqueadas = asignaciones_activas
        item.url_baja_docente = _url_baja_docente(especial_context, item.pk)
        item.url_editar_docente = _url_carga_docente(
            item.docente_cuil,
            url_docentes,
            "Volver a Docentes Especial",
        )

    return {
        "docentes": docentes,
        "especial_context": especial_context,
        "secciones_disponibles": secciones_disponibles,
        "docente_roles": DocenteSeccion.Rol.choices,
    }


def _docentes_fragment_response(request, especial_context, url_docentes):
    fragment_context = _docentes_fragment_context(especial_context, url_docentes)
    html_tabla = render_to_string(
        "especial/partials/docentes_tabla_especial.html",
        fragment_context,
        request=request,
    )
    return JsonResponse({
        "fragment_html": html_tabla,
        "fragment_selector": "[data-cef-fragment='profesores-banco']",
    })


@especial_required
def editar_docente_seccion(request, seccion_id, docente_id):
    """Vista para editar la asignación de un docente a una sección."""
    context = contexto_base(request, "secciones", "Editar asignación docente")
    especial_context = context["especial_context"]

    if request.method == "POST" and especial_context.get("ciclo_cerrado"):
        messages.error(
            request,
            "El ciclo seleccionado está cerrado y sólo puede consultarse.",
        )
        return redirect(request.get_full_path())
    
    if not especial_context["puede_operar"]:
        messages.warning(request, "Seleccioná un CUE-Anexo y un ciclo para operar.")
        return redirect("especial:docentes")

    seccion = get_object_or_404(
        SeccionEspecial.objects.filter(
            cueanexo=especial_context["cueanexo"],
            ciclo=especial_context["ciclo"]
        ),
        pk=seccion_id
    )

    asignacion = get_object_or_404(
        DocenteSeccion.objects.filter(
            seccion=seccion,
            pk=docente_id
        )
    )

    volver_gestionar = (
        request.GET.get("volver") == "gestionar"
        or request.POST.get("volver") == "gestionar"
    )
    volver_docentes = (
        request.GET.get("volver") == "docentes"
        or request.POST.get("volver") == "docentes"
    )
    volver_url = (
        redirect_con_contexto(
            "especial:gestionar_seccion",
            especial_context,
            seccion_id=seccion.pk,
        )
        if volver_gestionar or not volver_docentes
        else _url_docentes(especial_context)
    )

    if request.method == "POST":
        form = EspecialDocenteSeccionForm(request.POST, instance=asignacion)
        if form.is_valid():
            if form.rol_sin_cambios:
                bancos = list(
                    EspecialDocenteBanco.objects.filter(
                        cueanexo=especial_context["cueanexo"],
                        ciclo=especial_context["ciclo"],
                        docente_cuil=asignacion.docente_cuil,
                        estado=EspecialDocenteBanco.Estado.ACTIVO,
                    )
                )
                banco = max(bancos, key=lambda item: item.pk, default=None)
                if banco:
                    params = {
                        "abrir_modal_asignaciones": "1",
                        "modal_asignaciones_docente_id": banco.pk,
                        "asignacion_sin_cambios_id": asignacion.pk,
                    }
                    return redirect(
                        f"{_url_docentes(especial_context)}&{urlencode(params)}"
                    )
                return redirect(_url_docentes(especial_context))
            try:
                form.save()
            except IntegrityError:
                messages.error(
                    request,
                    "No se pudo actualizar la asignación porque existe un conflicto de integridad.",
                )
            else:
                messages.success(request, "Asignación actualizada correctamente.")
                return redirect(volver_url)
    else:
        form = EspecialDocenteSeccionForm(instance=asignacion)

    context.update({
        "form": form,
        "seccion": seccion,
        "asignacion": asignacion,
        "volver_url": volver_url,
        "volver_gestionar": volver_gestionar,
        "volver_docentes": volver_docentes,
    })
    return render(request, "especial/docente_seccion_form_especial.html", context)

@especial_required
def docentes(request):
    context = contexto_base(request, "docentes")
    especial_context = context["especial_context"]
    if request.method == "POST" and especial_context.get("ciclo_cerrado"):
        messages.error(
            request,
            "El ciclo seleccionado está cerrado y sólo puede consultarse.",
        )
        return redirect(request.get_full_path())

    docente = None
    cuil_buscado = ""
    cuil_error = ""
    docente_en_banco = False
    abrir_modal_asignaciones = request.GET.get("abrir_modal_asignaciones") == "1"
    try:
        modal_asignaciones_docente_id = int(
            request.GET.get("modal_asignaciones_docente_id") or ""
        )
    except (TypeError, ValueError):
        modal_asignaciones_docente_id = None
    try:
        asignacion_sin_cambios_id = int(
            request.GET.get("asignacion_sin_cambios_id") or ""
        )
    except (TypeError, ValueError):
        asignacion_sin_cambios_id = None
    abrir_modal_baja = request.GET.get("abrir_modal_baja_docente") == "1"
    abrir_modal = request.GET.get("abrir_modal_docente") == "1"
    if abrir_modal_baja:
        abrir_modal = False
    elif abrir_modal_asignaciones:
        abrir_modal = False
    baja_modal_docente = None
    baja_form = EspecialBajaDocenteForm(
        cueanexo_origen=especial_context.get("cueanexo"),
        ciclo_origen=especial_context.get("ciclo"),
    )
    baja_error = ""
    baja_asignaciones_activas = []
    url_docentes = _url_docentes(especial_context)

    if request.method == "POST":
        accion = request.POST.get("accion")

        if accion == "baja_docente_especial":
            abrir_modal = False
            if not especial_context["puede_operar"]:
                messages.warning(request, "Seleccioná un CUE-Anexo y un ciclo para operar.")
                return redirect(url_docentes)
            banco = _docente_banco_seguro(request.POST.get("docente_banco_id"), especial_context)
            baja_modal_docente = _preparar_docente_baja(banco, especial_context)
            baja_asignaciones_activas = list(baja_modal_docente.asignaciones_activas)
            baja_form = EspecialBajaDocenteForm(
                request.POST,
                cueanexo_origen=especial_context.get("cueanexo"),
                ciclo_origen=especial_context.get("ciclo"),
            )
            if banco.estado != EspecialDocenteBanco.Estado.ACTIVO:
                baja_error = "El docente ya no se encuentra activo en este establecimiento y ciclo."
            elif baja_modal_docente.asignaciones_activas:
                baja_error = "No se puede dar de baja al docente mientras conserve cargos o secciones activas en este establecimiento y ciclo."
            elif baja_form.is_valid():
                try:
                    dar_baja_docente_banco(
                        banco_id=banco.pk,
                        cueanexo=especial_context["cueanexo"],
                        ciclo=especial_context["ciclo"],
                        user=request.user,
                        motivo_baja=baja_form.cleaned_data["motivo_baja"],
                        observaciones=baja_form.cleaned_data.get("observaciones", ""),
                        cueanexo_destino=baja_form.cleaned_data.get("cueanexo_destino", ""),
                        ciclo_destino=baja_form.cleaned_data.get("ciclo_destino"),
                    )
                except ValidationError as exc:
                    baja_error = "; ".join(exc.messages)
                else:
                    messages.success(request, "Docente dado de baja de Especial correctamente.")
                    return redirect(url_docentes)
            else:
                baja_error = _errores_form(baja_form)
            abrir_modal_baja = True

        if accion == "baja_docente":
            if not especial_context["puede_operar"]:
                messages.warning(request, "Seleccioná un CUE-Anexo y un ciclo para operar.")
                return redirect(url_docentes)

            try:
                asignacion_id = int(request.POST.get("docente_seccion_id"))
            except (TypeError, ValueError):
                message = "La asignación seleccionada no es válida."
                if _is_ajax(request):
                    return JsonResponse({"error": message}, status=400)
                messages.error(request, message)
                return redirect(url_docentes)

            asignacion = get_object_or_404(
                DocenteSeccion.objects.filter(
                    pk=asignacion_id,
                    seccion__cueanexo=especial_context["cueanexo"],
                    seccion__ciclo=especial_context["ciclo"],
                )
            )
            try:
                dar_baja_docente_seccion(asignacion, request.user)
            except ValidationError as exc:
                message = "; ".join(exc.messages)
                if _is_ajax(request):
                    return JsonResponse({"error": message}, status=400)
                messages.error(request, message)
            else:
                message = "Asignación dada de baja correctamente."
                if _is_ajax(request):
                    return _docentes_fragment_response(request, especial_context, url_docentes)
                messages.success(request, message)
            return redirect(url_docentes)

        if accion == "asignar_seccion" and especial_context["puede_operar"]:
            
            seccion_id = request.POST.get("seccion_id")
            cuil = request.POST.get("cuil")
            
            if not seccion_id or not cuil:
                if _is_ajax(request):
                    return JsonResponse({"error": "Faltan datos obligatorios."}, status=400)
                messages.error(request, "Faltan datos obligatorios.")
                return redirect(url_docentes)

            try:
                seccion = SeccionEspecial.objects.get(
                    pk=seccion_id, 
                    cueanexo=especial_context["cueanexo"],
                    ciclo=especial_context["ciclo"]
                )
            except SeccionEspecial.DoesNotExist:
                if _is_ajax(request):
                    return JsonResponse({"error": "Sección no encontrada."}, status=404)
                messages.error(request, "Sección no encontrada.")
                return redirect(url_docentes)

            cuil = _solo_digitos(cuil)
            asignaciones_historicas = list(
                DocenteSeccion.objects.filter(
                    seccion=seccion,
                    docente_cuil=cuil,
                    estado__in=[
                        DocenteSeccion.Estado.BAJA,
                        DocenteSeccion.Estado.INACTIVO,
                    ],
                )
                .order_by("-pk")
            )
            asignacion_historica = max(
                asignaciones_historicas,
                key=lambda relacion: relacion.pk,
                default=None,
            )
            asignacion = asignacion_historica or DocenteSeccion(
                seccion=seccion,
                docente_cuil=cuil,
                creado_por=request.user,
                actualizado_por=request.user,
            )
            form_data = request.POST.copy()
            for campo_extra in ['cuil', 'seccion_id', 'accion', 'cueanexo_contexto', 'ciclo_contexto']:
                if campo_extra in form_data:
                    del form_data[campo_extra]

            form = EspecialDocenteSeccionForm(form_data, instance=asignacion)
            
            if form.is_valid():
                try:
                    if asignacion_historica:
                        asignacion = dar_alta_docente_seccion(
                            asignacion,
                            request.user,
                            rol=form.cleaned_data.get("rol"),
                            observaciones=form.cleaned_data.get("observaciones", ""),
                        )
                    else:
                        asignacion = form.save(commit=False)
                        asignacion.seccion = seccion
                        asignacion.docente_cuil = cuil
                        asignacion.creado_por = request.user
                        asignacion.actualizado_por = request.user
                        asignacion.save()
                except ValidationError as e:
                    if _is_ajax(request):
                        return JsonResponse({"error": str(e)}, status=400)
                    messages.error(request, str(e))
                    return redirect(url_docentes)
                except IntegrityError:
                    message = "No se pudo asignar el docente porque ya existe una asignación compatible."
                    if _is_ajax(request):
                        return JsonResponse({"error": message}, status=409)
                    messages.error(request, message)
                    return redirect(url_docentes)
                
                if _is_ajax(request):
                    docentes_actualizados = list(_docentes_especial(especial_context))
                    asignaciones_actualizadas = _asignaciones_por_docente(especial_context, docentes_actualizados)
                    secciones_disp = list(_secciones_disponibles(especial_context))
                    
                    for item in docentes_actualizados:
                        item.asignaciones_seccion = asignaciones_actualizadas.get(item.docente_cuil, [])
                        activas = [a for a in item.asignaciones_seccion if a.estado == DocenteSeccion.Estado.ACTIVO]
                        item.secciones_asignadas = [
                            a for a in item.asignaciones_seccion
                            if a.estado in {
                                DocenteSeccion.Estado.ACTIVO,
                                DocenteSeccion.Estado.INACTIVO,
                            }
                        ]
                        ids_activas = {a.seccion_id for a in activas}
                        item.secciones_asignables = [s for s in secciones_disp if s.pk not in ids_activas]
                        item.secciones_bloqueadas = activas
                        item.url_baja_docente = _url_baja_docente(especial_context, item.pk)
                        item.url_editar_docente = _url_carga_docente(item.docente_cuil, url_docentes, "Volver a Docentes Especial")

                    ctx_fragmento = {
                        "docentes": docentes_actualizados,
                        "especial_context": especial_context,
                        "secciones_disponibles": secciones_disp,
                        "docente_roles": DocenteSeccion.Rol.choices,
                    }
                    
                    html_tabla = render_to_string(
                        "especial/partials/docentes_tabla_especial.html",
                        ctx_fragmento, 
                        request=request
                    )
                    
                    return JsonResponse({
                        "fragment_html": html_tabla,
                        "fragment_selector": "[data-cef-fragment='profesores-banco']",
                        "close_modal": True
                    })
                
                messages.success(request, "Docente asignado correctamente.")
                return redirect(url_docentes)
            else:
                if _is_ajax(request):
                    ctx_modal = {
                        "docente_grupo_form": form,
                        "asignacion_docente_cuil": cuil,
                        "asignacion_grupo_seleccionado": seccion,
                        "especial_context": especial_context,
                    }
                    modal_html = render_to_string(
                        "especial/asignar_docente_seccion_modal_especial.html",
                        ctx_modal,
                        request=request
                    )
                    return JsonResponse({"modal_html": modal_html})
                
                for error in form.errors.values():
                    messages.error(request, " ".join(error))
                return redirect(url_docentes)

        busqueda_form = (
            EspecialBusquedaDocenteForm()
            if accion == "baja_docente_especial"
            else EspecialBusquedaDocenteForm(request.POST)
        )
        abrir_modal = accion != "baja_docente_especial"

        if busqueda_form.is_valid():
            cuil_buscado = busqueda_form.cleaned_data["cuil"]
            docente = _buscar_docente(cuil_buscado)
        else:
            cuil_buscado = _solo_digitos(request.POST.get("cuil"))
            cuil_error = _errores_form(busqueda_form)

        if accion == "baja_docente_especial":
            pass
        elif not docente:
            messages.error(request, "Primero buscá un docente existente por CUIL.")
        elif not especial_context["puede_operar"]:
            messages.error(
                request,
                "Seleccioná un CUE-Anexo y un ciclo lectivo para agregar docentes al banco.",
            )
        else:
            try:
                banco, creado, tabla_pendiente = _asegurar_docente_banco(
                    docente,
                    especial_context,
                    request.user,
                )
                docente_en_banco = bool(banco)
                if tabla_pendiente:
                    messages.error(request, MSG_BANCO_DOCENTES_PENDIENTE)
                elif creado:
                    messages.success(request, "Docente agregado al banco de Educación Especial.")
                    return redirect(url_docentes)
                else:
                    messages.info(
                        request,
                        "Ese docente ya está activo en el banco de este establecimiento y ciclo.",
                    )
            except (IntegrityError, ValidationError):
                messages.error(
                    request,
                    "No se pudo agregar el docente al banco. Verificá que no exista ya activo.",
                )
    else:
        busqueda_form = EspecialBusquedaDocenteForm(
            request.GET if request.GET.get("cuil") else None
        )
        if busqueda_form.is_valid():
            cuil_buscado = busqueda_form.cleaned_data["cuil"]
            docente = _buscar_docente(cuil_buscado)
        elif request.GET.get("cuil"):
            cuil_buscado = _solo_digitos(request.GET.get("cuil"))
            cuil_error = _errores_form(busqueda_form)

    next_url = _url_modal_docentes(especial_context, cuil_buscado)
    url_carga_docente = _url_carga_docente(cuil_buscado, next_url)
    docentes_banco_tabla_pendiente = False

    try:
        docentes = list(_docentes_especial(especial_context))
        if docente and not docente_en_banco:
            docente_en_banco = _docente_en_banco_activo(docente, especial_context)
    except (OperationalError, ProgrammingError):
        docentes = []
        docentes_banco_tabla_pendiente = True

    try:
        asignaciones_por_docente = _asignaciones_por_docente(especial_context, docentes)
    except (OperationalError, ProgrammingError):
        asignaciones_por_docente = {}

    secciones_disponibles = list(_secciones_disponibles(especial_context))

    for item in docentes:
        item.asignaciones_seccion = asignaciones_por_docente.get(item.docente_cuil, [])
        asignaciones_activas = [
            asignacion
            for asignacion in item.asignaciones_seccion
            if asignacion.estado == DocenteSeccion.Estado.ACTIVO
        ]
        item.secciones_asignadas = [
            asignacion
            for asignacion in item.asignaciones_seccion
            if asignacion.estado in {
                DocenteSeccion.Estado.ACTIVO,
                DocenteSeccion.Estado.INACTIVO,
            }
        ]
        secciones_activas_ids = {asignacion.seccion_id for asignacion in asignaciones_activas}
        item.secciones_asignables = [
            seccion for seccion in secciones_disponibles if seccion.pk not in secciones_activas_ids
        ]
        item.secciones_bloqueadas = asignaciones_activas
        item.url_baja_docente = _url_baja_docente(especial_context, item.pk)
        item.url_editar_docente = _url_carga_docente(
            item.docente_cuil,
            url_docentes,
            "Volver a Docentes Especial",
        )

    if abrir_modal_baja and baja_modal_docente is None:
        try:
            baja_modal_docente = _preparar_docente_baja(
                _docente_banco_seguro(request.GET.get("docente_banco_id"), especial_context),
                especial_context,
            )
            baja_asignaciones_activas = list(baja_modal_docente.asignaciones_activas)
        except Exception:
            logger.exception(
                "Error preparando baja de docente: docente_banco_id=%s, cueanexo=%s, ciclo=%s",
                request.GET.get("docente_banco_id"),
                especial_context.get("cueanexo"),
                getattr(especial_context.get("ciclo"), "pk", especial_context.get("ciclo")),
            )
            raise

    docente_grupo_form = EspecialDocenteSeccionForm()
    
    context.update(
        {
            "busqueda_form": busqueda_form,
            "docente": docente,
            "docente_row": _docente_row(docente),
            "docentes": docentes,
            "secciones_disponibles": secciones_disponibles,
            "docentes_banco_tabla_pendiente": docentes_banco_tabla_pendiente,
            "docente_en_banco": docente_en_banco,
            "cuil_buscado": cuil_buscado,
            "cuil_error": cuil_error,
            "url_carga_docente": url_carga_docente,
            "url_editar_docente": url_carga_docente,
            "modal_docente_abierto": abrir_modal,
            "abrir_modal_asignaciones": abrir_modal_asignaciones,
            "modal_asignaciones_docente_id": modal_asignaciones_docente_id,
            "asignacion_sin_cambios_id": asignacion_sin_cambios_id,
            "modal_action_url": _url_modal_docentes(especial_context),
            "modal_volver_url": url_docentes,
            "baja_modal_docente": baja_modal_docente,
            "baja_asignaciones_activas": baja_asignaciones_activas,
            "baja_form": baja_form,
            "baja_error": baja_error,
            "baja_action_url": url_docentes,
            "modal_baja_docente_abierto": abrir_modal_baja,
            "docente_grupo_form": docente_grupo_form,
            "docente_roles": DocenteSeccion.Rol.choices,
        }
    )
    if _is_ajax(request) and abrir_modal_baja:
        try:
            return render(request, "especial/docente_baja_especial_modal.html", context)
        except Exception:
            logger.exception(
                "Error renderizando modal de baja de docente: docente_banco_id=%s, cuil=%s, cueanexo=%s, ciclo=%s, asignaciones=%s",
                request.GET.get("docente_banco_id"),
                getattr(baja_modal_docente, "docente_cuil", None),
                especial_context.get("cueanexo"),
                getattr(especial_context.get("ciclo"), "pk", especial_context.get("ciclo")),
                len(baja_asignaciones_activas),
            )
            raise
    return render_especial(
        request,
        "especial/docentes_especial.html",
        context,
        "especial/partials/docentes_fragmento_especial.html",
    )
