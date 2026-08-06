# apps/especial/views_contexto.py
# -*- coding: utf-8 -*-

from urllib.parse import urlencode

from django.core.exceptions import PermissionDenied
from django.shortcuts import render
from django.urls import NoReverseMatch, reverse

from .models import (
    EspecialCiclo,
    get_escuelas_especiales_cargables_usuario,
    get_datos_establecimiento_especial,
    normalizar_cueanexo,
    usuario_es_admin_especial,
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
        "subtitle": "Buscar, consultar y vincular docentes al módulo Especial.",
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


def _especial_options_usuario(user):
    """Devuelve las escuelas especiales que el usuario puede gestionar."""
    options = []
    vistos = set()

    for cueanexo, nombre in (
        get_escuelas_especiales_cargables_usuario(user)
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


def _resolver_cueanexo(request, options):
    """Resuelve el CUE-Anexo desde GET/POST y valida permisos."""
    raw = (
        request.GET.get("cueanexo")
        or request.POST.get("cueanexo_contexto")
        or ""
    )

    if raw:
        cueanexo = normalizar_cueanexo(raw)
        cueanexos_permitidos = {option["cueanexo"] for option in options}
        if not cueanexo or cueanexo not in cueanexos_permitidos:
            raise PermissionDenied("No podés operar sobre el CUE-Anexo solicitado.")
        return cueanexo

    return options[0]["cueanexo"] if options else ""


def _resolver_ciclo(request):
    """Resuelve el ciclo lectivo desde GET/POST."""
    ciclos = list(EspecialCiclo.objects.filter(activo=True).order_by("-anio"))
    raw = request.GET.get("ciclo") or request.POST.get("ciclo_contexto") or ""

    if raw:
        try:
            ciclo_id = int(raw)
        except (TypeError, ValueError):
            # If invalid, fallback gracefully instead of crashing
            pass
        else:
            for ciclo in ciclos:
                if ciclo.pk == ciclo_id:
                    return ciclo, ciclos

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


def resolver_contexto_operativo(request):
    """Resuelve el contexto operativo completo para Especial."""
    cueanexo_options = _especial_options_usuario(request.user)
    cueanexo = _resolver_cueanexo(request, cueanexo_options)
    ciclo, ciclos = _resolver_ciclo(request)
    establecimiento = get_datos_establecimiento_especial(cueanexo) if cueanexo else None

    return {
        "cueanexo": cueanexo,
        "cueanexo_options": cueanexo_options,
        "ciclo": ciclo,
        "ciclos": ciclos,
        "establecimiento": establecimiento,
        "querystring": _context_querystring(cueanexo, ciclo),
        "alumnos_url": _alumnos_url(),
        "es_admin_especial": usuario_es_admin_especial(request.user),
        "puede_operar": bool(cueanexo and ciclo),
        "sin_cueanexo": not bool(cueanexo),
        "sin_ciclo": not bool(ciclo),
    }


def contexto_base(request, active_menu, title=None, subtitle=None):
    """Contexto base para todas las vistas de Especial."""
    especial_context = resolver_contexto_operativo(request)
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
        "request": request,
    }


def inicio(request):
    """Pantalla de acceso rápido del módulo Especial."""
    context = contexto_base(request, "inicio")
    context["especial_accesos_rapidos"] = construir_accesos_rapidos_especial(
        context["especial_context"]
    )
    return render(request, "especial/inicio_especial.html", context)


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
