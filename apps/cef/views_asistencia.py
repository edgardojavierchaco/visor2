# -*- coding: utf-8 -*-

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db.models import Count, Exists, OuterRef, Prefetch, Q, Subquery
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from .forms import CefAsistenciaFechaForm
from .models import (
    CefAsistencia,
    CefAsistenciaMovimiento,
    CefDocenteGrupo,
    CefGrupo,
    CefGrupoDiaFuncionamiento,
    CefInscripcion,
    CefJornadaAsistencia,
    normalizar_cuil_usuario,
)
from .permisos import cef_asistencia_required, get_permisos_cef_request
from .services_asistencia import (
    inscripciones_vigentes_jornada,
    registrar_asistencias_jornada,
)
from .views_contexto import contexto_base, redirect_con_contexto


def _url_asistencia(
    grupo,
    cef_context,
    fecha=None,
    modo_historial=False,
):
    url = redirect_con_contexto(
        "cef:asistencia_grupo",
        cef_context,
        grupo_id=grupo.pk,
    )
    separador = "&" if "?" in url else "?"
    params = []
    if fecha:
        params.append(f"fecha={fecha.isoformat()}")
    if modo_historial:
        params.append("modo=historial")
    return f"{url}{separador}{'&'.join(params)}" if params else url


def _grupos_asistencia_queryset(request, cef_context):
    permisos = get_permisos_cef_request(request)
    queryset = CefGrupo.objects.filter(
        cueanexo=cef_context["cueanexo"],
        ciclo=cef_context["ciclo"],
    )

    if permisos.get("es_profesor_cef"):
        cuil = normalizar_cuil_usuario(request.user)
        if not cuil:
            return queryset.none()
        queryset = queryset.filter(
            estado=CefGrupo.Estado.ACTIVO,
            docentes__docente_cuil=cuil,
            docentes__estado=CefDocenteGrupo.Estado.ACTIVO,
            docentes__rol__in=(
                CefDocenteGrupo.Rol.TITULAR,
                CefDocenteGrupo.Rol.SUPLENTE,
            ),
        )

    return queryset.distinct()


def _grupos_asistencia_listado(request, cef_context):
    hoy = timezone.localdate()
    docentes_activos = CefDocenteGrupo.objects.filter(
        estado=CefDocenteGrupo.Estado.ACTIVO,
        rol__in=(
            CefDocenteGrupo.Rol.TITULAR,
            CefDocenteGrupo.Rol.SUPLENTE,
        ),
    ).order_by("rol", "docente_nombre_snapshot", "docente_cuil")
    dias = CefGrupoDiaFuncionamiento.objects.select_related(
        "dia_semana"
    ).order_by("dia_semana__orden", "dia_semana__numero")
    ultima_asistencia = (
        CefJornadaAsistencia.objects.filter(
            grupo_id=OuterRef("pk"),
            asistencias__isnull=False,
        )
        .order_by("-fecha", "-pk")
        .values("fecha")[:1]
    )
    asistencia_hoy = CefAsistencia.objects.filter(
        jornada__grupo_id=OuterRef("pk"),
        jornada__fecha=hoy,
    )

    return (
        _grupos_asistencia_queryset(request, cef_context)
        .filter(estado=CefGrupo.Estado.ACTIVO)
        .select_related("ciclo", "actividad", "turno")
        .prefetch_related(
            Prefetch("dias_funcionamiento", queryset=dias, to_attr="dias_asistencia"),
            Prefetch("docentes", queryset=docentes_activos, to_attr="docentes_activos"),
        )
        .annotate(
            total_alumnos=Count(
                "inscripciones__alumno",
                filter=Q(inscripciones__estado=CefInscripcion.Estado.ACTIVO),
                distinct=True,
            ),
            ultima_asistencia_fecha=Subquery(ultima_asistencia),
            asistencia_hoy_cargada=Exists(asistencia_hoy),
        )
        .order_by("actividad__nombre", "numero", "pk")
    )


def _ultima_fecha_cargada(grupo):
    return (
        CefJornadaAsistencia.objects.filter(
            grupo=grupo,
            asistencias__isnull=False,
        )
        .order_by("-fecha", "-pk")
        .values_list("fecha", flat=True)
        .first()
    )


def _resolver_fecha_asistencia(request, grupo, solo_lectura):
    fecha_error = None
    raw_fecha = request.GET.get("fecha", "").strip()
    if raw_fecha:
        fecha_form = CefAsistenciaFechaForm({"fecha": raw_fecha})
        if fecha_form.is_valid():
            fecha = fecha_form.cleaned_data["fecha"]
            if fecha.year == grupo.ciclo.anio:
                return (
                    CefAsistenciaFechaForm(initial={"fecha": fecha}),
                    fecha,
                    None,
                )
            fecha_error = "La fecha debe pertenecer al año del ciclo seleccionado."
        else:
            fecha_error = "La fecha de asistencia no es válida."

    fecha = None
    if solo_lectura:
        fecha = _ultima_fecha_cargada(grupo)
    else:
        hoy = timezone.localdate()
        if grupo.ciclo.anio == hoy.year:
            fecha = hoy
    initial = {"fecha": fecha} if fecha else None
    return CefAsistenciaFechaForm(initial=initial), fecha, fecha_error


@cef_asistencia_required
@require_http_methods(["GET"])
def asistencia(request):
    context = contexto_base(request, "asistencia", "Asistencia CEF")
    cef_context = context["cef_context"]
    cef_context["selector_action"] = reverse("cef:asistencia")
    grupos = []
    hoy = timezone.localdate()

    if cef_context["puede_consultar"]:
        grupos = list(_grupos_asistencia_listado(request, cef_context))
        cuil_usuario = normalizar_cuil_usuario(request.user)
        for grupo in grupos:
            grupo.docentes_visibles = grupo.docentes_activos
            if cef_context["es_profesor_cef"]:
                grupo.docentes_visibles = [
                    asignacion
                    for asignacion in grupo.docentes_activos
                    if asignacion.docente_cuil == cuil_usuario
                ]
            ciclo_operativo_hoy = (
                grupo.ciclo.anio == hoy.year
                and not grupo.ciclo.cerrado
                and cef_context["puede_operar"]
            )
            if not ciclo_operativo_hoy:
                grupo.estado_hoy = "No aplica"
                grupo.estado_hoy_clase = "secondary"
                grupo.accion_asistencia = "Ver asistencias"
                grupo.asistencia_url = _url_asistencia(grupo, cef_context)
            elif grupo.asistencia_hoy_cargada:
                grupo.estado_hoy = "Cargada hoy"
                grupo.estado_hoy_clase = "success"
                grupo.accion_asistencia = "Ver asistencia"
                grupo.asistencia_url = _url_asistencia(grupo, cef_context, hoy)
            else:
                grupo.estado_hoy = "Pendiente hoy"
                grupo.estado_hoy_clase = "warning"
                grupo.accion_asistencia = "Tomar asistencia"
                grupo.asistencia_url = _url_asistencia(grupo, cef_context, hoy)

    context.update({"grupos": grupos, "hoy": hoy})
    return render(request, "cef/asistencia_cef.html", context)


def _estados_post(request):
    prefijo = "asistencia_"
    return {
        clave[len(prefijo):]: valor
        for clave, valor in request.POST.items()
        if clave.startswith(prefijo)
    }


@cef_asistencia_required
@require_http_methods(["GET", "POST"])
def asistencia_grupo(request, grupo_id):
    context = contexto_base(request, "asistencia", "Asistencia del grupo CEF")
    cef_context = context["cef_context"]
    cef_context["selector_action"] = reverse("cef:asistencia")
    if not cef_context["puede_consultar"]:
        messages.warning(
            request,
            "Seleccioná un CUE-Anexo y un ciclo lectivo para consultar asistencia.",
        )
        return redirect(redirect_con_contexto("cef:asistencia", cef_context))

    modo_historial = (
        request.GET.get("modo") or request.POST.get("modo")
    ) == "historial"
    grupo = get_object_or_404(
        _grupos_asistencia_queryset(request, cef_context)
        .select_related("ciclo", "actividad", "turno")
        .prefetch_related("dias_funcionamiento__dia_semana"),
        pk=grupo_id,
    )
    solo_lectura = (
        modo_historial
        or grupo.ciclo.cerrado
        or grupo.estado != CefGrupo.Estado.ACTIVO
        or not cef_context["puede_operar"]
    )

    if request.method == "POST":
        form_post = CefAsistenciaFechaForm(request.POST)
        fecha_post = (
            form_post.cleaned_data.get("fecha")
            if form_post.is_valid()
            else None
        )
        if solo_lectura:
            messages.error(
                request,
                "La asistencia se encuentra en modo sólo lectura.",
            )
        elif not fecha_post:
            messages.error(request, "La fecha de asistencia no es válida.")
        elif request.POST.get("accion") != "guardar_asistencia":
            messages.error(request, "La acción de asistencia no es válida.")
        else:
            try:
                resultado = registrar_asistencias_jornada(
                    grupo,
                    fecha_post,
                    _estados_post(request),
                    request.user,
                )
            except ValidationError as exc:
                messages.error(request, " ".join(exc.messages))
            else:
                fecha_texto = fecha_post.strftime("%d/%m/%Y")
                if not resultado["cargada_previamente"]:
                    mensaje = (
                        f"Asistencia del {fecha_texto} guardada correctamente."
                    )
                elif resultado["altas"] or resultado["cambios"]:
                    mensaje = (
                        f"Asistencia del {fecha_texto} actualizada correctamente."
                    )
                else:
                    mensaje = (
                        f"La asistencia del {fecha_texto} ya estaba guardada "
                        "y no presentó cambios."
                    )
                messages.success(request, mensaje)
        return redirect(
            _url_asistencia(
                grupo,
                cef_context,
                fecha_post,
                modo_historial,
            )
        )

    dias_habituales = list(grupo.dias_funcionamiento.all())
    fecha_form, fecha, fecha_error = _resolver_fecha_asistencia(
        request,
        grupo,
        solo_lectura,
    )

    jornada = None
    inscripciones = []
    asistencias = {}
    movimientos = []
    if fecha:
        jornada = (
            CefJornadaAsistencia.objects.filter(grupo=grupo, fecha=fecha)
            .select_related("grupo__ciclo")
            .first()
        )
        inscripciones = list(inscripciones_vigentes_jornada(grupo, fecha))
        if jornada:
            inscripciones_ids = [item.pk for item in inscripciones]
            asistencias = {
                item.inscripcion_id: item
                for item in (
                    CefAsistencia.objects.filter(
                        jornada=jornada,
                        inscripcion_id__in=inscripciones_ids,
                    )
                    .select_related("inscripcion__alumno")
                    .order_by("inscripcion_id")
                )
            }
            movimientos = list(
                CefAsistenciaMovimiento.objects.filter(
                    asistencia__jornada=jornada
                )
                .select_related(
                    "asistencia__inscripcion__alumno",
                    "creado_por",
                )
                .order_by("-creado_en", "-pk")
            )
    for inscripcion in inscripciones:
        inscripcion.asistencia_actual = asistencias.get(inscripcion.pk)

    asistencia_cargada = bool(asistencias)
    presentes = sum(
        1
        for item in asistencias.values()
        if item.estado == CefAsistencia.Estado.PRESENTE
    )
    ausentes = sum(
        1
        for item in asistencias.values()
        if item.estado == CefAsistencia.Estado.AUSENTE
    )
    justificadas = sum(
        1
        for item in asistencias.values()
        if item.estado == CefAsistencia.Estado.JUSTIFICADA
    )
    jornadas_registradas = list(
        CefJornadaAsistencia.objects.filter(grupo=grupo)
        .annotate(
            total_registros=Count("asistencias", distinct=True),
            presentes=Count(
                "asistencias__inscripcion__alumno",
                filter=Q(asistencias__estado=CefAsistencia.Estado.PRESENTE),
                distinct=True,
            ),
            ausentes=Count(
                "asistencias__inscripcion__alumno",
                filter=Q(asistencias__estado=CefAsistencia.Estado.AUSENTE),
                distinct=True,
            ),
            justificadas=Count(
                "asistencias__inscripcion__alumno",
                filter=Q(asistencias__estado=CefAsistencia.Estado.JUSTIFICADA),
                distinct=True,
            ),
        )
        .order_by("-fecha", "-pk")
    )
    for item in jornadas_registradas:
        item.seleccionada = item.fecha == fecha
        item.url_asistencia = _url_asistencia(
            grupo,
            cef_context,
            item.fecha,
            modo_historial,
        )
    cantidad_jornadas_registradas = sum(
        1 for item in jornadas_registradas if item.total_registros
    )

    fecha_futura = bool(fecha and fecha > timezone.localdate())
    context.update(
        {
            "grupo": grupo,
            "fecha_form": fecha_form,
            "fecha": fecha,
            "fecha_error": fecha_error,
            "dias_habituales": dias_habituales,
            "jornada": jornada,
            "inscripciones": inscripciones,
            "estado_choices": CefAsistencia.Estado.choices,
            "movimientos": movimientos,
            "jornadas_registradas": jornadas_registradas,
            "cantidad_jornadas_registradas": cantidad_jornadas_registradas,
            "fecha_futura": fecha_futura,
            "solo_lectura": solo_lectura,
            "asistencia_cargada": asistencia_cargada,
            "presentes": presentes,
            "ausentes": ausentes,
            "justificadas": justificadas,
            "modo_historial": modo_historial,
            "asistencia_url": _url_asistencia(
                grupo,
                cef_context,
                modo_historial=modo_historial,
            ),
            "asistencia_inicio_url": redirect_con_contexto(
                "cef:asistencia",
                cef_context,
            ),
        }
    )
    if request.headers.get("X-Cef-Asistencia-Fragment") == "workspace":
        response = render(
            request,
            "cef/asistencia_grupo_workspace_cef.html",
            context,
        )
        response["X-Cef-Asistencia-Fragment"] = "workspace"
        return response
    return render(request, "cef/asistencia_grupo_cef.html", context)
