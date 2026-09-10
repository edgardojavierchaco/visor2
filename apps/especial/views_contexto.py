# apps/especial/views_contexto.py
# -*- coding: utf-8 -*-

import json
from hashlib import sha256
from types import SimpleNamespace
from urllib.parse import urlencode

from django.core.exceptions import PermissionDenied
from django.core.cache import cache
from django.db.models import Q
from django.shortcuts import redirect, render
from django.urls import NoReverseMatch, reverse

from .models import (
    EspecialCiclo,
    normalizar_cueanexo,
)
from .permisos import (
    cueanexo_autorizado_especial,
    especial_required,
    get_permisos_especial_request,
)
from .performance import perf_phase


CACHE_TTL_CONTEXTO_ESPECIAL = 60 * 5
CACHE_VERSION_CONTEXTO_ESPECIAL = "v2_contexto_admin_all_20260810"
_CACHE_MISS_CONTEXTO = object()

ESTABLECIMIENTO_CACHE_FIELDS = (
    "cueanexo",
    "nom_est",
    "oferta",
    "region_loc",
    "localidad",
    "departamento",
    "apellido_resp",
    "nombre_resp",
    "sup_tecnico",
    "resploc_telefono",
    "resploc_email",
    "tel_suptecnico",
    "email_suptecnico",
)


ESPECIAL_MENU_METADATA = {
    "inicio": {
        "title": "Educación Especial",
        "subtitle": "Gestión institucional, alumnos, docentes, datos CUE-Anexo y secciones.",
    },
    "localizaciones": {
        "title": "Localizaciones",
        "subtitle": "Consulta institucional desde Padrón, con filtros, columnas y exportación Excel.",
    },
    "alumnos": {
        "title": "Alumnos",
        "subtitle": "Buscar, consultar y vincular alumnos al módulo Especial.",
    },
    "docentes": {
        "title": "Docentes",
        "subtitle": "Gestión de Docentes de Educación Especial.",
    },
    "cueanexo": {
        "title": "Datos CUE-Anexo",
        "subtitle": "Consultar los datos institucionales del establecimiento seleccionado.",
    },
    "secciones": {
        "title": "Secciones",
        "subtitle": "Administrar secciones, modalidades, turnos, capacidades e inscripciones.",
    },
    "ciclos": {
        "title": "Ciclos",
        "subtitle": "Administrar ciclos lectivos del módulo Especial.",
    },
}

ESPECIAL_MENU_DEFAULT = "inicio"
ESPECIAL_PARTIAL_SECTIONS = frozenset({"alumnos", "docentes", "cueanexo", "secciones", "ciclos"})

ESPECIAL_ACCESOS_RAPIDOS = (
    {
        "menu": "localizaciones",
        "url_name": "especial:visualizacion_localizaciones",
        "icon": "fa-location-dot",
        "append_querystring": False,
        "requires_admin": False,
    },
    {
        "menu": "alumnos",
        "url_name": "especial:alumnos",
        "icon": "fa-user-graduate",
        "append_querystring": True,
        "requires_admin": False,
    },
    {
        "menu": "docentes",
        "url_name": "especial:docentes",
        "icon": "fa-chalkboard-user",
        "append_querystring": True,
        "requires_admin": False,
    },
    {
        "menu": "cueanexo",
        "url_name": "especial:carga_cueanexo",
        "icon": "fa-school",
        "append_querystring": True,
        "requires_admin": False,
    },
    {
        "menu": "secciones",
        "url_name": "especial:carga_seccion",
        "icon": "fa-people-group",
        "append_querystring": True,
        "requires_admin": False,
    },
    {
        "menu": "ciclos",
        "url_name": "especial:administrar_ciclos",
        "icon": "fa-calendar-days",
        "append_querystring": True,
        "requires_admin": True,
    },
)


def _clean(valor):
    return str(valor or "").strip()


def _especial_options_usuario(permisos, scope="cargables"):
    """Devuelve las escuelas especiales que el usuario puede gestionar."""
    options = []
    vistos = set()
    queryset = permisos[f"escuelas_{scope}"]

    for cueanexo, nombre in (
        queryset
        .order_by("cueanexo", "nom_est")
        .values_list("cueanexo", "nom_est")
        .distinct()
    ):
        cueanexo_normalizado = normalizar_cueanexo(cueanexo)
        if not cueanexo_normalizado or cueanexo_normalizado in vistos:
            continue
        vistos.add(cueanexo_normalizado)
        options.append(
            {
                "cueanexo": cueanexo_normalizado,
                "nombre": _clean(nombre) or "Escuela Especial sin nombre",
            }
        )

    return options


def _cache_scope_fingerprint(permisos, scope):
    if scope not in {"visualizacion", "cargables"}:
        raise ValueError(f"Scope de CUE-Anexo no soportado: {scope!r}")
    if permisos.get("es_admin"):
        return "ALL"
    return sorted(
        {
            cueanexo
            for cueanexo in (
                normalizar_cueanexo(value)
                for value in permisos[f"cueanexos_{scope}"]
            )
            if cueanexo
        }
    )


def _cache_key_especial_options(request, permisos, scope):
    user_id = getattr(getattr(request, "user", None), "pk", None)
    if user_id is None or not str(user_id).strip():
        return None

    payload = json.dumps(
        {
            "user_id": str(user_id),
            "rol": str(permisos.get("rol") or ""),
            "scope": scope,
            "authorized_scope": _cache_scope_fingerprint(permisos, scope),
            "version": CACHE_VERSION_CONTEXTO_ESPECIAL,
        },
        ensure_ascii=True,
        separators=(",", ":"),
    )
    fingerprint = sha256(payload.encode("utf-8")).hexdigest()
    return f"especial:contexto:options:{CACHE_VERSION_CONTEXTO_ESPECIAL}:{fingerprint}"


def _validar_options_cache(value):
    if not isinstance(value, list):
        return _CACHE_MISS_CONTEXTO

    options = []
    for item in value:
        if not isinstance(item, dict) or set(item) != {"cueanexo", "nombre"}:
            return _CACHE_MISS_CONTEXTO
        cueanexo = item["cueanexo"]
        nombre = item["nombre"]
        cueanexo_normalizado = normalizar_cueanexo(cueanexo)
        if not isinstance(cueanexo, str) or not cueanexo_normalizado:
            return _CACHE_MISS_CONTEXTO
        if not isinstance(nombre, str):
            return _CACHE_MISS_CONTEXTO
        options.append(
            {
                "cueanexo": cueanexo_normalizado,
                "nombre": nombre,
            }
        )
    return options


def _get_especial_options_cached(request, permisos, scope):
    key = _cache_key_especial_options(request, permisos, scope)
    if key is None:
        return _especial_options_usuario(permisos, scope=scope)

    cached = cache.get(key, _CACHE_MISS_CONTEXTO)
    options = _validar_options_cache(cached)
    if options is not _CACHE_MISS_CONTEXTO:
        return options

    options = _especial_options_usuario(permisos, scope=scope)
    cache.set(key, options, CACHE_TTL_CONTEXTO_ESPECIAL)
    return options


def _establecimiento_cache_payload(establecimiento):
    if establecimiento is None:
        return None
    payload = {}
    for field in ESTABLECIMIENTO_CACHE_FIELDS:
        value = getattr(establecimiento, field, None)
        payload[field] = None if value is None else str(value)
    return payload


def _establecimiento_desde_cache(value, cueanexo):
    if value is None:
        return None
    if not isinstance(value, dict) or set(value) != set(ESTABLECIMIENTO_CACHE_FIELDS):
        return _CACHE_MISS_CONTEXTO
    if any(
        value[field] is not None and not isinstance(value[field], str)
        for field in ESTABLECIMIENTO_CACHE_FIELDS
    ):
        return _CACHE_MISS_CONTEXTO
    if normalizar_cueanexo(value["cueanexo"]) != cueanexo:
        return _CACHE_MISS_CONTEXTO

    payload = dict(value)
    payload["cueanexo"] = cueanexo
    return SimpleNamespace(**payload)


def _get_establecimiento_cached(permisos, cueanexo, scope):
    cueanexo_original = cueanexo
    cueanexo = normalizar_cueanexo(cueanexo)
    if not cueanexo:
        if cueanexo_original is None or cueanexo_original == "":
            return None
        raise PermissionDenied("No podés operar sobre el CUE-Anexo solicitado.")

    if not cueanexo_autorizado_especial(permisos, cueanexo, scope):
        raise PermissionDenied("No podés operar sobre el CUE-Anexo solicitado.")

    key = f"especial:contexto:establishment:{CACHE_VERSION_CONTEXTO_ESPECIAL}:{cueanexo}"
    cached = cache.get(key, _CACHE_MISS_CONTEXTO)
    establecimiento = _establecimiento_desde_cache(cached, cueanexo)
    if establecimiento is not _CACHE_MISS_CONTEXTO:
        return establecimiento

    establecimiento = (
        permisos["escuelas_visualizacion"]
        .filter(cueanexo=cueanexo)
        .order_by("cueanexo", "nom_est")
        .first()
    )
    payload = _establecimiento_cache_payload(establecimiento)
    cache.set(key, payload, CACHE_TTL_CONTEXTO_ESPECIAL)
    return _establecimiento_desde_cache(payload, cueanexo)


def _resolver_cueanexo(request, options):
    """Resuelve el CUE-Anexo desde GET/POST y valida permisos."""
    if "cueanexo" in request.GET:
        raw = request.GET.get("cueanexo")
    elif "cueanexo_contexto" in request.POST:
        raw = request.POST.get("cueanexo_contexto")
    else:
        raw = ""

    if raw is not None and raw != "":
        cueanexo = normalizar_cueanexo(raw)
        cueanexos_permitidos = {option["cueanexo"] for option in options}
        if not cueanexo or cueanexo not in cueanexos_permitidos:
            raise PermissionDenied("No podés operar sobre el CUE-Anexo solicitado.")
        return cueanexo

    return options[0]["cueanexo"] if options else ""


def _resolver_ciclo(request):
    """Resuelve el ciclo lectivo desde GET/POST."""
    ciclos = list(
        EspecialCiclo.objects.filter(Q(activo=True) | Q(cerrado=True)).order_by("-anio")
    )
    if "ciclo" in request.GET:
        raw = request.GET.get("ciclo")
    elif "ciclo_contexto" in request.POST:
        raw = request.POST.get("ciclo_contexto")
    else:
        raw = None

    if raw is not None:
        try:
            ciclo_id = int(raw)
        except (TypeError, ValueError):
            raise PermissionDenied("El ciclo solicitado no es válido.")
        else:
            for ciclo in ciclos:
                if ciclo.pk == ciclo_id:
                    return ciclo, ciclos
            raise PermissionDenied("El ciclo solicitado no está disponible.")

    ciclo_actual = next((ciclo for ciclo in ciclos if ciclo.actual), None)
    ciclo_operativo = ciclo_actual or (ciclos[0] if ciclos else None)
    return ciclo_operativo, ciclos


def _context_querystring(cueanexo, ciclo):
    """Construye el querystring con CUE-Anexo y ciclo."""
    params = {}
    if cueanexo:
        params["cueanexo"] = cueanexo
    if ciclo:
        params["ciclo"] = ciclo.pk
    return urlencode(params)


def _alumnos_url():
    """URL para la vista de alumnos."""
    try:
        return reverse("especial:alumnos")
    except NoReverseMatch:
        return ""


def metadata_menu_especial(active_menu):
    """Devuelve la metadata visual de la sección activa, con fallback a Inicio."""
    return ESPECIAL_MENU_METADATA.get(active_menu or "", ESPECIAL_MENU_METADATA[ESPECIAL_MENU_DEFAULT]).copy()


def es_navegacion_parcial(request, active_menu):
    """Indica si la vista soporta la representacion parcial solicitada."""
    return (
        request.method == "GET"
        and active_menu in ESPECIAL_PARTIAL_SECTIONS
        and request.headers.get("X-Especial-Partial") == "1"
    )


def render_especial(request, full_template, context, partial_template):
    """Renderiza la pagina completa o solo la region parcial autorizada."""
    template_name = partial_template if context.get("especial_partial") else full_template
    with perf_phase(request, "template"):
        return render(request, template_name, context)


def construir_accesos_rapidos_especial(especial_context):
    """Arma los accesos rápidos de Inicio reutilizando la metadata centralizada."""
    querystring = especial_context.get("querystring", "")
    es_admin = bool(especial_context.get("es_admin_especial"))
    accesos = []

    for acceso in ESPECIAL_ACCESOS_RAPIDOS:
        if acceso["requires_admin"] and not es_admin:
            continue

        metadata = metadata_menu_especial(acceso["menu"])
        url = reverse(acceso["url_name"])
        if acceso["append_querystring"] and querystring:
            url = f"{url}?{querystring}"

        accesos.append(
            {
                "menu": acceso["menu"],
                "url": url,
                "icon": acceso["icon"],
                "title": metadata["title"],
                "subtitle": metadata["subtitle"],
            }
        )

    return accesos


def resolver_contexto_operativo(request, scope="cargables"):
    """Resuelve el contexto operativo completo para Especial."""
    contexto_cacheado = getattr(request, "_especial_contexto_operativo", None)
    if contexto_cacheado is not None and getattr(request, "_especial_contexto_scope", None) == scope:
        return contexto_cacheado

    permisos = get_permisos_especial_request(request)
    with perf_phase(request, "context.options"):
        cueanexo_options = _get_especial_options_cached(
            request,
            permisos,
            scope=scope,
        )
    cueanexo = _resolver_cueanexo(request, cueanexo_options)
    with perf_phase(request, "context.cycle"):
        ciclo, ciclos = _resolver_ciclo(request)
    with perf_phase(request, "context.establishment"):
        establecimiento = _get_establecimiento_cached(
            permisos,
            cueanexo,
            scope=scope,
        )

    contexto = {
        "cueanexo": cueanexo,
        "cueanexo_options": cueanexo_options,
        "ciclo": ciclo,
        "ciclos": ciclos,
        "establecimiento": establecimiento,
        "querystring": _context_querystring(cueanexo, ciclo),
        "alumnos_url": _alumnos_url(),
        "es_admin_especial": permisos["es_admin"],
        "ciclo_cerrado": bool(ciclo and ciclo.cerrado),
        "puede_consultar": bool(cueanexo and ciclo),
        "puede_operar": bool(cueanexo and ciclo and not ciclo.cerrado),
        "sin_cueanexo": not bool(cueanexo),
        "sin_ciclo": not bool(ciclo),
    }
    request._especial_contexto_operativo = contexto
    request._especial_contexto_scope = scope
    return contexto


def contexto_base(request, active_menu, title=None, subtitle=None):
    """Contexto base para todas las vistas de Especial."""
    with perf_phase(request, "context"):
        scope = "visualizacion" if active_menu in {"localizaciones", "cueanexo"} else "cargables"
        especial_context = resolver_contexto_operativo(request, scope=scope)
        metadata = metadata_menu_especial(active_menu)
        if title is not None:
            metadata["title"] = title
        if subtitle is not None:
            metadata["subtitle"] = subtitle
        return {
            "title": metadata["title"],
            "subtitle": metadata["subtitle"],
            "especial_header": metadata,
            "active_menu": active_menu or ESPECIAL_MENU_DEFAULT,
            "especial_context": especial_context,
            "especial_partial": es_navegacion_parcial(request, active_menu),
            "request": request,
        }


@especial_required
def inicio(request):
    """Pantalla de acceso rápido del módulo Especial."""
    context = contexto_base(request, "inicio")
    context["especial_accesos_rapidos"] = construir_accesos_rapidos_especial(
        context["especial_context"]
    )
    return render(request, "especial/inicio_especial.html", context)


@especial_required
def visualizacion_inicio(request):
    """Redirige la entrada histórica hacia Localizaciones protegidas."""
    return redirect("especial:visualizacion_localizaciones")


def datos_establecimiento_items(establecimiento):
    """Convierte los datos del establecimiento en una lista de tuplas para el template."""
    if not establecimiento:
        return []

    responsable = " ".join(
        item
        for item in [
            _clean(getattr(establecimiento, "apellido_resp", "")),
            _clean(getattr(establecimiento, "nombre_resp", "")),
        ]
        if item
    )

    return [
        ("CUE-Anexo", _clean(getattr(establecimiento, "cueanexo", ""))),
        ("Establecimiento", _clean(getattr(establecimiento, "nom_est", ""))),
        ("Oferta", _clean(getattr(establecimiento, "oferta", ""))),
        ("Región", _clean(getattr(establecimiento, "region_loc", ""))),
        ("Localidad", _clean(getattr(establecimiento, "localidad", ""))),
        ("Departamento", _clean(getattr(establecimiento, "departamento", ""))),
        ("Responsable", responsable),
        ("Supervisor técnico", _clean(getattr(establecimiento, "sup_tecnico", ""))),
        ("Teléfono responsable", _clean(getattr(establecimiento, "resploc_telefono", ""))),
        ("Email responsable", _clean(getattr(establecimiento, "resploc_email", ""))),
        ("Teléfono supervisor", _clean(getattr(establecimiento, "tel_suptecnico", ""))),
        ("Email supervisor", _clean(getattr(establecimiento, "email_suptecnico", ""))),
    ]


def redirect_con_contexto(viewname, especial_context, *args, **kwargs):
    """Redirige manteniendo el contexto de CUE-Anexo y ciclo."""
    url = reverse(viewname, args=args, kwargs=kwargs)
    querystring = especial_context.get("querystring")
    return f"{url}?{querystring}" if querystring else url
