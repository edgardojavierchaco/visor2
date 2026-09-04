# apps/especial/views_docentes.py
# -*- coding: utf-8 -*-
from collections import defaultdict
import logging
import re
import unicodedata
from types import SimpleNamespace
from urllib.parse import urlencode

from django.contrib import messages
from django.core.paginator import Paginator
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.utils import OperationalError, ProgrammingError
from django.db.models import Min, OuterRef, Q, Subquery
from django.db.models.functions import Lower
from django.http import Http404, JsonResponse
from django.shortcuts import redirect, render
from django.template.loader import render_to_string
from django.urls import reverse
from django.shortcuts import get_object_or_404 # Asegúrate de tener este import
from apps.bnhpersonas.models import Personas
from .forms import EspecialBajaDocenteForm, EspecialDocenteSeccionForm

from .forms import EspecialBusquedaDocenteForm
from .models import (
    EspecialDocenteBnh,
    EspecialDocenteBanco,
    DocenteSeccion,
    SeccionEspecial,
    EspecialTrasladoDocente,
    PADRON_DB_ALIAS,
)
from .permisos import especial_required
from .services.docentes_seccion import dar_alta_docente_seccion, dar_baja_docente_seccion
from .services.baja_docentes import (
    dar_alta_docente_banco,
    dar_baja_docente_banco,
    preparar_baja_docente,
)
from .views_contexto import contexto_base, redirect_con_contexto, render_especial

URL_CARGA_DOCENTE = "/bnh/carga-personal/"
MSG_BANCO_DOCENTES_PENDIENTE = (
    "El banco de docentes de Educación Especial está pendiente de creación en base de datos."
)
logger = logging.getLogger(__name__)

DOCENTES_VISTA_DEFAULT = "actuales"
DOCENTES_VISTAS = {"actuales", "historial"}
DOCENTES_ESTADO_DEFAULT = "todos"
DOCENTES_ESTADOS = {"todos", "activo", "baja"}
DOCENTES_POR_PAGINA = 10
DOCENTES_BUSQUEDA_MAX_LENGTH = 100
DOCENTES_BUSQUEDA_EQUIVALENCIAS = {
    "a": "aáàäâãå",
    "e": "eéèëê",
    "i": "iíìïî",
    "n": "nñ",
    "o": "oóòöôõ",
    "u": "uúùüû",
}


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


def _docentes_vista_param(request):
    vista = (request.GET.get("vista") or DOCENTES_VISTA_DEFAULT).strip().lower()
    return vista if vista in DOCENTES_VISTAS else DOCENTES_VISTA_DEFAULT


def _docentes_busqueda_param(request):
    bruto = " ".join(str(request.GET.get("q") or "").split())
    if not bruto:
        return "", ""
    if len(bruto) > DOCENTES_BUSQUEDA_MAX_LENGTH:
        return (
            "",
            f"El término de búsqueda no puede superar los {DOCENTES_BUSQUEDA_MAX_LENGTH} caracteres.",
        )
    return bruto, ""


def _pagina_docentes_param(request):
    try:
        pagina = int(request.GET.get("page") or 1)
    except (TypeError, ValueError):
        pagina = 1
    return max(pagina, 1)


def _docentes_estado_param(request):
    estado = (request.GET.get("estado") or DOCENTES_ESTADO_DEFAULT).strip().lower()
    return estado if estado in DOCENTES_ESTADOS else DOCENTES_ESTADO_DEFAULT


def _docentes_state_params(
    especial_context,
    *,
    vista=DOCENTES_VISTA_DEFAULT,
    termino="",
    pagina=None,
    estado=DOCENTES_ESTADO_DEFAULT,
):
    params = {}
    if especial_context.get("cueanexo"):
        params["cueanexo"] = especial_context["cueanexo"]
    if especial_context.get("ciclo"):
        params["ciclo"] = especial_context["ciclo"].pk
    if vista in DOCENTES_VISTAS:
        params["vista"] = vista
    if termino:
        params["q"] = termino
    if vista == DOCENTES_VISTA_DEFAULT and estado in {"activo", "baja"}:
        params["estado"] = estado
    if pagina and pagina > 1:
        params["page"] = pagina
    return params


def _docentes_busqueda_tokens(valor):
    texto = unicodedata.normalize("NFD", str(valor or "")).casefold()
    texto = "".join(
        caracter
        for caracter in texto
        if unicodedata.category(caracter) != "Mn"
    )
    texto = re.sub(r"(\d)[,./-](?=\d)", r"\1", texto)
    return [token for token in re.split(r"[\s,./-]+", texto) if token]


def _docentes_busqueda_patron(token):
    caracteres = []
    for caracter in token:
        equivalencias = DOCENTES_BUSQUEDA_EQUIVALENCIAS.get(caracter)
        caracteres.append(
            f"[{equivalencias}]" if equivalencias else re.escape(caracter)
        )
    return "".join(caracteres)


def _aplicar_busqueda_docentes_historial(queryset, especial_context, termino):
    tokens = _docentes_busqueda_tokens(termino)
    if not tokens:
        return queryset.none() if termino else queryset

    filtros_globales = Q()
    for token in tokens:
        if token.isdigit():
            patron = r"\D*".join(re.escape(digito) for digito in token)
        else:
            patron = _docentes_busqueda_patron(token)
        filtros_token = (
            Q(docente_cuil__iregex=patron)
            | Q(docente_nombre_snapshot__iregex=patron)
            | Q(docente_dni_snapshot__iregex=patron)
        )
        filtros_token |= Q(
            docente_cuil__in=DocenteSeccion.objects.filter(
                seccion__cueanexo=especial_context["cueanexo"],
                seccion__nombre_seccion__iregex=patron,
            ).values("docente_cuil")
        )
        filtros_globales &= filtros_token
    return queryset.filter(filtros_globales)


def _docentes_historial_queryset(especial_context, termino=""):
    """Obtiene todos los registros del docente para el CUE seleccionado."""
    if not especial_context["puede_consultar"]:
        return EspecialDocenteBanco.objects.none()
    queryset = EspecialDocenteBanco.objects.filter(
        cueanexo=especial_context["cueanexo"],
    )
    return _aplicar_busqueda_docentes_historial(
        queryset,
        especial_context,
        termino,
    )


def _asignaciones_para_periodo_docente(banco, asignaciones):
    """Devuelve las asignaciones del ciclo sin repetir secciones."""
    asignaciones_periodo = []
    secciones_vistas = set()
    for asignacion in asignaciones:
        if asignacion.seccion.ciclo_id != banco.ciclo_id:
            continue
        # Al reactivar una asignación se reutiliza el mismo registro y se
        # limpia fecha_hasta; no debe reaparecer como activa en un banco que
        # ya quedó de baja.
        if (
            banco.estado == EspecialDocenteBanco.Estado.BAJA
            and asignacion.estado == DocenteSeccion.Estado.ACTIVO
        ):
            continue
        if banco.fecha_baja and asignacion.fecha_desde and asignacion.fecha_desde > banco.fecha_baja:
            continue
        if asignacion.fecha_hasta and asignacion.fecha_hasta < banco.fecha_alta:
            continue
        if asignacion.seccion_id in secciones_vistas:
            continue
        secciones_vistas.add(asignacion.seccion_id)
        asignaciones_periodo.append(asignacion)
    return asignaciones_periodo


def _historial_docentes_paginado(especial_context, queryset, pagina):
    """Agrupa el historial por docente y conserva todas sus asignaciones."""
    docentes_ids = (
        queryset.order_by()
        .values("docente_cuil")
        .annotate(nombre=Min("docente_nombre_snapshot"))
        .order_by(
            Lower("nombre"),
            "nombre",
            "docente_cuil",
        )
        .values_list("docente_cuil", flat=True)
    )
    page_obj = Paginator(docentes_ids, DOCENTES_POR_PAGINA).get_page(pagina)
    page_cuiles = list(page_obj.object_list)
    if not page_cuiles:
        return [], page_obj

    bancos = list(
        EspecialDocenteBanco.objects.filter(
            cueanexo=especial_context["cueanexo"],
            docente_cuil__in=page_cuiles,
        )
        .select_related("ciclo")
        .order_by("docente_cuil", "-ciclo__anio", "-fecha_alta", "-pk")
    )
    asignaciones = list(
        DocenteSeccion.objects.filter(
            seccion__cueanexo=especial_context["cueanexo"],
            docente_cuil__in=page_cuiles,
        )
        .select_related(
            "seccion",
            "seccion__ciclo",
            "seccion__cd_tipo_seccion",
        )
        .order_by(
            "docente_cuil",
            "-seccion__ciclo__anio",
            Lower("seccion__nombre_seccion"),
            "seccion__nombre_seccion",
            "rol",
            "pk",
        )
    )
    traslados = list(
        EspecialTrasladoDocente.objects.filter(
            cueanexo_origen=especial_context["cueanexo"],
            docente_cuil__in=page_cuiles,
            estado__in=[
                EspecialTrasladoDocente.Estado.EN_TRANSITO,
                EspecialTrasladoDocente.Estado.APLICADO,
            ],
        )
        .select_related("ciclo_origen", "ciclo_destino")
        .order_by("docente_cuil", "ciclo_origen__anio", "cueanexo_destino")
    )
    bancos_por_cuil = defaultdict(list)
    for banco in bancos:
        bancos_por_cuil[banco.docente_cuil].append(banco)
    asignaciones_por_cuil_ciclo = defaultdict(list)
    for asignacion in asignaciones:
        asignaciones_por_cuil_ciclo[
            (asignacion.docente_cuil, asignacion.seccion.ciclo_id)
        ].append(asignacion)
    destinos_por_cuil_ciclo = defaultdict(set)
    for traslado in traslados:
        destinos_por_cuil_ciclo[
            (traslado.docente_cuil, traslado.ciclo_origen_id)
        ].add(traslado.cueanexo_destino)

    items = []
    ciclo_seleccionado_id = getattr(especial_context.get("ciclo"), "pk", None)
    for docente_cuil in page_cuiles:
        bancos_docente = bancos_por_cuil.get(docente_cuil, [])
        if not bancos_docente:
            continue
        periodos = [
            SimpleNamespace(
                banco=banco,
                cueanexo_asociado=(
                    f"{banco.cueanexo} → "
                    f"{', '.join(sorted(destinos_por_cuil_ciclo[(docente_cuil, banco.ciclo_id)]))}"
                    if destinos_por_cuil_ciclo[(docente_cuil, banco.ciclo_id)]
                    else banco.cueanexo
                ),
                estado_label=banco.get_estado_display(),
                asignaciones=_asignaciones_para_periodo_docente(
                    banco,
                    asignaciones_por_cuil_ciclo[
                        (docente_cuil, banco.ciclo_id)
                    ],
                ),
            )
            for banco in bancos_docente
        ]
        bancos_ciclo_seleccionado = [
            banco for banco in bancos_docente
            if banco.ciclo_id == ciclo_seleccionado_id
        ]
        banco_actual = next(
            (
                banco for banco in bancos_ciclo_seleccionado
                if banco.estado == EspecialDocenteBanco.Estado.ACTIVO
            ),
            None,
        ) or (bancos_ciclo_seleccionado[0] if bancos_ciclo_seleccionado else bancos_docente[0])
        nombre_snapshot = next(
            (
                banco.docente_nombre_snapshot
                for banco in bancos_docente
                if banco.docente_nombre_snapshot
            ),
            "",
        )
        dni_snapshot = next(
            (
                banco.docente_dni_snapshot
                for banco in bancos_docente
                if banco.docente_dni_snapshot
            ),
            "",
        )
        tuvo_baja = any(
            banco.estado == EspecialDocenteBanco.Estado.BAJA
            for banco in bancos_docente
        )
        items.append(
            SimpleNamespace(
                docente_cuil=docente_cuil,
                docente_nombre_snapshot=nombre_snapshot,
                docente_dni_snapshot=dni_snapshot,
                ciclo=banco_actual.ciclo,
                estado=banco_actual.estado,
                estado_label=banco_actual.get_estado_display(),
                accion_actual="Alta" if banco_actual.estado == EspecialDocenteBanco.Estado.ACTIVO and tuvo_baja else "—",
                historial_periodos=periodos,
            )
        )
    return items, page_obj


def _docentes_especial(especial_context, estado=DOCENTES_ESTADO_DEFAULT):
    if not especial_context["puede_consultar"]:
        return EspecialDocenteBanco.objects.none()

    queryset = EspecialDocenteBanco.objects.filter(
        cueanexo=especial_context["cueanexo"],
        ciclo=especial_context["ciclo"],
    )
    ultimo_periodo = (
        EspecialDocenteBanco.objects.filter(
            cueanexo=especial_context["cueanexo"],
            ciclo=especial_context["ciclo"],
            docente_cuil=OuterRef("docente_cuil"),
        )
        .order_by("-fecha_alta", "-pk")
        .values("pk")[:1]
    )
    queryset = queryset.filter(pk=Subquery(ultimo_periodo))
    if estado in {"activo", "baja"}:
        queryset = queryset.filter(estado=estado)
    return queryset.order_by("docente_nombre_snapshot", "docente_cuil", "estado")


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


def _secciones_ocupadas_ids(especial_context, docente_cuil):
    """Devuelve secciones ya asignadas al docente en estados no asignables."""
    return set(
        DocenteSeccion.objects.filter(
            seccion__cueanexo=especial_context["cueanexo"],
            seccion__ciclo=especial_context["ciclo"],
            docente_cuil=_solo_digitos(docente_cuil),
            estado__in=[
                DocenteSeccion.Estado.ACTIVO,
                DocenteSeccion.Estado.INACTIVO,
            ],
        ).values_list("seccion_id", flat=True)
    )


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


def _url_carga_docente(
    cuil,
    next_url=None,
    return_label="Volver a Especial",
    *,
    alta_banco_especial=False,
    especial_context=None,
):
    params = {}
    if cuil:
        params["cuil"] = cuil
    if next_url:
        params["next"] = next_url
    if return_label:
        params["return_label"] = return_label
    if alta_banco_especial and especial_context:
        cueanexo = especial_context.get("cueanexo")
        ciclo = especial_context.get("ciclo")
        if cueanexo and ciclo:
            params["especial_alta"] = "1"
            params["especial_callback_url"] = (
                f"{reverse('especial:agregar_docente_banco_desde_bnh')}?"
                f"{urlencode({'cueanexo': cueanexo, 'ciclo': ciclo.pk})}"
            )
    return f"{URL_CARGA_DOCENTE}?{urlencode(params)}" if params else URL_CARGA_DOCENTE


def _url_edicion_docente(cuil, next_url=None, return_label="Volver a Especial"):
    """Devuelve la edición de BNH para una persona ya existente.

    Especial sólo persiste el CUIL del docente; BNH requiere el ID de su
    registro para cargar la instancia en el formulario. La consulta es de
    lectura y la vista de BNH vuelve a aplicar su propio alcance de permisos.
    """
    cuil_normalizado = _solo_digitos(cuil)
    persona_id = (
        Personas.objects
        .filter(cuil=cuil_normalizado, archivada=False)
        .values_list("pk", flat=True)
        .first()
    )
    if persona_id:
        params = {}
        if next_url:
            params["next"] = next_url
        if return_label:
            params["return_label"] = return_label
        url = reverse("bnhpersonas:carga_personal_edit", args=[persona_id])
        return f"{url}?{urlencode(params)}" if params else url

    return _url_carga_docente(cuil, next_url, return_label)


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


@especial_required
def agregar_docente_banco_desde_bnh(request):
    """Agrega al banco un docente recién creado en BNH."""
    if request.method != "POST":
        return JsonResponse({"ok": False, "error": "Método no permitido."}, status=405)

    context = contexto_base(request, "docentes")
    especial_context = context["especial_context"]
    if not especial_context.get("puede_operar") or especial_context.get("ciclo_cerrado"):
        return JsonResponse(
            {"ok": False, "error": "El contexto seleccionado no permite operar."},
            status=403,
        )

    cuil = _solo_digitos(request.POST.get("cuil"))
    if len(cuil) != 11:
        return JsonResponse({"ok": False, "error": "El CUIL no es válido."}, status=400)

    docente = _buscar_docente(cuil)
    if not docente:
        return JsonResponse(
            {"ok": False, "error": "El docente no existe todavía en BNH."},
            status=404,
        )

    try:
        banco, creado, tabla_pendiente = _asegurar_docente_banco(
            docente,
            especial_context,
            request.user,
        )
    except (IntegrityError, ValidationError):
        return JsonResponse(
            {"ok": False, "error": "No se pudo agregar el docente al banco."},
            status=409,
        )

    if tabla_pendiente:
        return JsonResponse({"ok": False, "error": MSG_BANCO_DOCENTES_PENDIENTE}, status=503)
    return JsonResponse({"ok": True, "created": creado, "banco_id": banco.pk if banco else None})


def _url_docentes(
    especial_context,
    *,
    vista=DOCENTES_VISTA_DEFAULT,
    termino="",
    pagina=None,
    estado=DOCENTES_ESTADO_DEFAULT,
):
    params = _docentes_state_params(
        especial_context,
        vista=vista,
        termino=termino,
        pagina=pagina,
        estado=estado,
    )
    querystring = urlencode(params)
    url = reverse("especial:docentes")
    return f"{url}?{querystring}" if querystring else url


def _errores_form(form):
    return " ".join(error for errors in form.errors.values() for error in errors)


def _docentes_fragment_context(especial_context, url_docentes, estado=DOCENTES_ESTADO_DEFAULT):
    """Arma el contexto mínimo para refrescar la tabla de Docentes."""
    docentes = list(_docentes_especial(especial_context, estado))
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
        secciones_ocupadas_ids = _secciones_ocupadas_ids(
            especial_context,
            item.docente_cuil,
        )
        item.secciones_asignables = [
            seccion
            for seccion in secciones_disponibles
            if seccion.pk not in secciones_ocupadas_ids
        ]
        item.secciones_bloqueadas = asignaciones_activas
        item.url_baja_docente = _url_baja_docente(especial_context, item.pk)
        item.url_editar_docente = _url_edicion_docente(
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


def _docentes_fragment_response(request, especial_context, url_docentes, estado=DOCENTES_ESTADO_DEFAULT):
    fragment_context = _docentes_fragment_context(especial_context, url_docentes, estado)
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
    vista = _docentes_vista_param(request)
    estado_docentes = _docentes_estado_param(request)
    termino_busqueda, busqueda_error = _docentes_busqueda_param(request)
    pagina_solicitada = _pagina_docentes_param(request)
    if request.method == "POST" and especial_context.get("ciclo_cerrado"):
        messages.error(
            request,
            "El ciclo seleccionado está cerrado y sólo puede consultarse.",
        )
        return redirect(request.get_full_path())

    if request.method == "POST" and vista != DOCENTES_VISTA_DEFAULT:
        messages.error(request, "El historial es consultivo y no admite operaciones.")
        return redirect(
            _url_docentes(
                especial_context,
                vista=vista,
                termino=termino_busqueda,
                pagina=pagina_solicitada,
            )
        )

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
    url_docentes = _url_docentes(
        especial_context,
        vista=vista,
        termino=termino_busqueda,
        pagina=pagina_solicitada if vista == "historial" else None,
        estado=estado_docentes,
    )

    if request.method == "POST":
        accion = request.POST.get("accion")

        if accion == "alta_docente_especial":
            if not especial_context["puede_operar"]:
                messages.warning(request, "Seleccioná un CUE-Anexo y un ciclo para operar.")
                return redirect(url_docentes)
            try:
                dar_alta_docente_banco(
                    banco_id=request.POST.get("docente_banco_id"),
                    cueanexo=especial_context["cueanexo"],
                    ciclo=especial_context["ciclo"],
                    user=request.user,
                )
            except (ValidationError, IntegrityError) as exc:
                messages.error(request, "; ".join(exc.messages) if isinstance(exc, ValidationError) else "El docente ya se encuentra activo en este establecimiento y ciclo.")
            else:
                messages.success(request, "Docente dado de alta en Educación Especial correctamente.")
                return redirect(
                    _url_docentes(
                        especial_context,
                        vista="historial",
                        termino=termino_busqueda,
                        pagina=1,
                    )
                )
            return redirect(url_docentes)

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
                    return _docentes_fragment_response(request, especial_context, url_docentes, estado_docentes)
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
            asignacion_inactiva = DocenteSeccion.objects.filter(
                seccion=seccion,
                docente_cuil=cuil,
                estado=DocenteSeccion.Estado.INACTIVO,
            ).exists()
            if asignacion_inactiva:
                message = "El docente ya está asignado a esta sección con estado Inactivo."
                if _is_ajax(request):
                    return JsonResponse({"error": message}, status=409)
                messages.error(request, message)
                return redirect(url_docentes)

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
                    docentes_actualizados = list(_docentes_especial(especial_context, estado_docentes))
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
                        ids_ocupadas = _secciones_ocupadas_ids(
                            especial_context,
                            item.docente_cuil,
                        )
                        item.secciones_asignables = [s for s in secciones_disp if s.pk not in ids_ocupadas]
                        item.secciones_bloqueadas = activas
                        item.url_baja_docente = _url_baja_docente(especial_context, item.pk)
                        item.url_editar_docente = _url_edicion_docente(item.docente_cuil, url_docentes, "Volver a Docentes Especial")

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
    url_carga_profesor = _url_carga_docente(
        cuil_buscado,
        next_url,
        "Volver a Docentes Especial",
        alta_banco_especial=True,
        especial_context=especial_context,
    )
    docentes_banco_tabla_pendiente = False
    page_obj = Paginator([], DOCENTES_POR_PAGINA).get_page(1)
    secciones_disponibles = []

    if vista == "historial":
        try:
            docentes, page_obj = _historial_docentes_paginado(
                especial_context,
                _docentes_historial_queryset(
                    especial_context,
                    termino_busqueda,
                ),
                pagina_solicitada,
            )
        except (OperationalError, ProgrammingError):
            docentes = []
            docentes_banco_tabla_pendiente = True
    else:
        try:
            docentes = list(_docentes_especial(especial_context, estado_docentes))
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
            secciones_ocupadas_ids = _secciones_ocupadas_ids(
                especial_context,
                item.docente_cuil,
            )
            item.secciones_asignables = [
                seccion for seccion in secciones_disponibles if seccion.pk not in secciones_ocupadas_ids
            ]
            item.secciones_bloqueadas = asignaciones_activas
            item.url_baja_docente = _url_baja_docente(especial_context, item.pk)
            item.url_editar_docente = _url_edicion_docente(
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
    docentes_actuales_url = _url_docentes(
        especial_context,
        vista=DOCENTES_VISTA_DEFAULT,
        termino=termino_busqueda,
        estado=estado_docentes,
    )
    docentes_todos_url = _url_docentes(
        especial_context,
        vista=DOCENTES_VISTA_DEFAULT,
        termino=termino_busqueda,
        estado="todos",
    )
    docentes_altas_url = _url_docentes(
        especial_context,
        vista=DOCENTES_VISTA_DEFAULT,
        termino=termino_busqueda,
        estado="activo",
    )
    docentes_bajas_url = _url_docentes(
        especial_context,
        vista=DOCENTES_VISTA_DEFAULT,
        termino=termino_busqueda,
        estado="baja",
    )
    docentes_historial_url = _url_docentes(
        especial_context,
        vista="historial",
        termino=termino_busqueda,
        pagina=1,
    )
    pagina_anterior_docentes_url = (
        _url_docentes(
            especial_context,
            vista="historial",
            termino=termino_busqueda,
            pagina=page_obj.previous_page_number(),
        )
        if vista == "historial" and page_obj.has_previous()
        else ""
    )
    pagina_siguiente_docentes_url = (
        _url_docentes(
            especial_context,
            vista="historial",
            termino=termino_busqueda,
            pagina=page_obj.next_page_number(),
        )
        if vista == "historial" and page_obj.has_next()
        else ""
    )
    
    context.update(
        {
            "busqueda_form": busqueda_form,
            "docente": docente,
            "docente_row": _docente_row(docente),
            "docentes": docentes,
            "docentes_actuales_url": docentes_actuales_url,
            "docentes_todos_url": docentes_todos_url,
            "docentes_altas_url": docentes_altas_url,
            "docentes_bajas_url": docentes_bajas_url,
            "docentes_historial_url": docentes_historial_url,
            "modo_historial_docentes": vista == "historial",
            "vista_docentes": vista,
            "estado_docentes": estado_docentes,
            "termino_busqueda_docentes": termino_busqueda,
            "busqueda_error_docentes": busqueda_error,
            "pagina_anterior_docentes_url": pagina_anterior_docentes_url,
            "pagina_siguiente_docentes_url": pagina_siguiente_docentes_url,
            "page_obj_docentes": page_obj,
            "secciones_disponibles": secciones_disponibles,
            "docentes_banco_tabla_pendiente": docentes_banco_tabla_pendiente,
            "docente_en_banco": docente_en_banco,
            "cuil_buscado": cuil_buscado,
            "cuil_error": cuil_error,
            "url_carga_docente": url_carga_docente,
            "url_carga_profesor": url_carga_profesor,
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
