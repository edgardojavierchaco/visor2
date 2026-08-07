# -*- coding: utf-8 -*-

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q

from .models import (
    CefAsistencia,
    CefAsistenciaMovimiento,
    CefCiclo,
    CefGrupo,
    CefInscripcion,
    CefJornadaAsistencia,
)
from .services import validar_ciclo_escribible


def inscripciones_vigentes_jornada(grupo, fecha):
    """Inscripciones cuyo período incluye la fecha, incluida su fecha de baja."""

    return (
        CefInscripcion.objects.filter(
            grupo=grupo,
            fecha_inscripcion__lte=fecha,
        )
        .filter(Q(fecha_baja__isnull=True) | Q(fecha_baja__gte=fecha))
        .select_related("alumno", "alumno__sexo")
        .order_by("alumno__apellidos", "alumno__nombres", "pk")
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


def registrar_asistencias_jornada(grupo, fecha, estados_por_inscripcion, user):
    """Crea o abre una jornada y guarda todos sus cambios en una transacción."""

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
        ciclo_id = (
            CefGrupo.objects.filter(pk=grupo.pk)
            .values_list("ciclo_id", flat=True)
            .first()
        )
        if not ciclo_id:
            raise ValidationError("El grupo seleccionado no es válido.")
        ciclo = CefCiclo.objects.select_for_update().get(pk=ciclo_id)
        validar_ciclo_escribible(ciclo)
        grupo = (
            CefGrupo.objects.select_for_update()
            .select_related("ciclo")
            .get(pk=grupo.pk)
        )
        if grupo.estado != CefGrupo.Estado.ACTIVO:
            raise ValidationError(
                "El grupo está dado de baja. La asistencia es de sólo lectura."
            )
        _validar_fecha_jornada(grupo, fecha)

        inscripciones = list(inscripciones_vigentes_jornada(grupo, fecha))
        inscripciones_por_id = {item.pk: item for item in inscripciones}
        ids_invalidos = set(estados_normalizados) - set(inscripciones_por_id)
        if ids_invalidos:
            raise ValidationError(
                "Una de las inscripciones no corresponde al grupo o no estaba vigente en la fecha."
            )

        jornada, creada = CefJornadaAsistencia.objects.get_or_create(
            grupo=grupo,
            fecha=fecha,
            defaults={
                "creado_por": user,
                "actualizado_por": user,
            },
        )
        if not creada:
            jornada = (
                CefJornadaAsistencia.objects.select_for_update()
                .select_related("grupo__ciclo")
                .get(pk=jornada.pk)
            )

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

        return {
            "jornada": jornada,
            "jornada_creada": creada,
            "altas": altas,
            "cambios": cambios,
        }
