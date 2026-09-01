# apps/especial/views_carga_seccion.py
# -*- coding: utf-8 -*-

from collections import defaultdict
import logging
import re
import unicodedata
from types import SimpleNamespace
from urllib.parse import urlencode

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db import DatabaseError, IntegrityError, transaction
from django.db.utils import OperationalError, ProgrammingError
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

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
    normalizar_cueanexo,
)
from .permisos import especial_required
from .views_contexto import contexto_base, redirect_con_contexto, render_especial
from .services.docentes_seccion import dar_alta_docente_seccion, dar_baja_docente_seccion
from .services.alumnos import (
    inscribir_alumno_en_seccion,
    ultima_matricula_compartida,
)
from .views_inscripcion_seccion import (
    _alumno_row,
    _buscar_alumno,
    _completar_contexto_desde_seccion,
    crear_inscripcion_activa,
    dar_alta_inscripcion_seccion,
    dar_baja_inscripcion_seccion,
)
from .views_docentes import _buscar_docente, _docente_row


logger = logging.getLogger(__name__)

SECCIONES_VISTA_DEFAULT = "actuales"
SECCIONES_VISTAS = {"actuales", "historial"}
SECCIONES_POR_PAGINA = 10
SECCIONES_BUSQUEDA_MAX_LENGTH = 100
SECCIONES_BUSQUEDA_EQUIVALENCIAS = {
    "a": "aáàäâãå",
    "e": "eéèëê",
    "i": "iíìïî",
    "n": "nñ",
    "o": "oóòöôõ",
    "u": "uúùüû",
}


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


def _secciones_vista_param(request):
    vista = (request.GET.get("vista") or SECCIONES_VISTA_DEFAULT).strip().lower()
    return vista if vista in SECCIONES_VISTAS else SECCIONES_VISTA_DEFAULT


def _secciones_busqueda_param(request):
    bruto = " ".join(str(request.GET.get("q") or "").split())
    if not bruto:
        return "", ""
    if len(bruto) > SECCIONES_BUSQUEDA_MAX_LENGTH:
        return (
            "",
            f"El término de búsqueda no puede superar los {SECCIONES_BUSQUEDA_MAX_LENGTH} caracteres.",
        )
    return bruto, ""


def _pagina_secciones_param(request):
    try:
        pagina = int(request.GET.get("page") or 1)
    except (TypeError, ValueError):
        pagina = 1
    return max(pagina, 1)


def _secciones_state_params(
    especial_context,
    *,
    vista=SECCIONES_VISTA_DEFAULT,
    termino="",
    pagina=None,
):
    params = {}
    if especial_context.get("cueanexo"):
        params["cueanexo"] = especial_context["cueanexo"]
    if especial_context.get("ciclo"):
        params["ciclo"] = especial_context["ciclo"].pk
    if vista in SECCIONES_VISTAS:
        params["vista"] = vista
    if termino:
        params["q"] = termino
    if pagina and pagina > 1:
        params["page"] = pagina
    return params


def _url_secciones(
    especial_context,
    *,
    vista=SECCIONES_VISTA_DEFAULT,
    termino="",
    pagina=None,
):
    querystring = urlencode(
        _secciones_state_params(
            especial_context,
            vista=vista,
            termino=termino,
            pagina=pagina,
        )
    )
    url = reverse("especial:carga_seccion")
    return f"{url}?{querystring}" if querystring else url


def _secciones_busqueda_tokens(valor):
    texto = unicodedata.normalize("NFD", str(valor or "")).casefold()
    texto = "".join(
        caracter
        for caracter in texto
        if unicodedata.category(caracter) != "Mn"
    )
    texto = re.sub(r"(\d)[,./-](?=\d)", r"\1", texto)
    return [token for token in re.split(r"[\s,./-]+", texto) if token]


def _secciones_busqueda_patron(token):
    caracteres = []
    for caracter in token:
        equivalencias = SECCIONES_BUSQUEDA_EQUIVALENCIAS.get(caracter)
        caracteres.append(
            f"[{equivalencias}]" if equivalencias else re.escape(caracter)
        )
    return "".join(caracteres)


def _secciones_historial_queryset(especial_context, termino=""):
    if not especial_context["puede_consultar"]:
        return SeccionEspecial.objects.none()

    queryset = SeccionEspecial.objects.filter(
        cueanexo=especial_context["cueanexo"],
    )
    for token in _secciones_busqueda_tokens(termino):
        patron = _secciones_busqueda_patron(token)
        filtros = (
            Q(nombre_seccion__iregex=patron)
            | Q(oferta__iregex=patron)
            | Q(cd_tipo_seccion__descripcion__iregex=patron)
            | Q(tipo_estructura_especial__descripcion__iregex=patron)
            | Q(turno__descripcion__iregex=patron)
            | Q(modalidad__descripcion__iregex=patron)
            | Q(rango_etario__descripcion__iregex=patron)
            | Q(cueanexo__iregex=patron)
        )
        if token.isdigit():
            try:
                numero = int(token)
            except (TypeError, ValueError, OverflowError):
                numero = None
            if numero is not None and numero <= 9223372036854775807:
                filtros |= Q(pk=numero)
                if 1900 <= numero <= 2100:
                    filtros |= Q(ciclo__anio=numero)
        queryset = queryset.filter(filtros)
    return queryset


def _seccion_historial_key(seccion):
    """Identidad operativa de una sección a través de sus ciclos."""
    return (
        seccion.cd_tipo_seccion_id,
        seccion.nombre_seccion or "",
        seccion.oferta or "",
    )


def _secciones_historial_sort_key(key):
    tipo_id, nombre, oferta = key
    nombre_normalizado = unicodedata.normalize("NFD", nombre or "").casefold()
    oferta_normalizada = unicodedata.normalize("NFD", oferta or "").casefold()
    return (
        "".join(c for c in nombre_normalizado if unicodedata.category(c) != "Mn"),
        "".join(c for c in oferta_normalizada if unicodedata.category(c) != "Mn"),
        tipo_id or 0,
    )


def _ultimo_por_clave(asignaciones, clave):
    vistos = set()
    resultado = []
    for asignacion in asignaciones:
        valor = clave(asignacion)
        if valor in vistos:
            continue
        vistos.add(valor)
        resultado.append(asignacion)
    return resultado


def _secciones_historial_paginado(especial_context, queryset, pagina):
    """Agrupa los registros de SeccionEspecial por sección operativa."""
    matching_sections = list(
        queryset.select_related(
            "cd_tipo_seccion",
            "turno",
            "rango_etario",
            "modalidad",
            "tipo_estructura_especial",
            "ciclo",
        ).order_by(
            "nombre_seccion",
            "oferta",
            "cd_tipo_seccion_id",
            "-ciclo__anio",
            "-pk",
        )
    )
    keys = sorted(
        {_seccion_historial_key(seccion) for seccion in matching_sections},
        key=_secciones_historial_sort_key,
    )
    page_obj = Paginator(keys, SECCIONES_POR_PAGINA).get_page(pagina)
    page_keys = list(page_obj.object_list)
    if not page_keys:
        return [], page_obj

    key_filter = Q()
    for tipo_id, nombre, oferta in page_keys:
        key_filter |= Q(
            cd_tipo_seccion_id=tipo_id,
            nombre_seccion=nombre,
            oferta=oferta,
        )
    sections = list(
        SeccionEspecial.objects.filter(
            cueanexo=especial_context["cueanexo"],
        )
        .filter(key_filter)
        .select_related(
            "cd_tipo_seccion",
            "turno",
            "rango_etario",
            "modalidad",
            "tipo_estructura_especial",
            "ciclo",
        )
        .order_by("nombre_seccion", "oferta", "-ciclo__anio", "-pk")
    )
    section_ids = [seccion.pk for seccion in sections]
    alumnos = list(
        AlumnoSeccion.objects.filter(seccion_id__in=section_ids)
        .select_related("seccion", "alumno")
        .order_by(
            "seccion_id",
            "alumno__apellidos",
            "alumno__nombres",
            "-fecha_inscripcion",
            "-pk",
        )
    ) if section_ids else []
    docentes = list(
        DocenteSeccion.objects.filter(seccion_id__in=section_ids)
        .select_related("seccion")
        .order_by(
            "seccion_id",
            "docente_nombre_snapshot",
            "docente_cuil",
            "-pk",
        )
    ) if section_ids else []

    alumnos_por_seccion = defaultdict(list)
    for alumno in alumnos:
        alumnos_por_seccion[alumno.seccion_id].append(alumno)
    docentes_por_seccion = defaultdict(list)
    for docente in docentes:
        docentes_por_seccion[docente.seccion_id].append(docente)

    secciones_por_clave = defaultdict(list)
    for seccion in sections:
        secciones_por_clave[_seccion_historial_key(seccion)].append(seccion)
    ciclo_seleccionado_id = getattr(especial_context.get("ciclo"), "pk", None)
    items = []
    for key in page_keys:
        periodos = []
        for seccion in secciones_por_clave[key]:
            inscripciones = _ultimo_por_clave(
                alumnos_por_seccion.get(seccion.pk, []),
                lambda item: item.alumno_id,
            )
            asignaciones = _ultimo_por_clave(
                docentes_por_seccion.get(seccion.pk, []),
                lambda item: item.docente_cuil,
            )
            periodos.append(
                SimpleNamespace(
                    seccion=seccion,
                    inscripciones=inscripciones,
                    asignaciones=asignaciones,
                )
            )
        seccion_actual = next(
            (
                periodo.seccion
                for periodo in periodos
                if periodo.seccion.ciclo_id == ciclo_seleccionado_id
            ),
            periodos[0].seccion,
        )
        items.append(
            SimpleNamespace(
                historial_key=key,
                seccion=seccion_actual,
                historial_periodos=periodos,
            )
        )
    return items, page_obj


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
    es_integracion = seccion.es_oferta_integracion
    ultima_matricula = (
        ultima_matricula_compartida(alumno, excluir_cueanexo=seccion.cueanexo)
        if alumno and es_integracion
        else None
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
        "matricula_compartida_habilitada": es_integracion,
        "matricula_compartida_busqueda_url": reverse(
            "especial:buscar_cueanexos_matricula_compartida"
        ) + f"?seccion_id={seccion.pk}",
        "seccion_es_oferta_integracion": es_integracion,
        "ultima_matricula_compartida": ultima_matricula,
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
            "ciclo",
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
    vista = _secciones_vista_param(request)
    termino_busqueda, busqueda_error = _secciones_busqueda_param(request)
    pagina_solicitada = _pagina_secciones_param(request)

    if request.method == "POST" and vista != SECCIONES_VISTA_DEFAULT:
        messages.error(request, "El historial es consultivo y no admite operaciones.")
        return redirect(
            _url_secciones(
                especial_context,
                vista=vista,
                termino=termino_busqueda,
                pagina=pagina_solicitada,
            )
        )

    if request.GET.get("accion") == "agregar" and vista == SECCIONES_VISTA_DEFAULT:
        return redirect(redirect_con_contexto("especial:carga_seccion_nueva", especial_context))

    secciones = (
        list(_secciones_queryset(especial_context))
        if especial_context["puede_consultar"] and vista == SECCIONES_VISTA_DEFAULT
        else []
    )
    secciones_historial = []
    page_obj_secciones = Paginator([], SECCIONES_POR_PAGINA).get_page(1)
    if vista == "historial" and not busqueda_error:
        secciones_historial, page_obj_secciones = _secciones_historial_paginado(
            especial_context,
            _secciones_historial_queryset(especial_context, termino_busqueda),
            pagina_solicitada,
        )

    pagina_estado = pagina_solicitada if vista == "historial" else None
    actuales_url = _url_secciones(
        especial_context,
        vista=SECCIONES_VISTA_DEFAULT,
        termino=termino_busqueda,
    )
    historial_url = _url_secciones(
        especial_context,
        vista="historial",
        termino=termino_busqueda,
        pagina=1,
    )
    pagina_anterior_secciones_url = (
        _url_secciones(
            especial_context,
            vista="historial",
            termino=termino_busqueda,
            pagina=page_obj_secciones.previous_page_number(),
        )
        if vista == "historial" and page_obj_secciones.has_previous()
        else ""
    )
    pagina_siguiente_secciones_url = (
        _url_secciones(
            especial_context,
            vista="historial",
            termino=termino_busqueda,
            pagina=page_obj_secciones.next_page_number(),
        )
        if vista == "historial" and page_obj_secciones.has_next()
        else ""
    )

    context.update(
        {
            "secciones": secciones,
            "total_secciones": len(secciones),
            "secciones_historial": secciones_historial,
            "total_secciones_historial": page_obj_secciones.paginator.count,
            "actuales_secciones_url": actuales_url,
            "historial_secciones_url": historial_url,
            "modo_historial_secciones": vista == "historial",
            "vista_secciones": vista,
            "termino_busqueda_secciones": termino_busqueda,
            "busqueda_error_secciones": busqueda_error,
            "page_obj_secciones": page_obj_secciones,
            "pagina_anterior_secciones_url": pagina_anterior_secciones_url,
            "pagina_siguiente_secciones_url": pagina_siguiente_secciones_url,
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

    es_edicion = seccion_id is not None
    seccion = _seccion_segura(seccion_id, especial_context) if es_edicion else None

    if seccion is None:
        seccion = SeccionEspecial(
            cueanexo=especial_context["cueanexo"],
            ciclo=especial_context["ciclo"]
        )

    if request.method == "POST":
        form = EspecialSeccionForm(
            request.POST,
            instance=seccion,
            ciclo=especial_context["ciclo"],
            cueanexo=especial_context["cueanexo"],
        )

        if form.is_valid():
            _guardar_seccion(form, especial_context, request.user)
            messages.success(request, "Sección guardada correctamente.")
            return redirect(redirect_con_contexto("especial:carga_seccion", especial_context))

        messages.error(request, "Revisá los datos del formulario para guardar la sección.")
    else:
        form = EspecialSeccionForm(
            instance=seccion,
            ciclo=especial_context["ciclo"],
            cueanexo=especial_context["cueanexo"],
        )

    context.update(
        {
            "form": form,
            "seccion_edicion": seccion if es_edicion else None,
            "form_title": "Editar Sección" if es_edicion else "Agregar Sección",
            "oferta_educativa_sin_configurar": form.oferta_educativa_sin_configurar,
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
    mostrar_cueanexo_matricula = seccion.es_oferta_integracion
    gestionar_seccion_url = redirect_con_contexto(
        "especial:gestionar_seccion",
        especial_context,
        seccion_id=seccion.pk,
    )
    for inscripcion in inscripciones:
        params = urlencode(
            {
                "abrir_modal_alumno": "1",
                "cuil": getattr(inscripcion.alumno, "cuil", ""),
            }
        )
        separador = "&" if "?" in gestionar_seccion_url else "?"
        inscripcion.reinscripcion_url = f"{gestionar_seccion_url}{separador}{params}"
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
        "gestionar_seccion_url": gestionar_seccion_url,
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
    asignacion_existente = (
        DocenteSeccion.objects
        .filter(seccion=seccion, docente_cuil=cuil)
        .order_by("-creado_en", "-id")
        .first()
    )
    if asignacion_existente and asignacion_existente.estado == DocenteSeccion.Estado.ACTIVO:
        return False, "El docente ya está asignado activamente a esta sección."

    # Reutilizar la relación existente evita crear otra fila para el mismo
    # docente y sección cuando se reactiva o cambia su estado.
    asignacion = asignacion_existente or DocenteSeccion(
        seccion=seccion,
        docente_cuil=cuil,
    )
    form = EspecialDocenteSeccionForm(request.POST, instance=asignacion)
    if form.is_valid():
        asignacion = form.save(commit=False)
        asignacion.seccion = seccion
        if not asignacion.pk:
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
    _completar_contexto_desde_seccion(request, seccion_id, especial_context)

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
            cueanexo_asociado_recibido = str(
                request.POST.get("cueanexo_matricula_compartida") or ""
            ).strip()
            alumno = _buscar_alumno(cuil)
            if not alumno:
                ok, message = False, "No se encontró el alumno indicado."
            else:
                logger.info(
                    "Inscripción Especial desde gestión recibida: seccion_id=%s "
                    "cue_especial=%s ciclo_id=%s cuil=%s cue_asociado=%s",
                    seccion.pk,
                    seccion.cueanexo,
                    seccion.ciclo_id,
                    cuil,
                    normalizar_cueanexo(cueanexo_asociado_recibido)
                    or cueanexo_asociado_recibido,
                )
                try:
                    _, creada, _ = inscribir_alumno_en_seccion(
                        seccion=seccion,
                        alumno=alumno,
                        user=request.user,
                        cueanexo_asociado=cueanexo_asociado_recibido,
                    )
                    ok = True
                    message = (
                        "Alumno inscripto correctamente."
                        if creada
                        else "La inscripción del alumno fue reactivada correctamente."
                    )
                except ValidationError as exc:
                    ok, message = False, "; ".join(exc.messages)
                    logger.warning(
                        "Inscripción Especial desde gestión rechazada: seccion_id=%s "
                        "cuil=%s cue_asociado=%s motivo=%s",
                        seccion.pk,
                        cuil,
                        normalizar_cueanexo(cueanexo_asociado_recibido)
                        or cueanexo_asociado_recibido,
                        message,
                    )
                except IntegrityError:
                    ok, message = False, "No se pudo crear la inscripción."
                    logger.exception(
                        "Inscripción Especial desde gestión rechazada por integridad: "
                        "seccion_id=%s cuil=%s cue_asociado=%s",
                        seccion.pk,
                        cuil,
                        normalizar_cueanexo(cueanexo_asociado_recibido)
                        or cueanexo_asociado_recibido,
                    )
                except (OperationalError, ProgrammingError):
                    ok, message = False, (
                        "No se pudo consultar el padrón o la base de datos. "
                        "Intentá nuevamente."
                    )
                    logger.exception(
                        "Inscripción Especial desde gestión con error de base: "
                        "seccion_id=%s cuil=%s cue_asociado=%s",
                        seccion.pk,
                        cuil,
                        normalizar_cueanexo(cueanexo_asociado_recibido)
                        or cueanexo_asociado_recibido,
                    )
                except DatabaseError:
                    ok, message = False, "No se pudo completar la inscripción por un error de base de datos."
                    logger.exception(
                        "Inscripción Especial desde gestión con error de base no clasificado: "
                        "seccion_id=%s cuil=%s cue_asociado=%s",
                        seccion.pk,
                        cuil,
                        normalizar_cueanexo(cueanexo_asociado_recibido)
                        or cueanexo_asociado_recibido,
                    )
                except Exception:
                    ok, message = False, "No se pudo completar la inscripción. Revisá los datos e intentá nuevamente."
                    logger.exception(
                        "Inscripción Especial desde gestión con error no controlado: "
                        "seccion_id=%s cuil=%s cue_asociado=%s",
                        seccion.pk,
                        cuil,
                        normalizar_cueanexo(cueanexo_asociado_recibido)
                        or cueanexo_asociado_recibido,
                    )
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
