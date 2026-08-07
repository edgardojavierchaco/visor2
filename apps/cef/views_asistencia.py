# -*- coding: utf-8 -*-

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from .forms import CefAsistenciaFechaForm
from .models import (
    CefAsistencia,
    CefAsistenciaMovimiento,
    CefGrupo,
    CefJornadaAsistencia,
)
from .permisos import cef_required
from .services_asistencia import (
    fecha_jornada_habitual,
    inscripciones_vigentes_jornada,
    registrar_asistencias_jornada,
)
from .views_contexto import contexto_base, redirect_con_contexto


def _url_asistencia(grupo, cef_context, fecha=None, modo_historial=False):
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


def _estados_post(request):
    prefijo = "asistencia_"
    return {
        clave[len(prefijo):]: valor
        for clave, valor in request.POST.items()
        if clave.startswith(prefijo)
    }


@cef_required
@require_http_methods(["GET", "POST"])
def asistencia_grupo(request, grupo_id):
    context = contexto_base(request, "grupos", "Asistencia del curso CEF")
    cef_context = context["cef_context"]
    if not cef_context["puede_consultar"]:
        messages.warning(
            request,
            "Seleccioná un CUE-Anexo y un ciclo lectivo para consultar asistencia.",
        )
        return redirect(redirect_con_contexto("cef:carga_grupo", cef_context))

    modo_historial = (
        request.GET.get("modo") or request.POST.get("modo")
    ) == "historial"
    grupos_permitidos = CefGrupo.objects.filter(
        cueanexo=cef_context["cueanexo"],
    )
    if not modo_historial:
        grupos_permitidos = grupos_permitidos.filter(
            ciclo=cef_context["ciclo"],
        )
    grupo = get_object_or_404(
        grupos_permitidos
        .select_related("ciclo", "actividad", "turno")
        .prefetch_related("dias_funcionamiento__dia_semana"),
        pk=grupo_id,
    )

    if request.method == "POST":
        if modo_historial:
            messages.error(
                request,
                "La consulta histórica de asistencia es de sólo lectura.",
            )
            return redirect(
                _url_asistencia(
                    grupo,
                    cef_context,
                    modo_historial=True,
                )
            )
        form_post = CefAsistenciaFechaForm(request.POST)
        if not form_post.is_valid():
            messages.error(request, "La fecha de la jornada no es válida.")
            return redirect(
                _url_asistencia(
                    grupo,
                    cef_context,
                    modo_historial=modo_historial,
                )
            )
        if not cef_context["puede_operar"]:
            messages.error(
                request,
                "El ciclo está cerrado. La asistencia se encuentra en modo sólo lectura.",
            )
            return redirect(
                _url_asistencia(
                    grupo,
                    cef_context,
                    form_post.cleaned_data["fecha"],
                    modo_historial,
                )
            )
        try:
            resultado = registrar_asistencias_jornada(
                grupo,
                form_post.cleaned_data["fecha"],
                _estados_post(request),
                request.user,
            )
        except ValidationError as exc:
            messages.error(request, " ".join(exc.messages))
        else:
            if resultado["jornada_creada"]:
                mensaje = "Jornada creada correctamente."
            elif resultado["altas"] or resultado["cambios"]:
                mensaje = "Asistencia actualizada correctamente."
            else:
                mensaje = "La jornada ya estaba abierta y no presentó cambios."
            messages.success(request, mensaje)
        return redirect(
            _url_asistencia(
                grupo,
                cef_context,
                form_post.cleaned_data["fecha"],
                modo_historial,
            )
        )

    fecha_form = CefAsistenciaFechaForm(request.GET or None)
    if fecha_form.is_bound and fecha_form.is_valid():
        fecha = fecha_form.cleaned_data["fecha"]
    elif fecha_form.is_bound:
        fecha = timezone.localdate()
        messages.error(request, "La fecha de la jornada no es válida.")
    else:
        fecha = timezone.localdate()

    jornada = (
        CefJornadaAsistencia.objects.filter(grupo=grupo, fecha=fecha)
        .select_related("grupo__ciclo")
        .first()
    )
    inscripciones = list(inscripciones_vigentes_jornada(grupo, fecha))
    asistencias = {}
    movimientos = []
    if jornada:
        asistencias = {
            item.inscripcion_id: item
            for item in (
                CefAsistencia.objects.filter(jornada=jornada)
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
    denominador = presentes + ausentes
    porcentaje = round((presentes * 100) / denominador) if denominador else None

    jornadas_anteriores = list(
        CefJornadaAsistencia.objects.filter(grupo=grupo)
        .annotate(
            presentes=Count(
                "asistencias",
                filter=Q(asistencias__estado=CefAsistencia.Estado.PRESENTE),
            ),
            ausentes=Count(
                "asistencias",
                filter=Q(asistencias__estado=CefAsistencia.Estado.AUSENTE),
            ),
            justificadas=Count(
                "asistencias",
                filter=Q(asistencias__estado=CefAsistencia.Estado.JUSTIFICADA),
            ),
        )
        .order_by("-fecha", "-pk")[:20]
    )
    for item in jornadas_anteriores:
        item.url_asistencia = _url_asistencia(
            grupo,
            cef_context,
            item.fecha,
            modo_historial,
        )

    gestionar_url = redirect_con_contexto(
        "cef:gestionar_grupo",
        cef_context,
        grupo_id=grupo.pk,
    )
    if modo_historial:
        separador = "&" if "?" in gestionar_url else "?"
        gestionar_url = f"{gestionar_url}{separador}modo=historial"

    context.update(
        {
            "grupo": grupo,
            "fecha_form": fecha_form,
            "fecha": fecha,
            "jornada": jornada,
            "inscripciones": inscripciones,
            "estado_choices": CefAsistencia.Estado.choices,
            "movimientos": movimientos,
            "jornadas_anteriores": jornadas_anteriores,
            "fecha_habitual": fecha_jornada_habitual(grupo, fecha),
            "solo_lectura": (
                modo_historial
                or grupo.ciclo.cerrado
                or grupo.estado != CefGrupo.Estado.ACTIVO
                or not cef_context["puede_operar"]
            ),
            "presentes": presentes,
            "ausentes": ausentes,
            "justificadas": justificadas,
            "porcentaje": porcentaje,
            "porcentaje_disponible": porcentaje is not None,
            "modo_historial": modo_historial,
            "asistencia_url": _url_asistencia(
                grupo,
                cef_context,
                modo_historial=modo_historial,
            ),
            "gestionar_url": gestionar_url,
        }
    )
    return render(request, "cef/asistencia_grupo_cef.html", context)
