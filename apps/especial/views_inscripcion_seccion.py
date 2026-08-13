# apps/especial/views_inscripcion_seccion.py
# -*- coding: utf-8 -*-

import re
from urllib.parse import urlencode

from django.apps import apps
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import NoReverseMatch, reverse

from .forms import EspecialBusquedaAlumnoForm, EspecialInscripcionForm
from .models import EspecialAlumnoBanco, SeccionEspecial, AlumnoSeccion
from .permisos import especial_required
from .services.alumnos import bloquear_alumno_banco_activo
from .views_contexto import contexto_base, redirect_con_contexto


ESTADOS_INSCRIPCION_ABIERTA = [
    AlumnoSeccion.Estado.ACTIVO,
]


def _solo_digitos(valor):
    return re.sub(r"\D", "", str(valor or ""))


def _alumno_model():
    return apps.get_model("bnhalumnos", "Alumno")


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


def _inscripciones_seccion(seccion):
    """QuerySet de inscripciones de una sección."""
    return (
        AlumnoSeccion.objects.filter(seccion=seccion)
        .select_related("alumno", "alumno__sexo")
        .order_by("alumno__apellidos", "alumno__nombres")
    )


def _buscar_alumno(cuil):
    return _alumno_model().objects.filter(cuil=cuil).first()


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
        bloquear_alumno_banco_activo(
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
            _reactivar_inscripcion_bloqueada(inscripcion_baja, user, seccion_bloqueada)
            return inscripcion_baja, False

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
                estado=AlumnoSeccion.Estado.ACTIVO,
                creado_por=user,
                actualizado_por=user,
            ),
            True,
        )


def _reactivar_inscripcion_bloqueada(inscripcion_bloqueada, user, seccion):
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

    inscripcion_bloqueada.estado = AlumnoSeccion.Estado.ACTIVO
    inscripcion_bloqueada.fecha_baja = None
    inscripcion_bloqueada.motivo_baja = ""
    inscripcion_bloqueada.actualizado_por = user
    inscripcion_bloqueada.save(
        update_fields=[
            "estado",
            "fecha_baja",
            "motivo_baja",
            "actualizado_por",
            "actualizado_en",
        ]
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
        bloquear_alumno_banco_activo(
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
        inscripcion_bloqueada.fecha_inscripcion = inscripcion.fecha_inscripcion
        inscripcion_bloqueada.observaciones = inscripcion.observaciones
        _reactivar_inscripcion_bloqueada(inscripcion_bloqueada, user, seccion)


def dar_baja_inscripcion_seccion(inscripcion, user):
    """
    Marca una inscripción de alumno como baja y registra la fecha de baja.
    Lanza ValidationError si la inscripción ya está en baja.
    """
    if inscripcion.estado == AlumnoSeccion.Estado.BAJA:
        raise ValidationError("La inscripción ya está dada de baja.")

    from django.utils import timezone
    with transaction.atomic():
        inscripcion.estado = AlumnoSeccion.Estado.BAJA
        inscripcion.fecha_baja = timezone.localdate()
        inscripcion.motivo_baja = "Baja desde gestión"
        inscripcion.actualizado_por = user
        inscripcion.save(update_fields=["estado", "fecha_baja", "motivo_baja", "actualizado_por", "actualizado_en"])


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


def _url_carga_alumno(cuil, next_url, return_label="Volver a la sección"):
    try:
        base = reverse("bnhalumnos:carga_alumno")
    except NoReverseMatch:
        return ""

    params = {}
    if cuil:
        params["cuil"] = cuil
    if next_url:
        params["next"] = next_url
    if return_label:
        params["return_label"] = return_label
    return f"{base}?{urlencode(params)}" if params else base


def _url_modal_seccion(seccion, especial_context, cuil=""):
    params = {}
    if especial_context.get("cueanexo"):
        params["cueanexo"] = especial_context["cueanexo"]
    if especial_context.get("ciclo"):
        params["ciclo"] = especial_context["ciclo"].pk
    params["abrir_modal_alumno"] = "1"
    if cuil:
        params["cuil"] = cuil
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
    if request.method == "POST" and especial_context.get("ciclo_cerrado"):
        messages.error(
            request,
            "El ciclo seleccionado está cerrado y sólo puede consultarse.",
        )
        return redirect(request.get_full_path())

    if not especial_context["puede_consultar"]:
        messages.warning(
            request,
            "Seleccioná un CUE-Anexo y un ciclo lectivo para administrar inscripciones.",
        )
        return redirect(redirect_con_contexto("especial:carga_seccion", especial_context))

    seccion = _seccion_segura(seccion_id, especial_context)
    alumno = None
    inscripcion_abierta = None
    cuil_buscado = ""
    cuil_error = ""
    abrir_modal = request.GET.get("abrir_modal_alumno") == "1"

    if request.method == "POST":
        busqueda_form = EspecialBusquedaAlumnoForm(request.POST)
        abrir_modal = True

        if busqueda_form.is_valid():
            cuil_buscado = busqueda_form.cleaned_data["cuil"]
            alumno = _buscar_alumno(cuil_buscado)
        else:
            cuil_buscado = _solo_digitos(request.POST.get("cuil"))
            cuil_error = _errores_form(busqueda_form)

        if not alumno:
            messages.error(request, "Primero buscá un alumno existente por CUIL.")
        else:
            inscripcion_abierta = AlumnoSeccion.objects.filter(
                seccion=seccion,
                alumno=alumno,
                estado__in=ESTADOS_INSCRIPCION_ABIERTA,
            ).first()

            if not inscripcion_abierta:
                try:
                    _, creada = crear_inscripcion_activa(
                        seccion=seccion,
                        alumno=alumno,
                        user=request.user,
                        seccion_queryset=SeccionEspecial.objects.filter(
                            cueanexo=especial_context["cueanexo"],
                            ciclo=especial_context["ciclo"],
                        ),
                        alumno_banco_queryset=EspecialAlumnoBanco.objects.filter(
                            cueanexo=especial_context["cueanexo"],
                            ciclo=especial_context["ciclo"],
                        ),
                    )
                    if inscripcion_abierta:
                        messages.info(
                            request,
                            "Ese alumno ya está inscripto en esta sección.",
                        )
                    elif creada:
                        messages.success(request, "Alumno inscripto correctamente.")
                        return redirect(
                            redirect_con_contexto(
                                "especial:inscripcion_seccion",
                                especial_context,
                                seccion_id=seccion.pk,
                            )
                        )
                    else:
                        messages.success(
                            request,
                            "La inscripción del alumno fue reactivada correctamente.",
                        )
                        return redirect(
                            redirect_con_contexto(
                                "especial:inscripcion_seccion",
                                especial_context,
                                seccion_id=seccion.pk,
                            )
                        )
                except ValidationError as exc:
                    messages.error(request, "; ".join(exc.messages))
                except IntegrityError:
                    messages.error(
                        request,
                        "No se pudo crear la inscripción. Verificá que no exista una inscripción activa.",
                    )
    else:
        busqueda_form = EspecialBusquedaAlumnoForm(
            request.GET if request.GET.get("cuil") else None
        )

        if busqueda_form.is_valid():
            cuil_buscado = busqueda_form.cleaned_data["cuil"]
            alumno = _buscar_alumno(cuil_buscado)
            if alumno:
                inscripcion_abierta = AlumnoSeccion.objects.filter(
                    seccion=seccion,
                    alumno=alumno,
                    estado__in=ESTADOS_INSCRIPCION_ABIERTA,
                ).first()
        elif request.GET.get("cuil"):
            cuil_buscado = _solo_digitos(request.GET.get("cuil"))
            cuil_error = _errores_form(busqueda_form)

    next_url = _url_modal_seccion(seccion, especial_context, cuil_buscado)
    context.update(
        {
            "seccion": seccion,
            "inscripciones": _inscripciones_seccion(seccion),
            "busqueda_form": busqueda_form,
            "alumno": alumno,
            "alumno_row": _alumno_row(alumno),
            "cuil_buscado": cuil_buscado,
            "cuil_error": cuil_error,
            "inscripcion_abierta": inscripcion_abierta,
            "url_carga_alumno": _url_carga_alumno(cuil_buscado, next_url),
            "url_editar_alumno": _url_carga_alumno(cuil_buscado, next_url),
            "modal_alumno_abierto": abrir_modal,
            "modal_action_url": _url_modal_seccion(seccion, especial_context),
            "modal_tiene_seccion": True,
            "modal_volver_url": _url_inscripcion_seccion(seccion, especial_context),
        }
    )
    return render(request, "especial/inscripcion_seccion_especial.html", context)


@especial_required
def editar_inscripcion_seccion(request, seccion_id, inscripcion_id):
    """Vista para editar una inscripción de alumno a sección."""
    context = contexto_base(request, "secciones", "Editar inscripción Educación Especial")
    especial_context = context["especial_context"]
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
