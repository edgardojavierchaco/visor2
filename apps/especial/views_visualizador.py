# -*- coding: utf-8 -*-
"""Visualizador global de personas y establecimientos para administradores."""

import re
from django.apps import apps
from django.core.exceptions import PermissionDenied
from django.db import connections
from django.db.models import Q
from django.db.utils import OperationalError, ProgrammingError
from django.http import JsonResponse
from django.shortcuts import render
from django.urls import reverse

from .models import (
    AlumnoSeccion,
    DocenteSeccion,
    EspecialDocenteBnh,
    PADRON_DB_ALIAS,
)
from .permisos import especial_required, get_permisos_especial_request
from .views_contexto import contexto_base


TIPOS_BUSQUEDA = {"alumno", "docente", "director"}


def _solo_digitos(valor):
    return re.sub(r"\D", "", str(valor or ""))


def _alumno_model():
    return apps.get_model("bnhalumnos", "Alumno")


def _es_administrador(request):
    return bool(get_permisos_especial_request(request).get("es_admin"))


def _exigir_administrador(request):
    if not _es_administrador(request):
        raise PermissionDenied("El Visualizador Global es exclusivo para administradores.")


def _error_busqueda(mensaje):
    return JsonResponse({"ok": False, "mensaje": mensaje, "resultados": []}, status=400)


def _buscar_personas(request, tipo):
    valor = (request.GET.get("q") or request.GET.get("cuil") or request.GET.get("dni") or "").strip()
    documento = _solo_digitos(valor)
    if len(documento) < 7:
        return _error_busqueda("Ingresá un CUIL o DNI válido para buscar.")

    if tipo == "alumno":
        alumnos = _alumno_model().objects.filter(
            Q(cuil=documento) | Q(nro_doc=documento)
        ).order_by("apellidos", "nombres")[:20]
        resultados = [
            {
                "nombre": f"{alumno.apellidos}, {alumno.nombres}",
                "dni": alumno.nro_doc or "",
                "cuil": alumno.cuil or "",
                "detalle_url": f"{reverse('especial:visualizador_detalle_alumno')}?cuil={alumno.cuil or documento}",
            }
            for alumno in alumnos
        ]
    elif tipo == "docente":
        docentes = EspecialDocenteBnh.objects.using(PADRON_DB_ALIAS).filter(
            Q(cuil=documento) | Q(dni=documento)
        ).order_by("apellido", "nombre")[:20]
        resultados = [
            {
                "nombre": docente.nombre_completo,
                "dni": docente.dni or "",
                "cuil": docente.cuil or "",
                "detalle_url": f"{reverse('especial:visualizador_detalle_docente')}?cuil={docente.cuil}",
            }
            for docente in docentes
        ]
    else:
        resultados = _buscar_directores(documento)

    return JsonResponse({"ok": True, "resultados": resultados})


def _buscar_directores(cuil):
    sql = """
        SELECT cueanexo, nom_est, oferta, localidad, departamento,
               estado_est, apellido_resp, nombre_resp, resploc_cuitcuil,
               resploc_email, resploc_telefono
          FROM v_capa_unica_ofertas_ant
         WHERE regexp_replace(COALESCE(resploc_cuitcuil, ''), '\\D', '', 'g') = %s
         ORDER BY cueanexo, nom_est, oferta
         LIMIT 50
    """
    try:
        with connections[PADRON_DB_ALIAS].cursor() as cursor:
            cursor.execute(sql, [cuil])
            columnas = [columna[0] for columna in cursor.description]
            filas = [dict(zip(columnas, fila)) for fila in cursor.fetchall()]
    except (OperationalError, ProgrammingError):
        return []

    return [
        {
            "nombre": " ".join(filter(None, [fila.get("apellido_resp"), fila.get("nombre_resp")])),
            "dni": "",
            "cuil": fila.get("resploc_cuitcuil") or cuil,
            "establecimiento": fila.get("nom_est") or "",
            "cueanexo": fila.get("cueanexo") or "",
            "detalle_url": f"{reverse('especial:visualizador_detalle_director')}?cuil={cuil}",
        }
        for fila in filas
    ]


def _datos_director(cuil):
    sql = """
        SELECT cueanexo, nom_est, oferta, localidad, departamento,
               estado_est, apellido_resp, nombre_resp, resploc_cuitcuil,
               resploc_email, resploc_telefono
          FROM v_capa_unica_ofertas_ant
         WHERE regexp_replace(COALESCE(resploc_cuitcuil, ''), '\\D', '', 'g') = %s
         ORDER BY cueanexo, nom_est, oferta
    """
    with connections[PADRON_DB_ALIAS].cursor() as cursor:
        cursor.execute(sql, [cuil])
        columnas = [columna[0] for columna in cursor.description]
        return [dict(zip(columnas, fila)) for fila in cursor.fetchall()]


def _persona_context(request, titulo):
    context = contexto_base(request, "visualizador", titulo, "Consulta global exclusiva para administradores.")
    context["visualizador_es_admin"] = True
    return context


@especial_required
def visualizador_inicio(request):
    _exigir_administrador(request)
    tipo = (request.GET.get("tipo") or "").lower()
    if request.headers.get("x-requested-with") == "XMLHttpRequest" and tipo in TIPOS_BUSQUEDA:
        try:
            return _buscar_personas(request, tipo)
        except (OperationalError, ProgrammingError):
            return JsonResponse({"ok": False, "mensaje": "No se pudo consultar la fuente de datos.", "resultados": []}, status=503)

    context = _persona_context(request, "Visualizador Global")
    context["opciones_visualizador"] = (
        ("alumno", "Buscar alumno", "fa-user-graduate"),
        ("docente", "Buscar docente", "fa-chalkboard-user"),
        ("director", "Buscar director", "fa-user-tie"),
    )
    return render(request, "especial/visualizador_inicio.html", context)


@especial_required
def visualizador_detalle_alumno(request):
    _exigir_administrador(request)
    cuil = _solo_digitos(request.GET.get("cuil"))
    alumno = None
    if len(cuil) == 11:
        alumno = _alumno_model().objects.filter(cuil=cuil).first()
    if not alumno and cuil:
        alumno = _alumno_model().objects.filter(nro_doc=cuil).first()
    context = _persona_context(request, "Detalle de alumno")
    context.update({"persona": alumno, "cuil_buscado": cuil, "inscripciones": []})
    if alumno:
        context["inscripciones"] = AlumnoSeccion.objects.filter(alumno=alumno).select_related(
            "seccion", "seccion__ciclo"
        ).order_by("seccion__cueanexo", "seccion__nombre_seccion", "-fecha_inscripcion")
    return render(request, "especial/visualizador_detalle_alumno.html", context)


@especial_required
def visualizador_detalle_docente(request):
    _exigir_administrador(request)
    cuil = _solo_digitos(request.GET.get("cuil"))
    docente = EspecialDocenteBnh.objects.using(PADRON_DB_ALIAS).filter(cuil=cuil).first() if len(cuil) == 11 else None
    context = _persona_context(request, "Detalle de docente")
    context.update({
        "persona": docente,
        "cuil_buscado": cuil,
        "asignaciones": [],
        "secciones_filtro": [],
        "cueanexos_filtro": [],
        "roles_filtro": DocenteSeccion.Rol.choices,
        "estados_filtro": DocenteSeccion.Estado.choices,
        "estados_seleccionados": set(
            request.GET.getlist("estado")
            if request.GET.get("estado_aplicado")
            else [estado for estado, _ in DocenteSeccion.Estado.choices]
        ),
        "filtro_seccion": request.GET.get("seccion", ""),
        "filtro_cueanexo": request.GET.get("cueanexo", ""),
        "filtro_rol": request.GET.get("rol", ""),
    })
    if docente:
        asignaciones_base = DocenteSeccion.objects.filter(docente_cuil=cuil).select_related(
            "seccion", "seccion__ciclo"
        )
        context["secciones_filtro"] = [
            {"id": seccion_id, "nombre": nombre, "cueanexo": cueanexo}
            for seccion_id, nombre, cueanexo in asignaciones_base.values_list(
                "seccion_id", "seccion__nombre_seccion", "seccion__cueanexo"
            ).distinct().order_by("seccion__cueanexo", "seccion__nombre_seccion")
        ]
        context["cueanexos_filtro"] = sorted(
            {cueanexo for _, _, cueanexo in context["secciones_filtro"]}
        )

        asignaciones = asignaciones_base
        seccion_id = request.GET.get("seccion")
        if seccion_id and seccion_id.isdigit():
            asignaciones = asignaciones.filter(seccion_id=int(seccion_id))
        cueanexo = _solo_digitos(request.GET.get("cueanexo"))
        if cueanexo:
            asignaciones = asignaciones.filter(seccion__cueanexo=cueanexo)
        rol = request.GET.get("rol")
        if rol in dict(DocenteSeccion.Rol.choices):
            asignaciones = asignaciones.filter(rol=rol)
        estados = set(request.GET.getlist("estado"))
        estados_validos = {estado for estado, _ in DocenteSeccion.Estado.choices}
        if request.GET.get("estado_aplicado"):
            asignaciones = asignaciones.filter(estado__in=estados & estados_validos)
        else:
            asignaciones = asignaciones.filter(estado__in=estados_validos)

        context["asignaciones"] = asignaciones.order_by(
            "seccion__cueanexo", "seccion__nombre_seccion", "-fecha_desde"
        )
    return render(request, "especial/visualizador_detalle_docente.html", context)


@especial_required
def visualizador_detalle_director(request):
    _exigir_administrador(request)
    cuil = _solo_digitos(request.GET.get("cuil"))
    context = _persona_context(request, "Detalle de director")
    filas = []
    error = ""
    if len(cuil) == 11:
        try:
            filas = _datos_director(cuil)
        except (OperationalError, ProgrammingError):
            error = "No se pudo consultar la información del Padrón."
    context.update({"director": filas[0] if filas else None, "escuelas": filas, "cuil_buscado": cuil, "consulta_error": error})
    return render(request, "especial/visualizador_detalle_director.html", context)
