# -*- coding: utf-8 -*-

from urllib.parse import urlencode
from types import SimpleNamespace

from django.core.cache import cache
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.middleware.csrf import get_token
from django.template.loader import get_template
from django.urls import NoReverseMatch, reverse

from .models import (
    CefCiclo,
    get_cefs_base_queryset,
    normalizar_cueanexo,
)
from .permisos import get_permisos_cef_request
from .performance import perf_phase


SELECTOR_CEF_CACHE_VERSION = "v2"
SELECTOR_CEF_CACHE_TTL = 300
ESTABLECIMIENTO_CEF_CACHE_VERSION = "v1"
ESTABLECIMIENTO_CEF_CACHE_TTL = 900
CICLOS_CEF_CACHE_KEY = "cef:ciclos:activos:v2"
CICLOS_CEF_CACHE_TTL = 3600
SESSION_CEF_CUEANEXO_KEY = "cef_cueanexo_actual"
ORIGENES_GESTION_GRUPO = {"grupos", "alumnos", "profesores"}
VISTAS_CEF = {"actuales", "historial"}

ESTABLECIMIENTO_CEF_FIELDS = (
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

CICLO_CEF_CACHE_FIELDS = (
    "id",
    "anio",
    "descripcion",
    "activo",
    "actual",
    "cerrado",
)


def _clean(valor):
    return str(valor or "").strip()


def resolver_origen_gestion_grupo(valor):
    return valor if valor in ORIGENES_GESTION_GRUPO else "grupos"


def normalizar_vista_cef(valor):
    return valor if valor in VISTAS_CEF else "actuales"


def _selector_cef_cache_key(user):
    user_id = getattr(user, "pk", None)
    if user_id is None:
        return ""

    return f"cef:selector:{SELECTOR_CEF_CACHE_VERSION}:user:{user_id}"


def _establecimiento_cef_cache_key(cueanexo):
    return (
        f"cef:establecimiento:{ESTABLECIMIENTO_CEF_CACHE_VERSION}:"
        f"cueanexo:{cueanexo}"
    )


def _establecimiento_desde_fila(fila):
    cueanexo = normalizar_cueanexo(fila.get("cueanexo"))
    if not cueanexo:
        return None

    establecimiento = {
        campo: fila.get(campo)
        for campo in ESTABLECIMIENTO_CEF_FIELDS
    }
    establecimiento["cueanexo"] = cueanexo
    return establecimiento


def _consultar_opciones_cef(permisos):
    if not permisos["puede_ver"]:
        return [], {}

    queryset = get_cefs_base_queryset()
    if not permisos["es_admin"]:
        cueanexos = permisos.get("cueanexos_cargables", [])
        if not cueanexos:
            return [], {}
        queryset = queryset.filter(cueanexo__in=cueanexos)

    options = []
    establecimientos = {}

    for fila in queryset.order_by("cueanexo", "nom_est").values(
        *ESTABLECIMIENTO_CEF_FIELDS
    ):
        establecimiento = _establecimiento_desde_fila(fila)
        if not establecimiento:
            continue

        cueanexo = establecimiento["cueanexo"]
        if cueanexo in establecimientos:
            continue

        establecimientos[cueanexo] = establecimiento
        options.append(
            {
                "cueanexo": cueanexo,
                "nombre": _clean(establecimiento["nom_est"]) or "CEF sin nombre",
            }
        )

    return options, establecimientos


def _filtrar_opciones_autorizadas(options, permisos):
    if not permisos["puede_ver"]:
        return []

    if permisos["es_admin"]:
        return options

    cueanexos_permitidos = set(permisos.get("cueanexos_cargables", []))
    return [
        option
        for option in options
        if option["cueanexo"] in cueanexos_permitidos
    ]


def _cef_options_usuario(request, permisos):
    options_cacheadas = getattr(request, "_cef_options_usuario", None)
    if options_cacheadas is not None:
        return options_cacheadas

    cache_key = _selector_cef_cache_key(request.user)
    sentinel = object()
    options = cache.get(cache_key, sentinel) if cache_key else sentinel
    establecimientos = {}

    if options is sentinel:
        options, establecimientos = _consultar_opciones_cef(permisos)
        if cache_key:
            cache.set(cache_key, options, SELECTOR_CEF_CACHE_TTL)

    options = _filtrar_opciones_autorizadas(options, permisos)

    if not permisos["es_admin"]:
        cueanexos_permitidos = set(permisos.get("cueanexos_cargables", []))
        cueanexos_disponibles = {option["cueanexo"] for option in options}
        if not cueanexos_permitidos.issubset(cueanexos_disponibles):
            options, establecimientos = _consultar_opciones_cef(permisos)
            if cache_key:
                cache.set(cache_key, options, SELECTOR_CEF_CACHE_TTL)

    request._cef_establecimientos_contexto = establecimientos

    request._cef_options_usuario = options
    return options


def _resolver_cueanexo(request, options):
    session = getattr(request, "session", None)
    raw = request.GET.get("cueanexo") or request.POST.get(
        "cueanexo_contexto"
    ) or ""

    if raw:
        cueanexo = normalizar_cueanexo(raw)
        cueanexos_permitidos = {option["cueanexo"] for option in options}
        if not cueanexo or cueanexo not in cueanexos_permitidos:
            raise PermissionDenied("No podés operar sobre el CUE-Anexo solicitado.")

        previous = session.get(SESSION_CEF_CUEANEXO_KEY, "") if session else ""
        session_write = session is not None and previous != cueanexo
        if session_write:
            session[SESSION_CEF_CUEANEXO_KEY] = cueanexo
        return cueanexo

    cueanexo_sesion = normalizar_cueanexo(
        session.get(SESSION_CEF_CUEANEXO_KEY, "") if session is not None else ""
    )
    cueanexos_permitidos = {option["cueanexo"] for option in options}
    if cueanexo_sesion in cueanexos_permitidos:
        return cueanexo_sesion

    if session is not None and cueanexo_sesion:
        session.pop(SESSION_CEF_CUEANEXO_KEY, None)

    cueanexo = options[0]["cueanexo"] if options else ""
    if cueanexo and session is not None:
        session[SESSION_CEF_CUEANEXO_KEY] = cueanexo
    return cueanexo


def _obtener_establecimiento_cef(request, cueanexo):
    if not cueanexo:
        return None

    establecimientos = getattr(request, "_cef_establecimientos_contexto", {})
    establecimiento = establecimientos.get(cueanexo)
    cache_key = _establecimiento_cef_cache_key(cueanexo)
    debe_cachear = establecimiento is not None

    if establecimiento is None:
        sentinel = object()
        establecimiento = cache.get(cache_key, sentinel)
        if establecimiento is sentinel:
            fila = (
                get_cefs_base_queryset()
                .filter(cueanexo=cueanexo)
                .order_by("cueanexo", "nom_est")
                .values(*ESTABLECIMIENTO_CEF_FIELDS)
                .first()
            )
            establecimiento = _establecimiento_desde_fila(fila) if fila else None
            debe_cachear = establecimiento is not None

    if establecimiento is not None:
        if debe_cachear:
            cache.set(cache_key, establecimiento, ESTABLECIMIENTO_CEF_CACHE_TTL)
        return SimpleNamespace(**establecimiento)

    return None


def invalidar_cache_ciclos_cef():
    cache.delete(CICLOS_CEF_CACHE_KEY)


def _ciclo_desde_cache(datos):
    ciclo = CefCiclo(**datos)
    ciclo._state.adding = False
    ciclo._state.db = CefCiclo.objects.db
    return ciclo


def _ciclos_activos_cacheados():
    sentinel = object()
    ciclos_serializados = cache.get(CICLOS_CEF_CACHE_KEY, sentinel)

    if ciclos_serializados is sentinel:
        ciclos_serializados = list(
            CefCiclo.objects.filter(activo=True)
            .order_by("-anio")
            .values(*CICLO_CEF_CACHE_FIELDS)
        )
        cache.set(
            CICLOS_CEF_CACHE_KEY,
            ciclos_serializados,
            CICLOS_CEF_CACHE_TTL,
        )

    return [_ciclo_desde_cache(datos) for datos in ciclos_serializados]


def _resolver_ciclo(request):
    ciclos = _ciclos_activos_cacheados()
    raw = request.GET.get("ciclo") or request.POST.get("ciclo_contexto") or ""

    if raw:
        try:
            ciclo_id = int(raw)
        except (TypeError, ValueError):
            raise PermissionDenied("El ciclo solicitado no es válido.")

        for ciclo in ciclos:
            if ciclo.pk == ciclo_id:
                return ciclo, ciclos

        raise PermissionDenied("El ciclo solicitado no está disponible.")

    ciclo_actual = next((ciclo for ciclo in ciclos if ciclo.actual), None)
    ciclo_operativo = ciclo_actual or (ciclos[0] if ciclos else None)
    return ciclo_operativo, ciclos


def _context_querystring(cueanexo, ciclo):
    params = {}
    if cueanexo:
        params["cueanexo"] = cueanexo
    if ciclo:
        params["ciclo"] = ciclo.pk
    return urlencode(params)


def _alumnos_url():
    try:
        return reverse("cef:alumnos")
    except NoReverseMatch:
        return ""


def _profesores_url():
    try:
        return reverse("cef:profesores")
    except NoReverseMatch:
        return ""


def resolver_contexto_operativo(request):
    contexto_cacheado = getattr(request, "_cef_contexto_operativo", None)
    if contexto_cacheado is not None:
        return contexto_cacheado

    permisos = get_permisos_cef_request(request)
    cueanexo_options = _cef_options_usuario(request, permisos)
    cueanexo = _resolver_cueanexo(request, cueanexo_options)
    ciclo, ciclos = _resolver_ciclo(request)
    establecimiento = _obtener_establecimiento_cef(request, cueanexo)
    vista = normalizar_vista_cef(
        request.GET.get("vista") or request.POST.get("vista")
    )
    puede_consultar = bool(cueanexo and ciclo)
    ciclo_cerrado = bool(ciclo and ciclo.cerrado)

    contexto = {
        "cueanexo": cueanexo,
        "cueanexo_options": cueanexo_options,
        "ciclo": ciclo,
        "ciclos": ciclos,
        "establecimiento": establecimiento,
        "querystring": _context_querystring(cueanexo, ciclo),
        "alumnos_url": _alumnos_url(),
        "profesores_url": _profesores_url(),
        "es_admin_cef": permisos["es_admin"],
        "es_profesor_cef": permisos.get("es_profesor_cef", False),
        "solo_asistencia": permisos.get("solo_asistencia", False),
        "puede_metricas": permisos.get("puede_metricas", False),
        "rol_usuario": permisos.get("rol"),
        "puede_consultar": puede_consultar,
        "ciclo_cerrado": ciclo_cerrado,
        "puede_operar": puede_consultar and not ciclo_cerrado,
        "vista": vista,
        "sin_cueanexo": not bool(cueanexo),
        "sin_ciclo": not bool(ciclo),
    }
    request._cef_contexto_operativo = contexto
    return contexto


def contexto_base(request, active_menu, titulo):
    with perf_phase(request, "context"):
        cef_context = resolver_contexto_operativo(request)
        return {
            "title": titulo,
            "active_menu": active_menu,
            "cef_context": cef_context,
            "puede_metricas": cef_context["puede_metricas"],
            "request": request,
        }


def render_fragmento_cef(request, template_name, context=None):
    """Renderiza HTML parcial sin construir un RequestContext global."""
    fragment_context = dict(context or {})
    fragment_context.update(
        {
            "request": request,
            "user": request.user,
            "csrf_token": get_token(request),
        }
    )
    html = get_template(template_name).render(fragment_context)
    return HttpResponse(html, content_type="text/html; charset=utf-8")


def datos_establecimiento_items(establecimiento):
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


def redirect_con_contexto(viewname, cef_context, *args, **kwargs):
    url = reverse(viewname, args=args, kwargs=kwargs)
    querystring = cef_context.get("querystring")
    return f"{url}?{querystring}" if querystring else url
