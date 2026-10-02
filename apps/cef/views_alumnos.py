# -*- coding: utf-8 -*-

import re
from urllib.parse import urlencode

from django.apps import apps
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.db.models import Q
from django.db.utils import OperationalError, ProgrammingError
from django.urls import NoReverseMatch, reverse
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.views.decorators.http import require_GET

from .forms import CefBajaMotivoForm, CefBusquedaAlumnoForm
from .models import CefAlumnoCef, CefGrupo, CefInscripcion
from .permisos import cef_required
from .performance import perf_render, perf_start_view
from .services import (
    asegurar_alumno_banco_activo,
    crear_inscripcion_activa,
    dar_baja_alumno_banco,
)
from .views_contexto import (
    contexto_base,
    normalizar_vista_cef,
    render_fragmento_cef,
    resolver_contexto_operativo,
)


MSG_BANCO_ALUMNOS_PENDIENTE = (
    "El banco de alumnos del CEF todavía no está disponible."
)


def _solo_digitos(valor):
    return re.sub(r"\D", "", str(valor or ""))


def _is_ajax(request):
    return request.headers.get("x-requested-with") == "XMLHttpRequest"


def _alumno_model():
    return apps.get_model("bnhalumnos", "Alumno")


def _buscar_alumno_identidad(*, tipo_doc, nro_doc="", cuil=""):
    """Resuelve una identidad fuerte sin depender exclusivamente del CUIL."""

    alumno_model = _alumno_model()
    por_documento = None
    por_cuil = None

    if tipo_doc and nro_doc:
        coincidencias_documento = list(
            alumno_model.objects.filter(
                tipo_doc=tipo_doc,
                nro_doc__iexact=nro_doc,
            )
            .order_by("pk")[:2]
        )
        if len(coincidencias_documento) > 1:
            raise ValidationError(
                "Hay más de un alumno con ese tipo y número de documento. "
                "No se seleccionó ninguno automáticamente."
            )
        por_documento = coincidencias_documento[0] if coincidencias_documento else None

    if cuil:
        coincidencias_cuil = list(
            alumno_model.objects.filter(cuil=cuil).order_by("pk")[:2]
        )
        if len(coincidencias_cuil) > 1:
            raise ValidationError(
                "Hay más de un alumno con ese CUIL. "
                "No se seleccionó ninguno automáticamente."
            )
        por_cuil = coincidencias_cuil[0] if coincidencias_cuil else None

    if por_documento and por_cuil and por_documento.pk != por_cuil.pk:
        raise ValidationError(
            "El documento y el CUIL informados corresponden a alumnos distintos."
        )

    return por_documento or por_cuil


def _alumno_por_id(valor):
    try:
        alumno_id = int(valor or "")
    except (TypeError, ValueError):
        return None
    return _alumno_model().objects.filter(pk=alumno_id).first()


def _buscar_alumno_sin_documento(
    *,
    apellidos,
    nombres,
    tipo_doc,
    fecha_nacimiento,
    sexo,
):
    """Busca un alumno sin número documental por sus datos actuales exactos.

    id_persona_jurisdiccional permanece inmutable en BNH y puede reflejar
    datos históricos si luego se corrigieron nombre, fecha o sexo. Por eso la
    recuperación operativa de CEF compara los campos actuales por separado,
    con la misma normalización estable usada por BNH y sin hacer coincidencias
    difusas ni elegir silenciosamente entre homónimos.
    """

    from apps.bnhalumnos.models import normalizar_componente_id_jurisdiccional

    apellido_normalizado = normalizar_componente_id_jurisdiccional(apellidos)
    nombre_normalizado = normalizar_componente_id_jurisdiccional(nombres)
    sexo_id = getattr(sexo, "pk", sexo)

    candidatos = (
        _alumno_model().objects
        .filter(
            tipo_doc=tipo_doc,
            fecha_nacimiento=fecha_nacimiento,
            sexo_id=sexo_id,
        )
        .filter(Q(nro_doc__isnull=True) | Q(nro_doc=""))
        .order_by("pk")
    )

    coincidencias = []
    for candidato in candidatos:
        if (
            normalizar_componente_id_jurisdiccional(candidato.apellidos)
            == apellido_normalizado
            and normalizar_componente_id_jurisdiccional(candidato.nombres)
            == nombre_normalizado
        ):
            coincidencias.append(candidato)
            if len(coincidencias) > 1:
                break

    if len(coincidencias) > 1:
        raise ValidationError(
            "Se encontró más de un alumno cargado con esos datos. "
            "Verifique la información antes de continuar; no se seleccionó ninguno automáticamente."
        )

    return coincidencias[0] if coincidencias else None


def _resolver_alumno_o_sge(*, tipo_doc, nro_doc="", cuil=""):
    """Busca primero en BNH y, si no existe, consulta la materializada SGE."""

    alumno = _buscar_alumno_identidad(
        tipo_doc=tipo_doc,
        nro_doc=nro_doc,
        cuil=cuil,
    )
    if alumno:
        return alumno, None

    # Reutiliza exactamente el resolver que usa Carga Alumno para no duplicar
    # equivalencias ni reglas de identidad entre CEF y BNH.
    from apps.bnhalumnos.views import (
        SGEConsultaNoDisponible,
        _resolver_persona_sge,
    )

    try:
        persona_sge = _resolver_persona_sge(
            cuil=cuil or None,
            tipo_doc=tipo_doc,
            nro_doc=nro_doc or None,
        )
    except SGEConsultaNoDisponible as exc:
        raise ValidationError(str(exc)) from exc

    if not persona_sge:
        return None, None

    id_persona_sge = persona_sge.get("id_persona_sge")
    if id_persona_sge:
        alumno_vinculado = (
            _alumno_model().objects
            .filter(id_persona_sge=id_persona_sge)
            .first()
        )
        if alumno_vinculado:
            return alumno_vinculado, None

    return None, persona_sge


def _persona_sge_row(persona_sge):
    if not persona_sge:
        return None

    alumno_model = _alumno_model()

    def catalogo_label(campo, pk):
        if pk in (None, ""):
            return ""
        modelo = alumno_model._meta.get_field(campo).remote_field.model
        item = modelo.objects.filter(pk=pk).first()
        return str(item) if item else str(pk)

    fecha_nac = persona_sge.get("fecha_nacimiento")
    if isinstance(fecha_nac, str):
        fecha_nac = parse_date(fecha_nac)

    return {
        "apellidos": persona_sge.get("apellidos") or "",
        "nombres": persona_sge.get("nombres") or "",
        "tipo_doc": catalogo_label("tipo_doc", persona_sge.get("tipo_doc")),
        "nro_doc": persona_sge.get("nro_doc") or "",
        "cuil": persona_sge.get("cuil") or "",
        "fecha_nac": fecha_nac,
        "sexo": catalogo_label("sexo", persona_sge.get("sexo")),
        "lugar_nac": persona_sge.get("lugar_nacimiento") or "",
    }


def _texto(valor):
    if valor is None:
        return ""
    return str(valor)


def _calcular_edad(fecha_nacimiento):
    if not fecha_nacimiento:
        return None

    hoy = timezone.localdate()
    edad = hoy.year - fecha_nacimiento.year
    if (hoy.month, hoy.day) < (fecha_nacimiento.month, fecha_nacimiento.day):
        edad -= 1
    return edad if edad >= 0 else None


def _alumno_row(alumno):
    if not alumno:
        return None
    return {
        "apellidos": getattr(alumno, "apellidos", "") or "",
        "nombres": getattr(alumno, "nombres", "") or "",
        "tipo_doc": _texto(getattr(alumno, "tipo_doc", "")),
        "nro_doc": getattr(alumno, "nro_doc", "") or "",
        "cuil": getattr(alumno, "cuil", "") or "",
        "fecha_nac": getattr(alumno, "fecha_nacimiento", None),
        "sexo": _texto(getattr(alumno, "sexo", "")),
        "lugar_nac": (
            _texto(getattr(alumno, "loc_nacimiento", ""))
            or getattr(alumno, "lugar_nacimiento", "")
            or ""
        ),
    }


def _url_carga_alumno(
    next_url,
    return_label="Volver a Alumnos",
    *,
    alumno=None,
    tipo_doc="",
    nro_doc="",
    cuil="",
    apellidos="",
    nombres="",
    fecha_nacimiento="",
    sexo="",
):
    try:
        base = reverse("bnhalumnos:carga_alumno")
    except NoReverseMatch:
        return ""

    params = {}
    if alumno is not None:
        params["alumno_id"] = alumno.pk
    else:
        if tipo_doc:
            params["tipo_doc"] = getattr(tipo_doc, "pk", tipo_doc)
        if nro_doc:
            params["nro_doc"] = nro_doc
        if cuil:
            params["cuil"] = cuil
        if apellidos:
            params["apellidos"] = apellidos
        if nombres:
            params["nombres"] = nombres
        if fecha_nacimiento:
            params["fecha_nacimiento"] = (
                fecha_nacimiento.isoformat()
                if hasattr(fecha_nacimiento, "isoformat")
                else fecha_nacimiento
            )
        if sexo:
            params["sexo"] = getattr(sexo, "pk", sexo)
    if next_url:
        params["next"] = next_url
    if return_label:
        params["return_label"] = return_label
    return f"{base}?{urlencode(params)}" if params else base


def _url_modal_alumnos(
    cef_context,
    *,
    alumno_id="",
    tipo_doc="",
    nro_doc="",
    cuil="",
    apellidos="",
    nombres="",
    fecha_nacimiento="",
    sexo="",
):
    params = {}
    if cef_context.get("cueanexo"):
        params["cueanexo"] = cef_context["cueanexo"]
    if cef_context.get("ciclo"):
        params["ciclo"] = cef_context["ciclo"].pk
    params["abrir_modal_alumno"] = "1"
    if alumno_id:
        params["alumno_id"] = getattr(alumno_id, "pk", alumno_id)
    if tipo_doc:
        params["tipo_doc"] = getattr(tipo_doc, "pk", tipo_doc)
    if nro_doc:
        params["nro_doc"] = nro_doc
    if cuil:
        params["cuil"] = cuil
    if apellidos:
        params["apellidos"] = apellidos
    if nombres:
        params["nombres"] = nombres
    if fecha_nacimiento:
        params["fecha_nacimiento"] = (
            fecha_nacimiento.isoformat()
            if hasattr(fecha_nacimiento, "isoformat")
            else fecha_nacimiento
        )
    if sexo:
        params["sexo"] = getattr(sexo, "pk", sexo)
    return f"{reverse('cef:alumnos')}?{urlencode(params)}"


def _url_alumnos(cef_context, vista="actuales"):
    params = {}
    if cef_context.get("cueanexo"):
        params["cueanexo"] = cef_context["cueanexo"]
    if cef_context.get("ciclo"):
        params["ciclo"] = cef_context["ciclo"].pk
    if normalizar_vista_cef(vista) == "historial":
        params["vista"] = "historial"
    querystring = urlencode(params)
    url = reverse("cef:alumnos")
    return f"{url}?{querystring}" if querystring else url


def _errores_form(form):
    return " ".join(error for errors in form.errors.values() for error in errors)


def _pk_post(request, campo):
    try:
        return int(request.POST.get(campo) or "")
    except (TypeError, ValueError):
        return None


def _inscribir_alumno_grupo_desde_banco(request, cef_context):
    if not cef_context["puede_operar"]:
        messages.error(
            request,
            "Seleccioná un CUE-Anexo y un ciclo lectivo para inscribir alumnos.",
        )
        return

    alumno_banco_id = _pk_post(request, "alumno_banco_id")
    grupo_id = _pk_post(request, "grupo_id")

    if not alumno_banco_id or not grupo_id:
        messages.error(request, "No se pudo identificar el alumno o el grupo.")
        return

    alumno_banco = (
        CefAlumnoCef.objects.filter(
            pk=alumno_banco_id,
            cueanexo=cef_context["cueanexo"],
            ciclo=cef_context["ciclo"],
            estado=CefAlumnoCef.Estado.ACTIVO,
        )
        .select_related("alumno")
        .first()
    )
    if not alumno_banco:
        messages.error(request, "El alumno no está activo en el banco de alumnos de este CEF y ciclo.")
        return

    grupo = CefGrupo.objects.filter(
        pk=grupo_id,
        cueanexo=cef_context["cueanexo"],
        ciclo=cef_context["ciclo"],
        estado=CefGrupo.Estado.ACTIVO,
    ).first()
    if not grupo:
        messages.error(request, "El grupo no corresponde al CEF y ciclo seleccionados.")
        return

    inscripcion_activa = CefInscripcion.objects.filter(
        grupo=grupo,
        alumno=alumno_banco.alumno,
        estado=CefInscripcion.Estado.ACTIVO,
    ).exists()
    if inscripcion_activa:
        messages.info(request, "El alumno ya se encuentra inscripto en ese grupo.")
        return

    try:
        crear_inscripcion_activa(
            grupo=grupo,
            alumno=alumno_banco.alumno,
            user=request.user,
            fecha_inscripcion=request.POST.get("fecha_inscripcion"),
        )
        messages.success(request, "Alumno inscripto correctamente al grupo.")
    except ValidationError as exc:
        messages.error(request, "; ".join(exc.messages))
    except IntegrityError:
        messages.error(
            request,
            "No se pudo crear la inscripción. Verificá que no exista una inscripción activa.",
        )


def _inscribir_alumno_grupo_desde_historial(request, cef_context):
    if not cef_context["puede_operar"]:
        messages.error(
            request,
            "El ciclo está cerrado. La información se encuentra en modo sólo lectura.",
        )
        return

    periodo_id = _pk_post(request, "periodo_historico_id")
    grupo_id = _pk_post(request, "grupo_id")
    if not periodo_id or not grupo_id:
        messages.error(request, "No se pudo identificar el alumno o el grupo.")
        return

    periodo = get_object_or_404(
        CefAlumnoCef.objects.filter(
            cueanexo=cef_context["cueanexo"],
            ciclo__anio__lt=cef_context["ciclo"].anio,
        ).select_related("alumno"),
        pk=periodo_id,
    )
    alumno_activo_actual = CefAlumnoCef.objects.filter(
        cueanexo=cef_context["cueanexo"],
        ciclo=cef_context["ciclo"],
        alumno_id=periodo.alumno_id,
        estado=CefAlumnoCef.Estado.ACTIVO,
    ).exists()
    if not alumno_activo_actual:
        messages.error(request, "El alumno debe reincorporarse primero al CEF.")
        return

    grupo = CefGrupo.objects.filter(
        pk=grupo_id,
        cueanexo=cef_context["cueanexo"],
        ciclo=cef_context["ciclo"],
        estado=CefGrupo.Estado.ACTIVO,
    ).first()
    if not grupo:
        messages.error(request, "El grupo seleccionado no pertenece al CEF y ciclo actual.")
        return

    try:
        crear_inscripcion_activa(
            grupo=grupo,
            alumno=periodo.alumno,
            user=request.user,
            fecha_inscripcion=request.POST.get("fecha_inscripcion"),
        )
        messages.success(request, "Alumno inscripto correctamente al grupo actual.")
    except ValidationError as exc:
        messages.error(request, "; ".join(exc.messages))
    except IntegrityError:
        messages.error(
            request,
            "No se pudo crear la inscripción. Verificá que no exista una inscripción activa.",
        )


def _alumnos_banco(cef_context):
    if not cef_context["puede_consultar"]:
        return CefAlumnoCef.objects.none()

    return (
        CefAlumnoCef.objects.filter(
            cueanexo=cef_context["cueanexo"],
            ciclo=cef_context["ciclo"],
            estado=CefAlumnoCef.Estado.ACTIVO,
        )
        .select_related("alumno")
        .order_by("alumno_nombre_snapshot", "alumno_cuil_snapshot")
    )


def _alumnos_bajas_ciclo(cef_context):
    if not cef_context["puede_consultar"]:
        return CefAlumnoCef.objects.none()
    return (
        CefAlumnoCef.objects.filter(
            cueanexo=cef_context["cueanexo"],
            ciclo=cef_context["ciclo"],
            estado=CefAlumnoCef.Estado.BAJA,
        )
        .select_related("alumno", "ciclo")
        .order_by("alumno_nombre_snapshot", "-fecha_alta", "-pk")
    )


def _alumnos_historial(cef_context):
    if not cef_context["puede_consultar"]:
        return CefAlumnoCef.objects.none()
    return (
        CefAlumnoCef.objects.filter(
            cueanexo=cef_context["cueanexo"],
            ciclo__anio__lt=cef_context["ciclo"].anio,
        )
        .select_related("alumno", "ciclo")
        .order_by(
            "-ciclo__anio",
            "alumno_nombre_snapshot",
            "-fecha_alta",
            "pk",
        )
    )


def _inscripciones_por_alumno(cef_context, alumnos_banco):
    alumnos_ids = [item.alumno_id for item in alumnos_banco]
    if not alumnos_ids:
        return {}

    inscripciones = (
        CefInscripcion.objects.filter(
            grupo__cueanexo=cef_context["cueanexo"],
            grupo__ciclo=cef_context["ciclo"],
            alumno_id__in=alumnos_ids,
        )
        .select_related("grupo", "grupo__actividad")
        .order_by("grupo__actividad__nombre", "grupo__numero")
    )

    por_alumno = {}
    for inscripcion in inscripciones:
        por_alumno.setdefault(inscripcion.alumno_id, []).append(inscripcion)
    return por_alumno


def _inscripciones_historicas_alumnos(cef_context):
    if not cef_context["puede_consultar"]:
        return CefInscripcion.objects.none()

    return (
        CefInscripcion.objects.filter(
            grupo__cueanexo=cef_context["cueanexo"],
            grupo__ciclo__anio__lte=cef_context["ciclo"].anio,
        )
        .exclude(
            grupo__ciclo=cef_context["ciclo"],
            estado=CefInscripcion.Estado.ACTIVO,
        )
        .select_related("grupo", "grupo__ciclo", "grupo__actividad", "grupo__turno")
        .order_by(
            "alumno_id",
            "-grupo__ciclo__anio",
            "-fecha_inscripcion",
            "-pk",
        )
    )


def _inscripciones_periodos_alumnos(cef_context, alumnos_ids):
    if not alumnos_ids:
        return []

    return list(
        CefInscripcion.objects.filter(
            grupo__cueanexo=cef_context["cueanexo"],
            grupo__ciclo__anio__lte=cef_context["ciclo"].anio,
            alumno_id__in=alumnos_ids,
        )
        .select_related("grupo", "grupo__ciclo", "grupo__actividad", "grupo__turno")
        .order_by(
            "alumno_id",
            "-grupo__ciclo__anio",
            "-fecha_inscripcion",
            "-pk",
        )
    )


def _vincular_inscripciones_a_periodos(periodos, inscripciones):
    periodos_por_ciclo = {}
    for periodo in periodos:
        periodo.inscripciones_grupo = []
        periodos_por_ciclo.setdefault(periodo.ciclo_id, []).append(periodo)

    for inscripcion in inscripciones:
        candidatos_ciclo = periodos_por_ciclo.get(inscripcion.grupo.ciclo_id, [])
        if not candidatos_ciclo:
            continue
        candidatos_fecha = [
            periodo
            for periodo in candidatos_ciclo
            if periodo.fecha_alta <= inscripcion.fecha_inscripcion
            and (
                periodo.fecha_baja is None
                or inscripcion.fecha_inscripcion <= periodo.fecha_baja
            )
        ]
        candidatos_base = candidatos_fecha or candidatos_ciclo
        candidatos_creados = [
            periodo
            for periodo in candidatos_base
            if periodo.creado_en <= inscripcion.creado_en
        ]
        if candidatos_creados:
            periodo_destino = max(
                candidatos_creados,
                key=lambda periodo: (periodo.creado_en, periodo.pk),
            )
        else:
            estado_periodo_preferido = (
                CefAlumnoCef.Estado.ACTIVO
                if inscripcion.estado == CefInscripcion.Estado.ACTIVO
                else CefAlumnoCef.Estado.BAJA
            )
            candidatos_estado = [
                periodo
                for periodo in candidatos_base
                if periodo.estado == estado_periodo_preferido
            ]
            periodo_destino = max(
                candidatos_estado or candidatos_base,
                key=lambda periodo: (periodo.fecha_alta, periodo.pk),
            )
        periodo_destino.inscripciones_grupo.append(inscripcion)


def _grupos_disponibles(cef_context):
    if not cef_context["puede_operar"]:
        return CefGrupo.objects.none()

    return (
        CefGrupo.objects.filter(
            cueanexo=cef_context["cueanexo"],
            ciclo=cef_context["ciclo"],
            estado=CefGrupo.Estado.ACTIVO,
        )
        .select_related("actividad", "rango_etario", "turno")
        .order_by("actividad__nombre", "numero", "nombre")
    )


def _alumnos_listado_context(cef_context, vista="actuales"):
    vista = normalizar_vista_cef(vista)
    alumnos_banco_tabla_pendiente = False
    if vista == "historial":
        try:
            alumnos_bajas_ciclo = list(_alumnos_bajas_ciclo(cef_context))
            alumnos_historial = list(_alumnos_historial(cef_context))
            inscripciones_historicas = list(
                _inscripciones_historicas_alumnos(cef_context)
            )
            alumnos_activos_ciclo = list(
                CefAlumnoCef.objects.filter(
                    cueanexo=cef_context["cueanexo"],
                    ciclo=cef_context["ciclo"],
                    estado=CefAlumnoCef.Estado.ACTIVO,
                ).select_related("alumno", "ciclo")
            )
        except (OperationalError, ProgrammingError):
            alumnos_bajas_ciclo = []
            alumnos_historial = []
            inscripciones_historicas = []
            alumnos_activos_ciclo = []
            alumnos_banco_tabla_pendiente = True
        alumnos_historicos_ids = {
            periodo.alumno_id for periodo in alumnos_historial
        } | {
            inscripcion.alumno_id for inscripcion in inscripciones_historicas
        }
        alumnos_activos_actuales = {
            periodo.alumno_id: periodo for periodo in alumnos_activos_ciclo
        }
        alumnos_ids = (
            alumnos_historicos_ids
            | {periodo.alumno_id for periodo in alumnos_bajas_ciclo}
            | set(alumnos_activos_actuales)
        )
        inscripciones_activas_por_alumno = {}
        inscripciones_periodos_por_alumno = {}
        grupos_disponibles = []
        if alumnos_ids:
            try:
                inscripciones_periodos = _inscripciones_periodos_alumnos(
                    cef_context,
                    alumnos_ids,
                )
            except (OperationalError, ProgrammingError):
                inscripciones_periodos = []
                alumnos_banco_tabla_pendiente = True
            for inscripcion in inscripciones_periodos:
                inscripciones_periodos_por_alumno.setdefault(
                    inscripcion.alumno_id,
                    [],
                ).append(inscripcion)
                if (
                    inscripcion.grupo.ciclo_id == cef_context["ciclo"].pk
                    and inscripcion.estado == CefInscripcion.Estado.ACTIVO
                ):
                    inscripciones_activas_por_alumno.setdefault(
                        inscripcion.alumno_id,
                        [],
                    ).append(inscripcion)
            if cef_context["puede_operar"]:
                grupos_disponibles = list(_grupos_disponibles(cef_context))

        ultimo_periodo_baja_por_alumno = {}
        for periodo in alumnos_bajas_ciclo:
            periodo_actual = ultimo_periodo_baja_por_alumno.get(periodo.alumno_id)
            if periodo_actual is None or periodo.pk > periodo_actual.pk:
                ultimo_periodo_baja_por_alumno[periodo.alumno_id] = periodo
        for periodo in alumnos_bajas_ciclo:
            periodo.puede_reincorporar = (
                cef_context["puede_operar"]
                and periodo.alumno_id not in alumnos_activos_actuales
                and ultimo_periodo_baja_por_alumno.get(periodo.alumno_id) is periodo
            )

        periodos_por_alumno = {}
        for periodo in alumnos_bajas_ciclo + alumnos_historial:
            periodos_por_alumno.setdefault(periodo.alumno_id, []).append(periodo)
        for alumno_id, periodo_activo in alumnos_activos_actuales.items():
            periodos_por_alumno.setdefault(alumno_id, []).append(periodo_activo)

        alumnos_historial_resumen = []
        for alumno_id, periodos in periodos_por_alumno.items():
            periodo_activo = alumnos_activos_actuales.get(alumno_id)
            periodo_resumen = periodo_activo or max(
                periodos,
                key=lambda periodo: (
                    periodo.ciclo.anio,
                    periodo.fecha_alta,
                    periodo.pk,
                ),
            )
            periodos_cronologicos = sorted(
                periodos,
                key=lambda periodo: (
                    periodo.ciclo.anio,
                    periodo.fecha_alta,
                    periodo.pk,
                ),
            )
            for numero_periodo, movimiento in enumerate(
                periodos_cronologicos,
                start=1,
            ):
                movimiento.numero_periodo = numero_periodo
            periodo_resumen.historial_periodos = list(
                reversed(periodos_cronologicos)
            )
            _vincular_inscripciones_a_periodos(
                periodo_resumen.historial_periodos,
                inscripciones_periodos_por_alumno.get(alumno_id, []),
            )
            periodo_resumen.periodo_baja_actual = ultimo_periodo_baja_por_alumno.get(
                alumno_id
            )
            if periodo_activo:
                periodo_resumen.estado_actual_cef = "Activo"
            elif periodo_resumen.periodo_baja_actual:
                periodo_resumen.estado_actual_cef = "Baja"
            else:
                periodo_resumen.estado_actual_cef = "No activo"
            periodo_resumen.periodo_historico_accion = next(
                (
                    periodo
                    for periodo in periodo_resumen.historial_periodos
                    if periodo.ciclo.anio < cef_context["ciclo"].anio
                ),
                None,
            )
            periodo_resumen.activo_banco_actual = periodo_activo is not None
            periodo_resumen.grupos_bloqueados = inscripciones_activas_por_alumno.get(
                alumno_id,
                [],
            )
            grupos_bloqueados_ids = {
                inscripcion.grupo_id
                for inscripcion in periodo_resumen.grupos_bloqueados
            }
            periodo_resumen.grupos_asignables = [
                grupo
                for grupo in grupos_disponibles
                if grupo.pk not in grupos_bloqueados_ids
            ]
            alumnos_historial_resumen.append(periodo_resumen)
        alumnos_historial_resumen.sort(
            key=lambda periodo: (
                periodo.alumno_nombre_snapshot,
                periodo.alumno_documento_snapshot,
                periodo.alumno_id,
            )
        )
        return {
            "vista": vista,
            "alumnos_bajas_ciclo": alumnos_bajas_ciclo,
            "alumnos_historial": alumnos_historial,
            "alumnos_historial_resumen": alumnos_historial_resumen,
            "total_alumnos_historial": len(alumnos_historial_resumen),
            "grupos_disponibles": grupos_disponibles,
            "alumnos_banco_tabla_pendiente": alumnos_banco_tabla_pendiente,
        }

    try:
        alumnos_banco = list(_alumnos_banco(cef_context))
    except (OperationalError, ProgrammingError):
        alumnos_banco = []
        alumnos_banco_tabla_pendiente = True

    try:
        inscripciones_por_alumno = _inscripciones_por_alumno(
            cef_context,
            alumnos_banco,
        )
    except (OperationalError, ProgrammingError):
        inscripciones_por_alumno = {}

    grupos_disponibles = list(_grupos_disponibles(cef_context))
    url_alumnos = _url_alumnos(cef_context)
    for item in alumnos_banco:
        item.inscripciones_grupo = inscripciones_por_alumno.get(
            item.alumno_id,
            [],
        )
        inscripciones_activas = [
            inscripcion
            for inscripcion in item.inscripciones_grupo
            if inscripcion.estado == CefInscripcion.Estado.ACTIVO
        ]
        item.inscripciones_activas = inscripciones_activas
        grupos_activos_ids = {
            inscripcion.grupo_id for inscripcion in inscripciones_activas
        }
        item.grupos_asignables = [
            grupo
            for grupo in grupos_disponibles
            if grupo.pk not in grupos_activos_ids
        ]
        item.grupos_bloqueados = inscripciones_activas
        item.edad = _calcular_edad(
            getattr(item.alumno, "fecha_nacimiento", None)
        )
        item.url_editar_alumno = _url_carga_alumno(
            url_alumnos,
            alumno=item.alumno,
        )

    return {
        "vista": vista,
        "alumnos": alumnos_banco,
        "grupos_disponibles": grupos_disponibles,
        "alumnos_banco_tabla_pendiente": alumnos_banco_tabla_pendiente,
        "baja_form_vacio": CefBajaMotivoForm(),
    }


def _alumno_cef_seguro(alumno_banco_id, cef_context):
    try:
        alumno_banco_id = int(alumno_banco_id)
    except (TypeError, ValueError):
        raise Http404("El alumno seleccionado no es válido.")

    return get_object_or_404(
        CefAlumnoCef.objects.filter(
            cueanexo=cef_context["cueanexo"],
            ciclo=cef_context["ciclo"],
        ).select_related("alumno"),
        pk=alumno_banco_id,
    )


def _preparar_alumno_baja(alumno_banco, cef_context):
    alumno_banco.inscripciones_activas = list(
        CefInscripcion.objects.filter(
            alumno=alumno_banco.alumno,
            grupo__cueanexo=cef_context["cueanexo"],
            grupo__ciclo=cef_context["ciclo"],
            estado=CefInscripcion.Estado.ACTIVO,
        )
        .select_related("grupo", "grupo__actividad", "grupo__turno")
        .order_by("grupo__actividad__nombre", "grupo__numero")
    )
    return alumno_banco


def _alumno_baja_modal(cef_context, alumno_banco_id):
    if not cef_context["puede_operar"] or not alumno_banco_id:
        return None
    return _preparar_alumno_baja(
        _alumno_cef_seguro(alumno_banco_id, cef_context),
        cef_context,
    )


def _reincorporar_alumno_cef(request, cef_context):
    if not cef_context["puede_operar"]:
        return None, "El ciclo está cerrado o no está listo para operar."

    periodo = _alumno_cef_seguro(
        request.POST.get("alumno_banco_id"),
        cef_context,
    )
    if periodo.estado != CefAlumnoCef.Estado.BAJA:
        return None, "El período seleccionado no se encuentra dado de baja."

    try:
        _, creado = asegurar_alumno_banco_activo(
            alumno=periodo.alumno,
            cueanexo=cef_context["cueanexo"],
            ciclo=cef_context["ciclo"],
            user=request.user,
        )
    except ValidationError as exc:
        return None, "; ".join(exc.messages)
    except IntegrityError:
        return (
            None,
            "No se pudo reincorporar al alumno. Verificá que no exista ya un período activo.",
        )

    if creado:
        return True, "Alumno reincorporado al CEF correctamente."
    return False, "El alumno ya se encuentra activo en este CEF y ciclo."


def _dar_baja_alumno_cef(request, cef_context):
    alumno_banco = _preparar_alumno_baja(
        _alumno_cef_seguro(request.POST.get("alumno_banco_id"), cef_context),
        cef_context,
    )
    baja_form = CefBajaMotivoForm(request.POST)
    if alumno_banco.estado != CefAlumnoCef.Estado.ACTIVO:
        return False, "El alumno ya no se encuentra activo en este CEF y ciclo.", alumno_banco, baja_form
    if alumno_banco.inscripciones_activas:
        return (
            False,
            "No se puede dar de baja al alumno del CEF porque posee inscripciones activas.",
            alumno_banco,
            baja_form,
        )
    if not baja_form.is_valid():
        return False, _errores_form(baja_form), alumno_banco, baja_form

    try:
        dar_baja_alumno_banco(
            alumno_banco,
            request.user,
            baja_form.cleaned_data["motivo_baja"],
        )
    except ValidationError as exc:
        alumno_banco = _preparar_alumno_baja(
            _alumno_cef_seguro(alumno_banco.pk, cef_context),
            cef_context,
        )
        return False, "; ".join(exc.messages), alumno_banco, baja_form
    return True, "Alumno dado de baja del CEF correctamente.", alumno_banco, baja_form


def _alumno_en_banco_activo(alumno, cef_context):
    if not alumno or not cef_context["puede_operar"]:
        return False

    return CefAlumnoCef.objects.filter(
        cueanexo=cef_context["cueanexo"],
        ciclo=cef_context["ciclo"],
        alumno=alumno,
        estado=CefAlumnoCef.Estado.ACTIVO,
    ).exists()


@cef_required
def alumnos(request):
    context = contexto_base(request, "alumnos", "Alumnos CEF")
    perf_start_view(request)
    cef_context = context["cef_context"]
    vista = normalizar_vista_cef(
        request.GET.get("vista") or request.POST.get("vista")
    )
    alumno = None
    persona_sge = None
    tipo_doc_buscado = "1"
    nro_doc_buscado = ""
    cuil_buscado = ""
    apellidos_buscados = ""
    nombres_buscados = ""
    fecha_nacimiento_buscada = ""
    sexo_buscado = ""
    cuil_error = ""
    busqueda_sin_identidad = False
    busqueda_sin_documento_realizada = False
    alumno_en_banco = False
    abrir_modal = request.GET.get("abrir_modal_alumno") == "1"
    baja_modal_alumno = None
    baja_form = CefBajaMotivoForm()

    if request.method == "POST":
        accion = request.POST.get("accion")
        if vista == "historial" and accion not in {
            "inscribir_grupo_historial",
            "reincorporar_cef",
        }:
            message = "La acción solicitada no está habilitada en Historial."
            if _is_ajax(request):
                return JsonResponse({"ok": False, "message": message})
            messages.error(request, message)
            return redirect(_url_alumnos(cef_context, "historial"))
        if not cef_context["puede_operar"]:
            message = (
                "El ciclo está cerrado. La información se encuentra en modo sólo lectura."
                if cef_context["ciclo_cerrado"]
                else "Seleccioná un CUE-Anexo y un ciclo lectivo para gestionar alumnos."
            )
            if _is_ajax(request):
                return JsonResponse({"ok": False, "message": message})
            messages.error(request, message)
            return redirect(_url_alumnos(cef_context, vista))
        if accion == "inscribir_grupo_historial":
            if vista != "historial":
                messages.error(request, "La acción histórica solicitada no es válida.")
                return redirect(_url_alumnos(cef_context))
            _inscribir_alumno_grupo_desde_historial(request, cef_context)
            return redirect(_url_alumnos(cef_context, "historial"))
        if request.POST.get("accion") == "baja_cef":
            baja_ok, baja_message, baja_modal_alumno, baja_form = _dar_baja_alumno_cef(
                request,
                cef_context,
            )
            if _is_ajax(request):
                baja_context = {
                    "cef_context": cef_context,
                    "baja_action_url": _url_alumnos(cef_context),
                    "baja_modal_alumno": None if baja_ok else baja_modal_alumno,
                    "baja_form": baja_form,
                }
                baja_context.update(_alumnos_listado_context(cef_context))
                return JsonResponse(
                    {
                        "ok": baja_ok,
                        "message": baja_message,
                        "fragment_selector": "[data-cef-fragment='alumnos-banco']",
                        "fragment_html": render_to_string(
                            "cef/alumnos_lista_cef.html",
                            baja_context,
                            request=request,
                        ),
                        "modal_html": render_to_string(
                            "cef/alumno_baja_cef_modal.html",
                            baja_context,
                            request=request,
                        ),
                        "close_modal": baja_ok,
                    }
                )
            if baja_ok:
                messages.success(request, baja_message)
            else:
                messages.error(request, baja_message)
            return redirect(_url_alumnos(cef_context, vista))

        if accion == "reincorporar_cef":
            reincorporacion_ok, reincorporacion_message = _reincorporar_alumno_cef(
                request,
                cef_context,
            )
            if reincorporacion_ok:
                messages.success(request, reincorporacion_message)
            elif reincorporacion_ok is False:
                messages.info(request, reincorporacion_message)
            else:
                messages.error(request, reincorporacion_message)
            return redirect(_url_alumnos(cef_context, vista))

        if request.POST.get("accion") == "inscribir_grupo":
            _inscribir_alumno_grupo_desde_banco(request, cef_context)
            return redirect(_url_alumnos(cef_context))

        busqueda_form = CefBusquedaAlumnoForm(request.POST)
        abrir_modal = True
        tipo_doc_buscado = request.POST.get("tipo_doc") or "1"
        nro_doc_buscado = (request.POST.get("nro_doc") or "").strip().upper()
        cuil_buscado = _solo_digitos(request.POST.get("cuil"))

        alumno_id_post = request.POST.get("alumno_id")
        if alumno_id_post:
            alumno = _alumno_por_id(alumno_id_post)
            if not alumno:
                cuil_error = "El alumno seleccionado ya no existe o no es válido."
        elif busqueda_form.is_valid():
            tipo_doc = busqueda_form.cleaned_data["tipo_doc_obj"]
            tipo_doc_buscado = str(tipo_doc.pk)
            nro_doc_buscado = busqueda_form.cleaned_data["nro_doc"]
            cuil_buscado = busqueda_form.cleaned_data["cuil"]
            busqueda_sin_identidad = busqueda_form.cleaned_data.get(
                "busqueda_sin_identidad",
                False,
            )
            if busqueda_sin_identidad:
                apellidos_buscados = busqueda_form.cleaned_data["apellidos"]
                nombres_buscados = busqueda_form.cleaned_data["nombres"]
                fecha_nacimiento_buscada = busqueda_form.cleaned_data["fecha_nacimiento"]
                sexo_buscado = busqueda_form.cleaned_data["sexo"]
                try:
                    alumno = _buscar_alumno_sin_documento(
                        apellidos=apellidos_buscados,
                        nombres=nombres_buscados,
                        tipo_doc=tipo_doc,
                        fecha_nacimiento=fecha_nacimiento_buscada,
                        sexo=sexo_buscado,
                    )
                    busqueda_sin_documento_realizada = True
                except ValidationError as exc:
                    cuil_error = "; ".join(exc.messages)
            else:
                try:
                    alumno, persona_sge = _resolver_alumno_o_sge(
                        tipo_doc=tipo_doc,
                        nro_doc=nro_doc_buscado,
                        cuil=cuil_buscado,
                    )
                except ValidationError as exc:
                    cuil_error = "; ".join(exc.messages)
        else:
            cuil_error = _errores_form(busqueda_form)

        if not alumno:
            if busqueda_sin_identidad and not cuil_error:
                messages.info(
                    request,
                    "No se encontró un alumno ya cargado con esos datos.",
                )
            elif persona_sge and not cuil_error:
                messages.info(
                    request,
                    "Alumno encontrado. Complete los datos faltantes antes de incorporarlo a CEF.",
                )
            else:
                messages.error(
                    request,
                    cuil_error or "Primero buscá y seleccioná un alumno existente.",
                )
        elif not cef_context["puede_operar"]:
            messages.error(
                request,
                "Seleccioná un CUE-Anexo y un ciclo lectivo para agregar alumnos al banco.",
            )
        else:
            try:
                try:
                    banco, creado = asegurar_alumno_banco_activo(
                        alumno=alumno,
                        cueanexo=cef_context["cueanexo"],
                        ciclo=cef_context["ciclo"],
                        user=request.user,
                    )
                    tabla_pendiente = False
                except (OperationalError, ProgrammingError):
                    banco = None
                    creado = False
                    tabla_pendiente = True
                alumno_en_banco = bool(banco)

                if tabla_pendiente:
                    messages.error(request, MSG_BANCO_ALUMNOS_PENDIENTE)
                elif creado:
                    messages.success(request, "Alumno agregado al banco de alumnos del CEF.")
                    return redirect(_url_alumnos(cef_context))
                else:
                    messages.info(
                        request,
                        "Ese alumno ya está activo en el banco de alumnos de este CEF y ciclo.",
                    )
            except (IntegrityError, ValidationError):
                messages.error(
                    request,
                    "No se pudo agregar el alumno al banco. Verificá que no exista ya activo para este CEF y ciclo.",
                )
    else:
        busqueda_solicitada = bool(
            request.GET.get("alumno_id")
            or request.GET.get("tipo_doc")
            or request.GET.get("nro_doc")
            or request.GET.get("cuil")
            or request.GET.get("apellidos")
            or request.GET.get("nombres")
            or request.GET.get("fecha_nacimiento")
            or request.GET.get("sexo")
        )
        busqueda_form = CefBusquedaAlumnoForm(
            request.GET if busqueda_solicitada else None
        )
        tipo_doc_buscado = request.GET.get("tipo_doc") or "1"
        nro_doc_buscado = (request.GET.get("nro_doc") or "").strip().upper()
        cuil_buscado = _solo_digitos(request.GET.get("cuil"))
        apellidos_buscados = (request.GET.get("apellidos") or "").strip()
        nombres_buscados = (request.GET.get("nombres") or "").strip()
        fecha_nacimiento_buscada = (request.GET.get("fecha_nacimiento") or "").strip()
        sexo_buscado = (request.GET.get("sexo") or "").strip()

        alumno_id_get = request.GET.get("alumno_id")
        if alumno_id_get:
            alumno = _alumno_por_id(alumno_id_get)
            if not alumno:
                cuil_error = "El alumno seleccionado ya no existe o no es válido."
        elif busqueda_solicitada and busqueda_form.is_valid():
            tipo_doc = busqueda_form.cleaned_data["tipo_doc_obj"]
            tipo_doc_buscado = str(tipo_doc.pk)
            nro_doc_buscado = busqueda_form.cleaned_data["nro_doc"]
            cuil_buscado = busqueda_form.cleaned_data["cuil"]
            busqueda_sin_identidad = busqueda_form.cleaned_data.get(
                "busqueda_sin_identidad",
                False,
            )
            if busqueda_sin_identidad:
                apellidos_buscados = busqueda_form.cleaned_data["apellidos"]
                nombres_buscados = busqueda_form.cleaned_data["nombres"]
                fecha_nacimiento_buscada = busqueda_form.cleaned_data["fecha_nacimiento"]
                sexo_buscado = busqueda_form.cleaned_data["sexo"]
                try:
                    alumno = _buscar_alumno_sin_documento(
                        apellidos=apellidos_buscados,
                        nombres=nombres_buscados,
                        tipo_doc=tipo_doc,
                        fecha_nacimiento=fecha_nacimiento_buscada,
                        sexo=sexo_buscado,
                    )
                    busqueda_sin_documento_realizada = True
                except ValidationError as exc:
                    cuil_error = "; ".join(exc.messages)
            else:
                try:
                    alumno, persona_sge = _resolver_alumno_o_sge(
                        tipo_doc=tipo_doc,
                        nro_doc=nro_doc_buscado,
                        cuil=cuil_buscado,
                    )
                except ValidationError as exc:
                    cuil_error = "; ".join(exc.messages)
        elif busqueda_solicitada:
            cuil_error = _errores_form(busqueda_form)

        if request.GET.get("abrir_modal_baja") == "1":
            baja_modal_alumno = _alumno_baja_modal(
                cef_context,
                request.GET.get("alumno_banco_id"),
            )

    next_url = _url_modal_alumnos(
        cef_context,
        alumno_id=alumno.pk if alumno else "",
        tipo_doc=tipo_doc_buscado,
        nro_doc=nro_doc_buscado,
        cuil=cuil_buscado,
        apellidos=apellidos_buscados,
        nombres=nombres_buscados,
        fecha_nacimiento=fecha_nacimiento_buscada,
        sexo=sexo_buscado,
    )
    url_alumnos = _url_alumnos(cef_context)
    if alumno and not alumno_en_banco:
        try:
            alumno_en_banco = _alumno_en_banco_activo(alumno, cef_context)
        except (OperationalError, ProgrammingError):
            alumno_en_banco = False

    context.update(
        {
            "busqueda_form": busqueda_form,
            "alumno": alumno,
            "alumno_row": _alumno_row(alumno) or _persona_sge_row(persona_sge),
            "alumno_desde_sge": bool(persona_sge and not alumno),
            "alumno_en_banco": alumno_en_banco,
            "tipo_doc_buscado": tipo_doc_buscado,
            "nro_doc_buscado": nro_doc_buscado,
            "cuil_buscado": cuil_buscado,
            "apellidos_buscados": apellidos_buscados,
            "nombres_buscados": nombres_buscados,
            "fecha_nacimiento_buscada": fecha_nacimiento_buscada,
            "sexo_buscado": sexo_buscado,
            "cuil_error": cuil_error,
            "busqueda_sin_identidad": busqueda_sin_identidad,
            "busqueda_sin_documento_realizada": busqueda_sin_documento_realizada,
            "url_carga_alumno": _url_carga_alumno(
                next_url,
                tipo_doc=tipo_doc_buscado,
                nro_doc=nro_doc_buscado,
                cuil=cuil_buscado,
                apellidos=apellidos_buscados,
                nombres=nombres_buscados,
                fecha_nacimiento=fecha_nacimiento_buscada,
                sexo=sexo_buscado,
            ),
            "url_editar_alumno": (
                _url_carga_alumno(next_url, alumno=alumno)
                if alumno
                else ""
            ),
            "modal_alumno_abierto": abrir_modal,
            "modal_action_url": _url_modal_alumnos(cef_context),
            "modal_tiene_grupo": False,
            "modal_puede_agregar_banco": cef_context["puede_operar"],
            "modal_volver_url": url_alumnos,
            "baja_action_url": url_alumnos,
            "baja_modal_alumno": baja_modal_alumno,
            "baja_form": baja_form,
        }
    )
    context.update(_alumnos_listado_context(cef_context, vista))
    return perf_render(request, "cef/alumnos_cef.html", context)


@cef_required
@require_GET
def alumnos_fragmento(request):
    cef_context = resolver_contexto_operativo(request)
    vista = normalizar_vista_cef(request.GET.get("vista"))
    context = {
        "cef_context": cef_context,
        "cef_partial": True,
        "modal_action_url": _url_modal_alumnos(cef_context),
        "baja_action_url": _url_alumnos(cef_context),
        "baja_modal_alumno": (
            _alumno_baja_modal(
                cef_context,
                request.GET.get("alumno_banco_id"),
            )
            if vista == "actuales" and request.GET.get("abrir_modal_baja") == "1"
            else None
        ),
        "baja_form": CefBajaMotivoForm(),
    }
    context.update(_alumnos_listado_context(cef_context, vista))
    return render_fragmento_cef(request, "cef/alumnos_seccion_cef.html", context)