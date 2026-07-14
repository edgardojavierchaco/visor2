# apps/especial/views_docentes.py
# -*- coding: utf-8 -*-
import re
from urllib.parse import urlencode
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.utils import OperationalError, ProgrammingError
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.template.loader import render_to_string
from django.urls import reverse
from .forms import EspecialBusquedaDocenteForm, EspecialDocenteSeccionForm
from .models import (
    EspecialDocenteBanco,
    DocenteSeccion,
    SeccionEspecial,
)
from .permisos import especial_required
from .views_contexto import contexto_base

# URL externa para carga de personal (ajustar según tu proyecto real)
URL_CARGA_PERSONAL = "/bnh/carga-personal/" 
MSG_BANCO_DOCENTES_PENDIENTE = (
    "El banco de docentes de Educación Especial está pendiente de creación en base de datos."
)

def _solo_digitos(valor):
    return re.sub(r"\D", "", str(valor or ""))

def _is_ajax(request):
    return request.headers.get("x-requested-with") == "XMLHttpRequest"

def _buscar_docente_bnh(cuil):
    """
    Busca en bnhpersonas o la tabla que uses para docentes.
    NOTA: Debes conectar esto con tu modelo real de personas/docentes.
    Por ahora retorna None si no hay integración directa.
    """
    # from apps.bnhpersonas.models import Persona
    # return Persona.objects.filter(cuil=cuil).first()
    return None 

def _docente_row(docente):
    if not docente:
        return None
    return {
        "apellido": getattr(docente, "apellido", "") or "",
        "nombre": getattr(docente, "nombre", "") or "",
        "cuil": getattr(docente, "cuil", "") or "",
        "dni": getattr(docente, "dni", "") or "",
    }

def _docentes_banco(especial_context):
    if not especial_context["puede_operar"]:
        return EspecialDocenteBanco.objects.none()
    return (
        EspecialDocenteBanco.objects.filter(
            cueanexo=especial_context["cueanexo"],
            ciclo=especial_context["ciclo"],
        )
        .order_by("docente_nombre_snapshot", "docente_cuil")
    )

def _asignaciones_por_docente(especial_context, docentes_banco):
    cuiles = [item.docente_cuil for item in docentes_banco]
    if not cuiles:
        return {}
    asignaciones = (
        DocenteSeccion.objects.filter(
            grupo__cueanexo=especial_context["cueanexo"],
            grupo__ciclo=especial_context["ciclo"],
            docente_cuil__in=cuiles,
        )
        .select_related("grupo", "grupo__cd_tipo_seccion")
        .order_by("grupo__nombre_seccion", "rol")
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

def _docente_en_banco_activo(docente_cuil, especial_context):
    if not docente_cuil or not especial_context["puede_operar"]:
        return False
    return EspecialDocenteBanco.objects.filter(
        cueanexo=especial_context["cueanexo"],
        ciclo=especial_context["ciclo"],
        docente_cuil=docente_cuil,
        estado=EspecialDocenteBanco.Estado.ACTIVO,
    ).exists()

def _asegurar_docente_banco(docente_cuil, nombre_docente, especial_context, user):
    if not docente_cuil or not especial_context["puede_operar"]:
        return None, False, False
    try:
        existente = EspecialDocenteBanco.objects.filter(
            cueanexo=especial_context["cueanexo"],
            ciclo=especial_context["ciclo"],
            docente_cuil=docente_cuil,
            estado=EspecialDocenteBanco.Estado.ACTIVO,
        ).first()
        if existente:
            return existente, False, False
        with transaction.atomic():
            banco = EspecialDocenteBanco.objects.create(
                cueanexo=especial_context["cueanexo"],
                ciclo=especial_context["ciclo"],
                docente_cuil=docente_cuil,
                docente_nombre_snapshot=nombre_docente,
                estado=EspecialDocenteBanco.Estado.ACTIVO,
                creado_por=user,
                actualizado_por=user,
            )
            return banco, True, False
    except (OperationalError, ProgrammingError):
        return None, False, True

def _url_carga_docente(cuil, next_url=None, return_label="Volver a Docentes"):
    params = {}
    if cuil:
        params["cuil"] = cuil
    if next_url:
        params["next"] = next_url
    if return_label:
        params["return_label"] = return_label
    return f"{URL_CARGA_PERSONAL}?{urlencode(params)}" if params else URL_CARGA_PERSONAL

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

@especial_required
def docentes(request):
    context = contexto_base(request, "docentes", "Docentes Educación Especial")
    especial_context = context["especial_context"]
    
    cuil_buscado = ""
    cuil_error = ""
    docente_en_banco = False
    abrir_modal = request.GET.get("abrir_modal_docente") == "1"
    
    # Simulación de datos si no hay búsqueda activa
    docente_data = None 

    if request.method == "POST":
        busqueda_form = EspecialBusquedaDocenteForm(request.POST)
        abrir_modal = True
        if busqueda_form.is_valid():
            cuil_buscado = busqueda_form.cleaned_data["cuil"]
            # Intentar buscar en BD real si está configurado
            docente_data = _buscar_docente_bnh(cuil_buscado)
            if not docente_data:
                 # Fallback para pruebas si no hay BD conectada aún
                 docente_data = {"cuil": cuil_buscado, "nombre": "Docente Buscado"} 
        else:
            cuil_buscado = _solo_digitos(request.POST.get("cuil"))
            cuil_error = _errores_form(busqueda_form)

        if not docente_data:
            messages.error(request, "Primero buscá un docente existente por CUIL.")
        elif not especial_context["puede_operar"]:
            messages.error(
                request,
                "Seleccioná un CUE-Anexo y un ciclo lectivo para agregar docentes al banco.",
            )
        else:
            nombre_docente = docente_data.get("nombre", "") if isinstance(docente_data, dict) else getattr(docente_data, 'nombre', '')
            try:
                banco, creado, tabla_pendiente = _asegurar_docente_banco(
                    cuil_buscado,
                    nombre_docente,
                    especial_context,
                    request.user,
                )
                docente_en_banco = bool(banco)
                if tabla_pendiente:
                    messages.error(request, MSG_BANCO_DOCENTES_PENDIENTE)
                elif creado:
                    messages.success(request, "Docente agregado al banco de Educación Especial.")
                    return redirect(_url_docentes(especial_context))
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
            docente_data = _buscar_docente_bnh(cuil_buscado)
            if not docente_data:
                 docente_data = {"cuil": cuil_buscado, "nombre": "Docente Buscado"}
        elif request.GET.get("cuil"):
            cuil_buscado = _solo_digitos(request.GET.get("cuil"))
            cuil_error = _errores_form(busqueda_form)

    next_url = _url_modal_docentes(especial_context, cuil_buscado)
    url_docentes = _url_docentes(especial_context)
    
    docentes_banco_tabla_pendiente = False
    try:
        docentes_banco = list(_docentes_banco(especial_context))
        if cuil_buscado and not docente_en_banco:
            docente_en_banco = _docente_en_banco_activo(cuil_buscado, especial_context)
    except (OperationalError, ProgrammingError):
        docentes_banco = []
        docentes_banco_tabla_pendiente = True

    try:
        asignaciones_por_docente = _asignaciones_por_docente(especial_context, docentes_banco)
    except (OperationalError, ProgrammingError):
        asignaciones_por_docente = {}

    secciones_disponibles = list(_secciones_disponibles(especial_context))
    
    for item in docentes_banco:
        item.asignaciones_seccion = asignaciones_por_docente.get(item.docente_cuil, [])
        asignaciones_activas = [
            asig for asig in item.asignaciones_seccion
            if asig.estado == DocenteSeccion.Estado.ACTIVO
        ]
        secciones_activas_ids = {asig.grupo_id for asig in asignaciones_activas}
        item.secciones_asignables = [
            sec for sec in secciones_disponibles if sec.pk not in secciones_activas_ids
        ]
        item.secciones_bloqueadas = asignaciones_activas

    context.update(
        {
            "busqueda_form": busqueda_form,
            "docente_data": docente_data,
            "docente_row": _docente_row(docente_data) if docente_data else None,
            "docentes": docentes_banco,
            "secciones_disponibles": secciones_disponibles,
            "docentes_banco_tabla_pendiente": docentes_banco_tabla_pendiente,
            "docente_en_banco": docente_en_banco,
            "cuil_buscado": cuil_buscado,
            "cuil_error": cuil_error,
            "url_carga_docente": _url_carga_docente(cuil_buscado, next_url),
            "modal_docente_abierto": abrir_modal,
            "modal_action_url": _url_modal_docentes(especial_context),
            "modal_volver_url": url_docentes,
        }
    )
    return render(request, "especial/docentes_especial.html", context)