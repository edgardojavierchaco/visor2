# apps/especial/views_inscripcion_seccion.py
# -*- coding: utf-8 -*-

import logging
import re
from urllib.parse import urlencode

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db import DatabaseError, IntegrityError, transaction
from django.db.utils import OperationalError, ProgrammingError
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

from .forms import EspecialBusquedaAlumnoForm, EspecialInscripcionForm
from .models import (
    AlumnoSeccion,
    EspecialAlumnoBanco,
    SeccionEspecial,
    normalizar_cueanexo,
)
from .permisos import (
    cueanexo_autorizado_especial,
    especial_required,
    get_permisos_especial_request,
)
from .services.alumnos import (
    bloquear_alumno_banco_activo,
    dar_baja_inscripcion_y_matricula_compartida,
    inscribir_alumno_en_seccion,
    ultima_matricula_compartida,
)
from .services.alumnos_identidad import (
    _alumno_por_id,
    _buscar_alumno_sin_documento,
    _persona_sge_row,
    _resolver_alumno_o_sge,
    _url_carga_alumno as _url_carga_alumno_base,
)
from .views_contexto import contexto_base, redirect_con_contexto


logger = logging.getLogger(__name__)


ESTADOS_INSCRIPCION_ABIERTA = [
    AlumnoSeccion.Estado.ACTIVO,
]


def _solo_digitos(valor):
    return re.sub(r"\D", "", str(valor or ""))



def _seccion_segura(seccion_id, especial_context, for_update=False):
    """Obtiene una sección validando permisos."""
    queryset = SeccionEspecial.objects.filter(
            cueanexo=especial_context["cueanexo"],
            ciclo=especial_context["ciclo"],
        )
    if for_update:
        queryset = queryset.select_for_update()
    return get_object_or_404(
        queryset
        .select_related(
            "cd_tipo_seccion",
            "turno",
            "rango_etario",
            "modalidad",
            "tipo_estructura_especial",
        ),
        pk=seccion_id,
    )


def _completar_contexto_desde_seccion(request, seccion_id, especial_context):
    """Hace que la sección persistida sea la fuente del CUE y ciclo."""
    seccion = (
        SeccionEspecial.objects
        .filter(pk=seccion_id)
        .select_related("ciclo")
        .first()
    )
    if not seccion:
        return

    permisos = get_permisos_especial_request(request)
    if not cueanexo_autorizado_especial(
        permisos,
        seccion.cueanexo,
        "cargables",
    ):
        return

    especial_context["cueanexo"] = seccion.cueanexo
    especial_context["ciclo"] = seccion.ciclo
    especial_context["querystring"] = (
        f"cueanexo={seccion.cueanexo}&ciclo={especial_context['ciclo'].pk}"
    )
    especial_context["puede_consultar"] = True
    especial_context["ciclo_cerrado"] = bool(seccion.ciclo.cerrado)
    especial_context["seccion_inactiva"] = (
        seccion.estado != SeccionEspecial.Estado.ACTIVO
    )
    especial_context["puede_operar"] = (
        not especial_context["ciclo_cerrado"]
        and not especial_context["seccion_inactiva"]
    )
    especial_context["sin_cueanexo"] = False


def _inscripciones_seccion(seccion):
    """Devuelve una única inscripción visible por alumno.

    Las bajas anteriores se conservan para el historial, pero no deben
    aparecer junto con una reinscripción activa en la pantalla operativa.
    """
    candidatas = (
        AlumnoSeccion.objects.filter(seccion=seccion)
        .select_related("alumno", "alumno__sexo")
        .order_by("alumno_id", "-pk")
    )
    visibles = {}
    for inscripcion in candidatas:
        anterior = visibles.get(inscripcion.alumno_id)
        if anterior is None or (
            inscripcion.estado == AlumnoSeccion.Estado.ACTIVO
            and anterior.estado != AlumnoSeccion.Estado.ACTIVO
        ):
            visibles[inscripcion.alumno_id] = inscripcion
    return sorted(
        visibles.values(),
        key=lambda inscripcion: (
            inscripcion.alumno.apellidos or "",
            inscripcion.alumno.nombres or "",
        ),
    )



def crear_inscripcion_activa(
    *,
    seccion,
    alumno,
    user,
    seccion_queryset,
    alumno_banco_queryset,
):
    """Crea o reactiva una inscripción validando contexto, banco y cupo."""
    with transaction.atomic():
        banco_activo = bloquear_alumno_banco_activo(
            alumno=alumno,
            cueanexo=seccion.cueanexo,
            ciclo=seccion.ciclo,
            alumno_banco_queryset=alumno_banco_queryset,
        )
        seccion_bloqueada = get_object_or_404(
            seccion_queryset.select_for_update(),
            pk=seccion.pk,
        )
        if seccion_bloqueada.estado != SeccionEspecial.Estado.ACTIVO:
            raise ValidationError("La sección no está activa.")

        inscripcion_activa = (
            AlumnoSeccion.objects.select_for_update()
            .filter(
                seccion=seccion_bloqueada,
                alumno=alumno,
                estado=AlumnoSeccion.Estado.ACTIVO,
            )
            .first()
        )
        if inscripcion_activa:
            raise ValidationError("El alumno ya está inscripto en esta sección.")

        inscripcion_baja = (
            AlumnoSeccion.objects.select_for_update()
            .filter(
                seccion=seccion_bloqueada,
                alumno=alumno,
                estado=AlumnoSeccion.Estado.BAJA,
            )
            .order_by("-pk")
            .first()
        )
        if inscripcion_baja:
            inscripcion_nueva = _reactivar_inscripcion_bloqueada(
                inscripcion_baja, user, seccion_bloqueada, banco_activo
            )
            return inscripcion_nueva, False

        total_activos = AlumnoSeccion.objects.filter(
            seccion=seccion_bloqueada,
            estado=AlumnoSeccion.Estado.ACTIVO,
        ).count()
        if total_activos >= seccion_bloqueada.capacidad_total:
            raise ValidationError(
                "No se puede inscribir: la sección alcanzó su capacidad máxima."
            )

        return (
            AlumnoSeccion.objects.create(
                seccion=seccion_bloqueada,
                alumno=alumno,
                alumno_banco=banco_activo,
                estado=AlumnoSeccion.Estado.ACTIVO,
                tipo_inclusion=(
                    AlumnoSeccion.TipoInclusion.INCLUSION_PLENA
                    if seccion_bloqueada.es_oferta_integracion else None
                ),
                creado_por=user,
                actualizado_por=user,
            ),
            True,
        )


def _reactivar_inscripcion_bloqueada(
    inscripcion_bloqueada,
    user,
    seccion,
    banco_activo,
    *,
    fecha_inscripcion=None,
    observaciones=None,
):
    duplicado = AlumnoSeccion.objects.filter(
        seccion=seccion,
        alumno_id=inscripcion_bloqueada.alumno_id,
        estado=AlumnoSeccion.Estado.ACTIVO,
    ).exclude(pk=inscripcion_bloqueada.pk).exists()
    if duplicado:
        raise ValidationError(
            "El alumno ya tiene otra inscripción activa en esta sección."
        )

    total_activos = AlumnoSeccion.objects.filter(
        seccion=seccion,
        estado=AlumnoSeccion.Estado.ACTIVO,
    ).count()
    if total_activos >= seccion.capacidad_total:
        raise ValidationError(
            "No se puede reinscribir: la sección alcanzó su capacidad máxima."
        )

    return AlumnoSeccion.objects.create(
        seccion=seccion,
        alumno_id=inscripcion_bloqueada.alumno_id,
        alumno_banco=banco_activo,
        estado=AlumnoSeccion.Estado.ACTIVO,
        tipo_inclusion=(
            AlumnoSeccion.TipoInclusion.INCLUSION_PLENA
            if seccion.es_oferta_integracion else None
        ),
        fecha_inscripcion=fecha_inscripcion or timezone.localdate(),
        observaciones=(
            inscripcion_bloqueada.observaciones
            if observaciones is None
            else observaciones
        ),
        creado_por=user,
        actualizado_por=user,
    )


def dar_alta_inscripcion_seccion(
    inscripcion,
    user,
    *,
    seccion_queryset,
    alumno_banco_queryset,
):
    """Reactiva una inscripción bajo el orden de locks del dominio."""
    with transaction.atomic():
        seccion_sin_bloqueo = get_object_or_404(
            seccion_queryset,
            pk=inscripcion.seccion_id,
        )
        if seccion_sin_bloqueo.es_oferta_integracion:
            raise ValidationError(
                "Para reinscribir en una sección de Integración debe usar "
                "Agregar alumno y validar nuevamente la matrícula compartida."
            )
        banco_activo = bloquear_alumno_banco_activo(
            alumno=inscripcion.alumno_id,
            cueanexo=seccion_sin_bloqueo.cueanexo,
            ciclo=seccion_sin_bloqueo.ciclo_id,
            alumno_banco_queryset=alumno_banco_queryset,
        )
        seccion = get_object_or_404(
            seccion_queryset.select_for_update(),
            pk=inscripcion.seccion_id,
        )
        inscripcion_bloqueada = get_object_or_404(
            AlumnoSeccion.objects.select_for_update().select_related("alumno"),
            pk=inscripcion.pk,
            seccion=seccion,
        )
        if inscripcion_bloqueada.estado == AlumnoSeccion.Estado.ACTIVO:
            raise ValidationError("La inscripción ya está activa.")
        _reactivar_inscripcion_bloqueada(
            inscripcion_bloqueada,
            user,
            seccion,
            banco_activo,
            fecha_inscripcion=inscripcion.fecha_inscripcion,
            observaciones=inscripcion.observaciones,
        )


def dar_baja_inscripcion_seccion(inscripcion, user, *, motivo_baja="Baja desde gestión"):
    """
    Marca una inscripción de alumno como baja y registra la fecha de baja.
    Lanza ValidationError si la inscripción ya está en baja.
    """
    return dar_baja_inscripcion_y_matricula_compartida(
        inscripcion,
        user,
        motivo_baja=motivo_baja,
    )


def _texto(valor):
    if valor is None:
        return ""
    return str(valor)


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



def _url_modal_seccion(
    seccion,
    especial_context,
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
    if especial_context.get("cueanexo"):
        params["cueanexo"] = especial_context["cueanexo"]
    if especial_context.get("ciclo"):
        params["ciclo"] = especial_context["ciclo"].pk
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
    return f"{reverse('especial:inscripcion_seccion', kwargs={'seccion_id': seccion.pk})}?{urlencode(params)}"


def _url_inscripcion_seccion(seccion, especial_context):
    params = {}
    if especial_context.get("cueanexo"):
        params["cueanexo"] = especial_context["cueanexo"]
    if especial_context.get("ciclo"):
        params["ciclo"] = especial_context["ciclo"].pk
    querystring = urlencode(params)
    url = reverse("especial:inscripcion_seccion", kwargs={"seccion_id": seccion.pk})
    return f"{url}?{querystring}" if querystring else url


def _url_gestionar_seccion(seccion, especial_context):
    params = {}
    if especial_context.get("cueanexo"):
        params["cueanexo"] = especial_context["cueanexo"]
    if especial_context.get("ciclo"):
        params["ciclo"] = especial_context["ciclo"].pk
    querystring = urlencode(params)
    url = reverse("especial:gestionar_seccion", kwargs={"seccion_id": seccion.pk})
    return f"{url}?{querystring}" if querystring else url


def _errores_form(form):
    return " ".join(error for errors in form.errors.values() for error in errors)


@especial_required
def inscripcion_seccion(request, seccion_id):
    """Vista de inscripción de alumnos a una sección."""
    context = contexto_base(request, "secciones", "Inscripción de alumnos Educación Especial")
    especial_context = context["especial_context"]
    _completar_contexto_desde_seccion(request, seccion_id, especial_context)
    if request.method == "POST" and especial_context.get("ciclo_cerrado"):
        messages.error(request, "El ciclo seleccionado está cerrado y sólo puede consultarse.")
        return redirect(request.get_full_path())

    if not especial_context["puede_consultar"]:
        messages.warning(
            request,
            "Seleccioná un CUE-Anexo y un ciclo lectivo para administrar inscripciones.",
        )
        return redirect(redirect_con_contexto("especial:carga_seccion", especial_context))

    seccion = _seccion_segura(seccion_id, especial_context)
    alumno = None
    persona_sge = None
    inscripcion_abierta = None
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
    matricula_compartida_cueanexo = ""
    modal_feedback = ""
    modal_feedback_level = "error"
    abrir_modal = request.GET.get("abrir_modal_alumno") == "1"

    def procesar_busqueda(form, datos):
        nonlocal alumno, persona_sge, cuil_error
        nonlocal tipo_doc_buscado, nro_doc_buscado, cuil_buscado
        nonlocal apellidos_buscados, nombres_buscados
        nonlocal fecha_nacimiento_buscada, sexo_buscado
        nonlocal busqueda_sin_identidad, busqueda_sin_documento_realizada
        tipo_doc_buscado = datos.get("tipo_doc") or "1"
        nro_doc_buscado = (datos.get("nro_doc") or "").strip().upper()
        cuil_buscado = _solo_digitos(datos.get("cuil"))
        apellidos_buscados = (datos.get("apellidos") or "").strip()
        nombres_buscados = (datos.get("nombres") or "").strip()
        fecha_nacimiento_buscada = (datos.get("fecha_nacimiento") or "").strip()
        sexo_buscado = (datos.get("sexo") or "").strip()
        if not form.is_valid():
            cuil_error = _errores_form(form)
            return
        tipo_doc = form.cleaned_data["tipo_doc_obj"]
        tipo_doc_buscado = str(tipo_doc.pk)
        nro_doc_buscado = form.cleaned_data["nro_doc"]
        cuil_buscado = form.cleaned_data["cuil"]
        if form.cleaned_data.get("busqueda_sin_identidad"):
            busqueda_sin_identidad = True
            apellidos_buscados = form.cleaned_data["apellidos"]
            nombres_buscados = form.cleaned_data["nombres"]
            fecha_nacimiento_buscada = form.cleaned_data["fecha_nacimiento"]
            sexo_obj = form.cleaned_data["sexo"]
            sexo_buscado = str(sexo_obj.pk)
            try:
                alumno = _buscar_alumno_sin_documento(
                    apellidos=apellidos_buscados,
                    nombres=nombres_buscados,
                    tipo_doc=tipo_doc,
                    fecha_nacimiento=fecha_nacimiento_buscada,
                    sexo=sexo_obj,
                )
                busqueda_sin_documento_realizada = True
            except ValidationError as exc:
                cuil_error = "; ".join(exc.messages)
            return
        try:
            alumno, persona_sge = _resolver_alumno_o_sge(
                tipo_doc=tipo_doc,
                nro_doc=nro_doc_buscado,
                cuil=cuil_buscado,
            )
        except ValidationError as exc:
            cuil_error = "; ".join(exc.messages)

    if request.method == "POST":
        busqueda_form = EspecialBusquedaAlumnoForm(request.POST)
        abrir_modal = True
        alumno_id_post = request.POST.get("alumno_id")
        cueanexo_asociado_recibido = str(
            request.POST.get("cueanexo_matricula_compartida") or ""
        ).strip()
        matricula_compartida_cueanexo = (
            normalizar_cueanexo(cueanexo_asociado_recibido)
            or cueanexo_asociado_recibido
        )
        if alumno_id_post:
            alumno = _alumno_por_id(alumno_id_post)
            if not alumno:
                cuil_error = "El alumno seleccionado ya no existe o no es válido."
        else:
            procesar_busqueda(busqueda_form, request.POST)

        if not alumno:
            if persona_sge and not cuil_error:
                modal_feedback = (
                    "Alumno encontrado en SGE. Complete los datos faltantes antes de inscribirlo."
                )
                messages.info(request, modal_feedback)
            elif busqueda_sin_identidad and not cuil_error:
                modal_feedback = "No se encontró un alumno ya cargado con esos datos."
                messages.info(request, modal_feedback)
            else:
                modal_feedback = cuil_error or "Primero buscá y seleccioná un alumno existente."
                messages.error(request, modal_feedback)
        else:
            cuil_buscado = getattr(alumno, "cuil", "") or cuil_buscado
            logger.info(
                "Inscripción Especial recibida: seccion_id=%s cue_especial=%s ciclo_id=%s "
                "alumno_id=%s cuil=%s cue_asociado=%s",
                seccion.pk,
                seccion.cueanexo,
                seccion.ciclo_id,
                alumno.pk,
                cuil_buscado,
                matricula_compartida_cueanexo,
            )
            inscripcion_abierta = AlumnoSeccion.objects.filter(
                seccion=seccion,
                alumno=alumno,
                estado__in=ESTADOS_INSCRIPCION_ABIERTA,
            ).first()
            if inscripcion_abierta:
                modal_feedback = "El alumno ya se encuentra inscripto en esta sección."
                messages.error(request, modal_feedback)
            else:
                try:
                    _, creada, _ = inscribir_alumno_en_seccion(
                        seccion=seccion,
                        alumno=alumno,
                        user=request.user,
                        cueanexo_asociado=cueanexo_asociado_recibido,
                    )
                    messages.success(
                        request,
                        "Alumno inscripto correctamente."
                        if creada
                        else "La inscripción del alumno fue reactivada correctamente.",
                    )
                    return redirect(
                        redirect_con_contexto(
                            "especial:inscripcion_seccion",
                            especial_context,
                            seccion_id=seccion.pk,
                        )
                    )
                except ValidationError as exc:
                    modal_feedback = "; ".join(exc.messages)
                    logger.warning(
                        "Inscripción Especial rechazada: seccion_id=%s alumno_id=%s "
                        "cue_asociado=%s motivo=%s",
                        seccion.pk,
                        alumno.pk,
                        matricula_compartida_cueanexo,
                        modal_feedback,
                    )
                    messages.error(request, modal_feedback)
                except IntegrityError:
                    modal_feedback = (
                        "No se pudo crear la inscripción. Verificá que no exista "
                        "una inscripción activa."
                    )
                    logger.exception(
                        "Inscripción Especial rechazada por integridad: seccion_id=%s alumno_id=%s",
                        seccion.pk,
                        alumno.pk,
                    )
                    messages.error(request, modal_feedback)
                except (OperationalError, ProgrammingError):
                    modal_feedback = (
                        "No se pudo consultar el padrón o la base de datos. Intentá nuevamente."
                    )
                    logger.exception("Error de base al inscribir alumno Especial.")
                    messages.error(request, modal_feedback)
                except DatabaseError:
                    modal_feedback = "No se pudo completar la inscripción por un error de base de datos."
                    logger.exception("Error de base no clasificado al inscribir alumno Especial.")
                    messages.error(request, modal_feedback)
                except Exception:
                    modal_feedback = "No se pudo completar la inscripción. Revisá los datos e intentá nuevamente."
                    logger.exception("Error no controlado al inscribir alumno Especial.")
                    messages.error(request, modal_feedback)
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
        busqueda_form = EspecialBusquedaAlumnoForm(
            request.GET if busqueda_solicitada else None
        )
        if request.GET.get("alumno_id"):
            alumno = _alumno_por_id(request.GET.get("alumno_id"))
            if not alumno:
                cuil_error = "El alumno seleccionado ya no existe o no es válido."
        elif busqueda_solicitada:
            procesar_busqueda(busqueda_form, request.GET)
        if alumno:
            inscripcion_abierta = AlumnoSeccion.objects.filter(
                seccion=seccion,
                alumno=alumno,
                estado__in=ESTADOS_INSCRIPCION_ABIERTA,
            ).first()

    next_url = _url_modal_seccion(
        seccion,
        especial_context,
        alumno_id=alumno.pk if alumno else "",
        tipo_doc=tipo_doc_buscado,
        nro_doc=nro_doc_buscado,
        cuil=cuil_buscado,
        apellidos=apellidos_buscados,
        nombres=nombres_buscados,
        fecha_nacimiento=fecha_nacimiento_buscada,
        sexo=sexo_buscado,
    )
    alumno_en_banco = bool(
        alumno
        and EspecialAlumnoBanco.objects.filter(
            alumno=alumno,
            cueanexo=seccion.cueanexo,
            ciclo=seccion.ciclo,
            estado=EspecialAlumnoBanco.Estado.ACTIVO,
        ).exists()
    )
    ultima_matricula = (
        ultima_matricula_compartida(
            alumno,
            excluir_cueanexo=seccion.cueanexo,
        )
        if alumno and seccion.es_oferta_integracion
        else None
    )
    inscripciones = list(_inscripciones_seccion(seccion))
    bancos_por_alumno = {
        banco.alumno_id: banco
        for banco in EspecialAlumnoBanco.objects.filter(
            cueanexo=seccion.cueanexo,
            ciclo=seccion.ciclo,
            alumno_id__in=[item.alumno_id for item in inscripciones],
            estado=EspecialAlumnoBanco.Estado.ACTIVO,
        )
    } if inscripciones else {}
    for item in inscripciones:
        banco = bancos_por_alumno.get(item.alumno_id)
        item.cueanexo_matricula_compartida = banco.matricula_compartida if banco else ""
        item.reinscripcion_url = _url_modal_seccion(
            seccion,
            especial_context,
            alumno_id=item.alumno_id,
        )
    context.update(
        {
            "seccion": seccion,
            "inscripciones": inscripciones,
            "inscripciones_activas": [
                item for item in inscripciones
                if item.estado == AlumnoSeccion.Estado.ACTIVO
            ],
            "busqueda_form": busqueda_form,
            "alumno": alumno,
            "alumno_row": _alumno_row(alumno) or _persona_sge_row(persona_sge),
            "alumno_desde_sge": bool(persona_sge and not alumno),
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
            "matricula_compartida_cueanexo": matricula_compartida_cueanexo,
            "inscripcion_abierta": inscripcion_abierta,
            "alumno_en_banco": alumno_en_banco,
            "alumno_en_seccion": bool(inscripcion_abierta),
            "seccion_es_oferta_integracion": seccion.es_oferta_integracion,
            "matricula_compartida_habilitada": seccion.es_oferta_integracion,
            "matricula_compartida_busqueda_url": (
                f"{reverse('especial:buscar_cueanexos_matricula_compartida')}"
                f"?seccion_id={seccion.pk}"
            ),
            "ultima_matricula_compartida": ultima_matricula,
            "mostrar_cueanexo_matricula": seccion.es_oferta_integracion,
            "gestionar_seccion_modo": True,
            "gestionar_seccion_url": _url_gestionar_seccion(seccion, especial_context),
            "url_carga_alumno": _url_carga_alumno_base(
                next_url,
                return_label="Volver a la sección",
                tipo_doc=tipo_doc_buscado,
                nro_doc=nro_doc_buscado,
                cuil=cuil_buscado,
                apellidos=apellidos_buscados,
                nombres=nombres_buscados,
                fecha_nacimiento=fecha_nacimiento_buscada,
                sexo=sexo_buscado,
            ),
            "url_editar_alumno": (
                _url_carga_alumno_base(
                    next_url,
                    return_label="Volver a la sección",
                    alumno=alumno,
                )
                if alumno
                else ""
            ),
            "modal_alumno_abierto": abrir_modal,
            "modal_action_url": _url_modal_seccion(seccion, especial_context),
            "modal_tiene_seccion": True,
            "modal_volver_url": _url_inscripcion_seccion(seccion, especial_context),
            "modal_feedback": modal_feedback,
            "modal_feedback_level": modal_feedback_level,
        }
    )
    return render(request, "especial/inscripcion_seccion_especial.html", context)


@especial_required
def editar_inscripcion_seccion(request, seccion_id, inscripcion_id):
    """Vista para editar una inscripción de alumno a sección."""
    context = contexto_base(request, "secciones", "Editar inscripción Educación Especial")
    especial_context = context["especial_context"]
    _completar_contexto_desde_seccion(request, seccion_id, especial_context)
    if request.method == "POST" and especial_context.get("ciclo_cerrado"):
        messages.error(
            request,
            "El ciclo seleccionado está cerrado y sólo puede consultarse.",
        )
        return redirect(request.get_full_path())

    if not especial_context["puede_operar"]:
        messages.warning(
            request,
            "Seleccioná un CUE-Anexo y un ciclo lectivo para administrar inscripciones.",
        )
        return redirect(redirect_con_contexto("especial:carga_seccion", especial_context))

    seccion = _seccion_segura(seccion_id, especial_context)
    volver_gestionar = (
        request.GET.get("volver") == "gestionar"
        or request.POST.get("volver") == "gestionar"
    )
    volver_url = (
        _url_gestionar_seccion(seccion, especial_context)
        if volver_gestionar
        else _url_inscripcion_seccion(seccion, especial_context)
    )
    inscripcion = get_object_or_404(
        AlumnoSeccion.objects.filter(
            seccion=seccion,
            seccion__cueanexo=especial_context["cueanexo"],
            seccion__ciclo=especial_context["ciclo"],
        ).select_related("alumno", "alumno__sexo"),
        pk=inscripcion_id,
    )

    if request.method == "POST":
        estado_anterior = inscripcion.estado
        form = EspecialInscripcionForm(request.POST, instance=inscripcion)
        if form.is_valid():
            inscripcion = form.save(commit=False)
            try:
                if (
                    estado_anterior != AlumnoSeccion.Estado.ACTIVO
                    and inscripcion.estado == AlumnoSeccion.Estado.ACTIVO
                ):
                    dar_alta_inscripcion_seccion(
                        inscripcion,
                        request.user,
                        seccion_queryset=SeccionEspecial.objects.filter(
                            cueanexo=especial_context["cueanexo"],
                            ciclo=especial_context["ciclo"],
                        ),
                        alumno_banco_queryset=EspecialAlumnoBanco.objects.filter(
                            cueanexo=especial_context["cueanexo"],
                            ciclo=especial_context["ciclo"],
                        ),
                    )
                elif (
                    estado_anterior == AlumnoSeccion.Estado.ACTIVO
                    and inscripcion.estado == AlumnoSeccion.Estado.BAJA
                ):
                    dar_baja_inscripcion_seccion(
                        inscripcion,
                        request.user,
                        motivo_baja=inscripcion.motivo_baja,
                    )
                else:
                    inscripcion.actualizado_por = request.user
                    inscripcion.save()
            except IntegrityError:
                messages.error(
                    request,
                    "No se pudo actualizar la inscripción por un conflicto de integridad.",
                )
            except ValidationError as exc:
                messages.error(request, "; ".join(exc.messages))
            else:
                messages.success(request, "Inscripción actualizada correctamente.")
                return redirect(volver_url)

        messages.error(request, "Revisá los datos de la inscripción.")
    else:
        form = EspecialInscripcionForm(instance=inscripcion)

    context.update(
        {
            "seccion": seccion,
            "inscripcion": inscripcion,
            "form": form,
            "volver_url": volver_url,
            "volver_gestionar": volver_gestionar,
        }
    )
    return render(request, "especial/inscripcion_seccion_form_especial.html", context)
