# -*- coding: utf-8 -*-

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from .models import (
    CefAsistencia,
    CefAsistenciaMovimiento,
    CefGrupo,
    CefInscripcion,
    CefJornadaAsistencia,
)
from .services import validar_ciclo_escribible


def inscripciones_vigentes_jornada(grupo, fecha):
    """Devuelve una única inscripción representativa por alumno para la fecha."""

    candidatas = list(
        CefInscripcion.objects.filter(
            grupo=grupo,
            fecha_inscripcion__lte=fecha,
        )
        .filter(Q(fecha_baja__isnull=True) | Q(fecha_baja__gte=fecha))
        .select_related("alumno", "alumno__sexo")
        .order_by("alumno__apellidos", "alumno__nombres", "pk")
    )
    if not candidatas:
        return []

    ids_con_asistencia = set(
        CefAsistencia.objects.filter(
            jornada__grupo=grupo,
            jornada__fecha=fecha,
            inscripcion_id__in=[item.pk for item in candidatas],
        ).values_list("inscripcion_id", flat=True)
    )
    seleccionadas = {}
    for inscripcion in candidatas:
        prioridad = (
            inscripcion.pk in ids_con_asistencia,
            inscripcion.estado == CefInscripcion.Estado.ACTIVO,
            inscripcion.fecha_inscripcion,
            inscripcion.creado_en,
            inscripcion.pk,
        )
        anterior = seleccionadas.get(inscripcion.alumno_id)
        if anterior is None or prioridad > anterior[0]:
            seleccionadas[inscripcion.alumno_id] = (prioridad, inscripcion)

    return sorted(
        (item[1] for item in seleccionadas.values()),
        key=lambda item: (
            (item.alumno.apellidos or "").casefold(),
            (item.alumno.nombres or "").casefold(),
            item.pk,
        ),
    )


def fecha_jornada_habitual(grupo, fecha):
    numeros = {
        numero
        for numero in grupo.dias_funcionamiento.values_list(
            "dia_semana__numero",
            flat=True,
        )
    }
    return fecha.isoweekday() in numeros


def _validar_fecha_jornada(grupo, fecha):
    ciclo = grupo.ciclo
    if fecha.year != ciclo.anio:
        raise ValidationError("La fecha debe corresponder al año del ciclo.")
    if fecha > timezone.localdate():
        raise ValidationError(
            "No se puede registrar asistencia de una fecha futura."
        )


def _bloquear_grupo_asistencia(grupo, fecha):
    grupo = CefGrupo.objects.select_for_update().select_related("ciclo").filter(
        pk=grupo.pk
    ).first()
    if grupo is None:
        raise ValidationError("El grupo seleccionado no es válido.")
    validar_ciclo_escribible(grupo.ciclo_id)
    if grupo.estado != CefGrupo.Estado.ACTIVO:
        raise ValidationError(
            "El grupo está dado de baja. La asistencia es de sólo lectura."
        )
    _validar_fecha_jornada(grupo, fecha)
    return grupo


def registrar_asistencias_jornada(grupo, fecha, estados_por_inscripcion, user):
    """Crea la jornada si hace falta y guarda todos los estados de la fecha."""

    estados_validos = {valor for valor, _ in CefAsistencia.Estado.choices}
    estados_normalizados = {}
    for inscripcion_id, estado in (estados_por_inscripcion or {}).items():
        estado = str(estado or "").strip()
        if not estado:
            continue
        if estado not in estados_validos:
            raise ValidationError("Existe un estado de asistencia no válido.")
        try:
            inscripcion_id = int(inscripcion_id)
        except (TypeError, ValueError):
            raise ValidationError("Existe una inscripción no válida.") from None
        estados_normalizados[inscripcion_id] = estado

    with transaction.atomic():
        grupo = _bloquear_grupo_asistencia(grupo, fecha)

        inscripciones = list(inscripciones_vigentes_jornada(grupo, fecha))
        if not inscripciones:
            raise ValidationError(
                "No hay alumnos vigentes para registrar en esta fecha."
            )
        inscripciones_por_id = {item.pk: item for item in inscripciones}
        ids_invalidos = set(estados_normalizados) - set(inscripciones_por_id)
        if ids_invalidos:
            raise ValidationError(
                "Una de las inscripciones no corresponde al grupo o no estaba vigente en la fecha."
            )
        ids_faltantes = set(inscripciones_por_id) - set(estados_normalizados)
        if ids_faltantes:
            raise ValidationError(
                "Registrá la asistencia de todos los alumnos antes de guardar."
            )

        jornada, jornada_creada = CefJornadaAsistencia.objects.get_or_create(
            grupo=grupo,
            fecha=fecha,
            defaults={
                "creado_por": user,
                "actualizado_por": user,
            },
        )
        if not jornada_creada:
            jornada = CefJornadaAsistencia.objects.select_for_update().get(
                pk=jornada.pk
            )
        cargada_previamente = CefAsistencia.objects.filter(
            jornada=jornada
        ).exists()

        existentes = {
            item.inscripcion_id: item
            for item in (
                CefAsistencia.objects.select_for_update()
                .filter(
                    jornada=jornada,
                    inscripcion_id__in=estados_normalizados,
                )
                .select_related(
                    "jornada__grupo__ciclo",
                    "inscripcion__grupo",
                )
            )
        }
        altas = 0
        cambios = 0
        for inscripcion_id, estado_nuevo in estados_normalizados.items():
            asistencia = existentes.get(inscripcion_id)
            estado_anterior = asistencia.estado if asistencia else None
            if estado_anterior == estado_nuevo:
                continue

            if asistencia is None:
                asistencia = CefAsistencia.objects.create(
                    jornada=jornada,
                    inscripcion=inscripciones_por_id[inscripcion_id],
                    estado=estado_nuevo,
                    creado_por=user,
                    actualizado_por=user,
                )
                altas += 1
            else:
                asistencia.estado = estado_nuevo
                asistencia.actualizado_por = user
                asistencia.save(
                    update_fields=[
                        "estado",
                        "actualizado_por",
                        "actualizado_en",
                    ]
                )
                cambios += 1

            CefAsistenciaMovimiento.objects.create(
                asistencia=asistencia,
                estado_anterior=estado_anterior,
                estado_nuevo=estado_nuevo,
                creado_por=user,
                actualizado_por=user,
            )

        if altas or cambios:
            jornada.actualizado_por = user
            jornada.save(update_fields=["actualizado_por", "actualizado_en"])

        return {
            "jornada": jornada,
            "jornada_creada": jornada_creada,
            "cargada_previamente": cargada_previamente,
            "altas": altas,
            "cambios": cambios,
        }
