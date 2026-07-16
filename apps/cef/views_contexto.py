# -*- coding: utf-8 -*-

from urllib.parse import urlencode

from django.core.exceptions import PermissionDenied
from django.urls import NoReverseMatch, reverse

from .models import (
    CefCiclo,
    get_cefs_cargables_usuario,
    get_datos_establecimiento_cef,
    normalizar_cueanexo,
    usuario_es_admin_cef,
)


def _clean(valor):
    return str(valor or "").strip()


def _cef_options_usuario(user):
    options = []
    vistos = set()

    for cueanexo, nombre in (
        get_cefs_cargables_usuario(user)
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
                "nombre": _clean(nombre) or "CEF sin nombre",
            }
        )

    return options


def _resolver_cueanexo(request, options):
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
    ciclos = list(CefCiclo.objects.filter(activo=True).order_by("-anio"))
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
    cueanexo_options = _cef_options_usuario(request.user)
    cueanexo = _resolver_cueanexo(request, cueanexo_options)
    ciclo, ciclos = _resolver_ciclo(request)
    establecimiento = get_datos_establecimiento_cef(cueanexo) if cueanexo else None

    return {
        "cueanexo": cueanexo,
        "cueanexo_options": cueanexo_options,
        "ciclo": ciclo,
        "ciclos": ciclos,
        "establecimiento": establecimiento,
        "querystring": _context_querystring(cueanexo, ciclo),
        "alumnos_url": _alumnos_url(),
        "profesores_url": _profesores_url(),
        "es_admin_cef": usuario_es_admin_cef(request.user),
        "puede_operar": bool(cueanexo and ciclo),
        "sin_cueanexo": not bool(cueanexo),
        "sin_ciclo": not bool(ciclo),
    }


def contexto_base(request, active_menu, titulo):
    cef_context = resolver_contexto_operativo(request)
    return {
        "title": titulo,
        "active_menu": active_menu,
        "cef_context": cef_context,
        "request": request,
    }


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
