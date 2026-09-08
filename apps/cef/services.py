# -*- coding: utf-8 -*-

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone
from django.utils.dateparse import parse_date

from .models import (
    CefAlumnoCef,
    CefCiclo,
    CefDocenteBnh,
    CefDocenteCef,
    CefDocenteGrupo,
    CefGrupo,
    CefGrupoEstadoMovimiento,
    CefInscripcion,
    PADRON_DB_ALIAS,
    solo_digitos,
    validar_docente_grupo_activo,
)


def validar_ciclo_escribible(ciclo):
    """Rechaza cualquier mutación asociada a un ciclo inexistente o cerrado."""

    ciclo_id = getattr(ciclo, "pk", ciclo)
    if not ciclo_id:
        raise ValidationError("El ciclo seleccionado no es válido.")
    queryset = CefCiclo.objects.filter(pk=ciclo_id).only("cerrado")
    if transaction.get_connection().in_atomic_block:
        queryset = queryset.select_for_update()
    ciclo_real = queryset.first()
    if ciclo_real is None:
        raise ValidationError("El ciclo seleccionado no es válido.")
    if ciclo_real.cerrado:
        raise ValidationError(
            "El ciclo está cerrado. La información se encuentra en modo sólo lectura."
        )
    return ciclo_real


def _normalizar_motivo_baja(motivo_baja):
    motivo = str(motivo_baja or "").strip()
    if len(motivo) > 255:
        raise ValidationError("El motivo de la baja no puede superar 255 caracteres.")
    return motivo


def _buscar_conflicto_horario_alumnos(
    *,
    alumnos_ids,
    grupo_destino_id,
    actividad_id,
    ciclo_id,
    cueanexo,
    hora_inicio,
    hora_fin,
    dias_ids,
):
    """Busca el primer conflicto dentro del CEF/ciclo con valores propuestos."""

    alumnos_ids = list(dict.fromkeys(alumnos_ids or []))
    dias_ids = list(dict.fromkeys(dias_ids or []))
    if not alumnos_ids or not dias_ids or not hora_inicio or not hora_fin:
        return None

    return (
        CefInscripcion.objects.filter(
            alumno_id__in=alumnos_ids,
            estado=CefInscripcion.Estado.ACTIVO,
            grupo__estado=CefGrupo.Estado.ACTIVO,
            grupo__ciclo_id=ciclo_id,
            grupo__cueanexo=cueanexo,
            grupo__hora_inicio__lt=hora_fin,
            grupo__hora_fin__gt=hora_inicio,
            grupo__dias_funcionamiento__dia_semana_id__in=dias_ids,
        )
        .exclude(grupo_id=grupo_destino_id)
        .exclude(grupo__actividad_id=actividad_id)
        .values(
            "alumno_id",
            "grupo_id",
            "grupo__actividad__nombre",
            "grupo__numero",
            "grupo__hora_inicio",
            "grupo__hora_fin",
            "grupo__dias_funcionamiento__dia_semana__nombre",
            "grupo__dias_funcionamiento__dia_semana__orden",
        )
        .order_by(
            "grupo__actividad__nombre",
            "grupo__numero",
            "grupo__dias_funcionamiento__dia_semana__orden",
            "alumno_id",
        )
        .first()
    )


def _mensaje_conflicto_horario(conflicto, *, edicion=False):
    actividad = conflicto["grupo__actividad__nombre"]
    numero = conflicto["grupo__numero"]
    dia = conflicto["grupo__dias_funcionamiento__dia_semana__nombre"]
    hora_inicio = conflicto["grupo__hora_inicio"].strftime("%H:%M")
    hora_fin = conflicto["grupo__hora_fin"].strftime("%H:%M")
    prefijo = (
        "No se puede modificar el grupo porque generaría un conflicto horario"
        if edicion
        else "No se puede inscribir al alumno porque existe un conflicto horario"
    )
    return (
        f"{prefijo} con {actividad} Nro. {numero}, "
        f"{dia} de {hora_inicio} a {hora_fin}."
    )


def validar_disponibilidad_horaria_alumno(grupo, alumno):
    """Valida una inscripción contra grupos activos del mismo CEF y ciclo."""

    conflicto = _buscar_conflicto_horario_alumnos(
        alumnos_ids=[alumno.pk],
        grupo_destino_id=grupo.pk,
        actividad_id=grupo.actividad_id,
        ciclo_id=grupo.ciclo_id,
        cueanexo=grupo.cueanexo,
        hora_inicio=grupo.hora_inicio,
        hora_fin=grupo.hora_fin,
        dias_ids=grupo.dias_funcionamiento.values_list(
            "dia_semana_id",
            flat=True,
        ),
    )
    if conflicto:
        raise ValidationError(_mensaje_conflicto_horario(conflicto))


def validar_conflictos_horarios_edicion_grupo(
    grupo,
    *,
    actividad_id,
    hora_inicio,
    hora_fin,
    dias_ids,
    alumnos_ids,
):
    """Valida en bloque los alumnos activos con el estado propuesto del grupo."""

    conflicto = _buscar_conflicto_horario_alumnos(
        alumnos_ids=alumnos_ids,
        grupo_destino_id=grupo.pk,
        actividad_id=actividad_id,
        ciclo_id=grupo.ciclo_id,
        cueanexo=grupo.cueanexo,
        hora_inicio=hora_inicio,
        hora_fin=hora_fin,
        dias_ids=dias_ids,
    )
    if conflicto:
        raise ValidationError(
            _mensaje_conflicto_horario(conflicto, edicion=True)
        )


def asegurar_alumno_banco_activo(alumno, cueanexo, ciclo, user):
    """Devuelve el periodo activo del alumno o crea uno nuevo."""

    try:
        with transaction.atomic():
            validar_ciclo_escribible(ciclo)
            periodos = list(
                CefAlumnoCef.objects.select_for_update()
                .filter(
                    cueanexo=cueanexo,
                    ciclo=ciclo,
                    alumno=alumno,
                )
                .order_by("-pk")
            )
            periodo_activo = next(
                (
                    periodo
                    for periodo in periodos
                    if periodo.estado == CefAlumnoCef.Estado.ACTIVO
                ),
                None,
            )
            if periodo_activo:
                return periodo_activo, False

            periodo_activo = CefAlumnoCef.objects.create(
                cueanexo=cueanexo,
                ciclo=ciclo,
                alumno=alumno,
                estado=CefAlumnoCef.Estado.ACTIVO,
                creado_por=user,
                actualizado_por=user,
            )
            return periodo_activo, True
    except IntegrityError:
        periodo_activo = CefAlumnoCef.objects.filter(
            cueanexo=cueanexo,
            ciclo=ciclo,
            alumno=alumno,
            estado=CefAlumnoCef.Estado.ACTIVO,
        ).first()
        if periodo_activo:
            return periodo_activo, False
        raise


def asegurar_docente_banco_activo(docente_cuil, cueanexo, ciclo, user):
    """Devuelve el periodo activo del docente o crea uno nuevo."""

    docente_cuil = solo_digitos(docente_cuil)
    try:
        with transaction.atomic():
            validar_ciclo_escribible(ciclo)
            docente_valido = CefDocenteBnh.objects.using(PADRON_DB_ALIAS).filter(
                cuil=docente_cuil
            ).exists()
            if not docente_valido:
                raise ValidationError("El profesor seleccionado no es válido.")

            periodos = list(
                CefDocenteCef.objects.select_for_update()
                .filter(
                    cueanexo=cueanexo,
                    ciclo=ciclo,
                    docente_cuil=docente_cuil,
                )
                .order_by("-pk")
            )
            periodo_activo = next(
                (
                    periodo
                    for periodo in periodos
                    if periodo.estado == CefDocenteCef.Estado.ACTIVO
                ),
                None,
            )
            if periodo_activo:
                return periodo_activo, False

            periodo_activo = CefDocenteCef.objects.create(
                cueanexo=cueanexo,
                ciclo=ciclo,
                docente_cuil=docente_cuil,
                estado=CefDocenteCef.Estado.ACTIVO,
                creado_por=user,
                actualizado_por=user,
            )
            return periodo_activo, True
    except IntegrityError:
        periodo_activo = CefDocenteCef.objects.filter(
            cueanexo=cueanexo,
            ciclo=ciclo,
            docente_cuil=docente_cuil,
            estado=CefDocenteCef.Estado.ACTIVO,
        ).first()
        if periodo_activo:
            return periodo_activo, False
        raise


def validar_fecha_inscripcion_grupo(grupo, fecha_inscripcion):
    """Valida la fecha efectiva de incorporación de un alumno a un grupo."""

    if isinstance(fecha_inscripcion, str):
        try:
            fecha_inscripcion = parse_date(fecha_inscripcion.strip())
        except ValueError:
            fecha_inscripcion = None
    if not fecha_inscripcion or not getattr(fecha_inscripcion, "year", None):
        raise ValidationError("Indicá la fecha de incorporación al grupo.")
    if fecha_inscripcion.year != grupo.ciclo.anio:
        raise ValidationError(
            "La fecha de incorporación al grupo debe pertenecer al año del ciclo."
        )
    return fecha_inscripcion


def crear_inscripcion_activa(
    grupo,
    alumno,
    user,
    fecha_inscripcion=None,
):
    """Crea una inscripcion activa nueva sin reactivar periodos historicos."""

    try:
        with transaction.atomic():
            grupo = CefGrupo.objects.select_for_update().get(pk=grupo.pk)
            validar_ciclo_escribible(grupo.ciclo_id)
            fecha_inscripcion = validar_fecha_inscripcion_grupo(
                grupo,
                fecha_inscripcion,
            )
            if grupo.estado != CefGrupo.Estado.ACTIVO:
                raise ValidationError(
                    "No se puede inscribir alumnos en un grupo dado de baja."
                )

            alumno_cef_activo = CefAlumnoCef.objects.select_for_update().filter(
                cueanexo=grupo.cueanexo,
                ciclo=grupo.ciclo,
                alumno=alumno,
                estado=CefAlumnoCef.Estado.ACTIVO,
            ).order_by("pk").first()
            if not alumno_cef_activo:
                raise ValidationError(
                    "El alumno no está activo en el banco de este CEF y ciclo. "
                    "Reincorporalo antes de inscribirlo."
                )

            if CefInscripcion.objects.filter(
                grupo=grupo,
                alumno=alumno,
                estado=CefInscripcion.Estado.ACTIVO,
            ).exists():
                raise ValidationError(
                    "El alumno ya tiene una inscripción activa en este grupo."
                )

            validar_disponibilidad_horaria_alumno(grupo, alumno)

            return CefInscripcion.objects.create(
                grupo=grupo,
                alumno=alumno,
                estado=CefInscripcion.Estado.ACTIVO,
                fecha_inscripcion=fecha_inscripcion,
                creado_por=user,
                actualizado_por=user,
            )
    except IntegrityError:
        raise ValidationError(
            "El alumno ya tiene una inscripción activa en este grupo."
        ) from None


def dar_baja_inscripcion(
    inscripcion,
    user,
    motivo_baja,
    fecha_baja=None,
):
    """Finaliza una inscripcion activa sin eliminar ni reactivar filas."""

    with transaction.atomic():
        inscripcion = CefInscripcion.objects.select_for_update().get(
            pk=inscripcion.pk
        )
        validar_ciclo_escribible(inscripcion.grupo.ciclo_id)
        if inscripcion.estado != CefInscripcion.Estado.ACTIVO:
            raise ValidationError("La inscripción ya se encuentra dada de baja.")
        motivo_baja = _normalizar_motivo_baja(motivo_baja)

        inscripcion.estado = CefInscripcion.Estado.BAJA
        inscripcion.fecha_baja = fecha_baja or timezone.localdate()
        inscripcion.motivo_baja = motivo_baja
        inscripcion.actualizado_por = user
        inscripcion.save()
        return inscripcion


def reinscribir_alumno(
    inscripcion_origen,
    user,
    fecha_inscripcion=None,
):
    """Crea una nueva inscripcion activa desde una fila historica en baja."""

    if inscripcion_origen.estado == CefInscripcion.Estado.ACTIVO:
        raise ValidationError("La inscripción ya se encuentra activa.")

    return crear_inscripcion_activa(
        grupo=inscripcion_origen.grupo,
        alumno=inscripcion_origen.alumno,
        user=user,
        fecha_inscripcion=fecha_inscripcion,
    )


def crear_asignacion_docente_activa(
    grupo,
    docente_cuil,
    rol,
    user,
    fecha_desde,
    observaciones="",
):
    """Crea una asignacion docente activa nueva."""

    if not fecha_desde:
        raise ValidationError("Debe indicar la fecha de asignación del profesor.")

    docente_cuil = solo_digitos(docente_cuil)
    try:
        with transaction.atomic():
            grupo = CefGrupo.objects.select_for_update().get(pk=grupo.pk)
            validar_ciclo_escribible(grupo.ciclo_id)
            if grupo.estado != CefGrupo.Estado.ACTIVO:
                raise ValidationError(
                    "No se pueden asignar profesores a un grupo dado de baja."
                )

            docente_cef_activo = CefDocenteCef.objects.select_for_update().filter(
                cueanexo=grupo.cueanexo,
                ciclo=grupo.ciclo,
                docente_cuil=docente_cuil,
                estado=CefDocenteCef.Estado.ACTIVO,
            ).order_by("pk").first()
            if not docente_cef_activo:
                raise ValidationError(
                    "El profesor no está activo en el banco de este CEF y ciclo. "
                    "Reincorporalo antes de asignarlo."
                )

            validar_docente_grupo_activo(grupo, docente_cuil, rol)
            return CefDocenteGrupo.objects.create(
                grupo=grupo,
                docente_cuil=docente_cuil,
                rol=rol,
                estado=CefDocenteGrupo.Estado.ACTIVO,
                fecha_desde=fecha_desde,
                observaciones=observaciones,
                creado_por=user,
                actualizado_por=user,
            )
    except IntegrityError:
        raise ValidationError(
            "No se pudo crear la asignación. Verificá que no exista un docente "
            "o rol activo duplicado."
        ) from None


def dar_baja_asignacion_docente(
    asignacion,
    user,
    motivo_baja,
    fecha_hasta=None,
):
    """Finaliza una asignacion activa sin eliminar la fila historica."""

    with transaction.atomic():
        asignacion = CefDocenteGrupo.objects.select_for_update().get(
            pk=asignacion.pk
        )
        validar_ciclo_escribible(asignacion.grupo.ciclo_id)
        if asignacion.estado != CefDocenteGrupo.Estado.ACTIVO:
            raise ValidationError("La asignación ya se encuentra dada de baja.")
        motivo_baja = _normalizar_motivo_baja(motivo_baja)

        asignacion.estado = CefDocenteGrupo.Estado.BAJA
        asignacion.fecha_hasta = fecha_hasta or timezone.localdate()
        asignacion.motivo_baja = motivo_baja
        asignacion.actualizado_por = user
        asignacion.save()
        return asignacion


def reasignar_docente_grupo(
    asignacion_origen,
    user,
    fecha_desde=None,
    rol=None,
):
    """Crea una asignacion activa nueva desde una fila historica en baja."""

    if asignacion_origen.estado == CefDocenteGrupo.Estado.ACTIVO:
        raise ValidationError("La asignación ya se encuentra activa.")

    return crear_asignacion_docente_activa(
        grupo=asignacion_origen.grupo,
        docente_cuil=asignacion_origen.docente_cuil,
        rol=rol or asignacion_origen.rol,
        user=user,
        fecha_desde=fecha_desde or timezone.localdate(),
    )


def dar_baja_alumno_banco(alumno_cef, user, motivo_baja, fecha_baja=None):
    """Finaliza un periodo del banco si no conserva inscripciones activas."""

    with transaction.atomic():
        alumno_cef = CefAlumnoCef.objects.select_for_update().get(pk=alumno_cef.pk)
        validar_ciclo_escribible(alumno_cef.ciclo_id)
        if alumno_cef.estado != CefAlumnoCef.Estado.ACTIVO:
            raise ValidationError("El alumno ya se encuentra dado de baja del banco.")
        motivo_baja = _normalizar_motivo_baja(motivo_baja)

        tiene_inscripciones = CefInscripcion.objects.filter(
            alumno=alumno_cef.alumno,
            grupo__cueanexo=alumno_cef.cueanexo,
            grupo__ciclo=alumno_cef.ciclo,
            estado=CefInscripcion.Estado.ACTIVO,
        ).exists()
        if tiene_inscripciones:
            raise ValidationError(
                "No se puede dar de baja al alumno del banco mientras tenga "
                "inscripciones activas en este CEF y ciclo. Primero debe dar "
                "de baja esas inscripciones desde la gestión de los grupos."
            )

        alumno_cef.estado = CefAlumnoCef.Estado.BAJA
        alumno_cef.fecha_baja = fecha_baja or timezone.localdate()
        alumno_cef.motivo_baja = motivo_baja
        alumno_cef.actualizado_por = user
        alumno_cef.save()
        return alumno_cef


def dar_baja_docente_banco(docente_cef, user, motivo_baja, fecha_baja=None):
    """Finaliza un periodo del banco si no conserva asignaciones activas."""

    with transaction.atomic():
        docente_cef = CefDocenteCef.objects.select_for_update().get(pk=docente_cef.pk)
        validar_ciclo_escribible(docente_cef.ciclo_id)
        if docente_cef.estado != CefDocenteCef.Estado.ACTIVO:
            raise ValidationError("El profesor ya se encuentra dado de baja del banco.")
        motivo_baja = _normalizar_motivo_baja(motivo_baja)

        tiene_asignaciones = CefDocenteGrupo.objects.filter(
            docente_cuil=docente_cef.docente_cuil,
            grupo__cueanexo=docente_cef.cueanexo,
            grupo__ciclo=docente_cef.ciclo,
            estado=CefDocenteGrupo.Estado.ACTIVO,
        ).exists()
        if tiene_asignaciones:
            raise ValidationError(
                "No se puede dar de baja al profesor del banco mientras tenga "
                "asignaciones activas en este CEF y ciclo. Primero debe dar de "
                "baja esas asignaciones desde la gestión de los grupos."
            )

        docente_cef.estado = CefDocenteCef.Estado.BAJA
        docente_cef.fecha_baja = fecha_baja or timezone.localdate()
        docente_cef.motivo_baja = motivo_baja
        docente_cef.actualizado_por = user
        docente_cef.save()
        return docente_cef


def dar_baja_grupo(grupo, user, motivo_baja, fecha_baja=None):
    """Registra la baja actual de un grupo vacío y conserva su transición."""

    with transaction.atomic():
        grupo = CefGrupo.objects.select_for_update().get(pk=grupo.pk)
        validar_ciclo_escribible(grupo.ciclo_id)
        if grupo.estado != CefGrupo.Estado.ACTIVO:
            raise ValidationError("El grupo ya se encuentra dado de baja.")
        motivo_baja = _normalizar_motivo_baja(motivo_baja)

        alumnos_activos = CefInscripcion.objects.filter(
            grupo=grupo,
            estado=CefInscripcion.Estado.ACTIVO,
        ).exists()
        docentes_activos = CefDocenteGrupo.objects.filter(
            grupo=grupo,
            estado=CefDocenteGrupo.Estado.ACTIVO,
        ).exists()
        if alumnos_activos or docentes_activos:
            raise ValidationError(
                "No se puede dar de baja el grupo mientras tenga alumnos o "
                "profesores activos. Primero debe dar de baja esas relaciones "
                "desde Gestionar grupo."
            )

        fecha_baja = fecha_baja or timezone.localdate()
        grupo.estado = CefGrupo.Estado.BAJA
        grupo.fecha_baja = fecha_baja
        grupo.motivo_baja = motivo_baja
        grupo.actualizado_por = user
        grupo.save()

        CefGrupoEstadoMovimiento.objects.create(
            grupo=grupo,
            estado_resultante=CefGrupo.Estado.BAJA,
            fecha=fecha_baja,
            motivo=motivo_baja,
            creado_por=user,
            actualizado_por=user,
        )
        return grupo


def reactivar_grupo(grupo, user, fecha_reactivacion=None):
    """Reactiva el mismo grupo sin modificar sus relaciones históricas."""

    with transaction.atomic():
        grupo = CefGrupo.objects.select_for_update().get(pk=grupo.pk)
        validar_ciclo_escribible(grupo.ciclo_id)
        if grupo.estado != CefGrupo.Estado.BAJA:
            raise ValidationError("El grupo ya se encuentra activo.")

        alumnos_activos = CefInscripcion.objects.filter(
            grupo=grupo,
            estado=CefInscripcion.Estado.ACTIVO,
        ).exists()
        docentes_activos = CefDocenteGrupo.objects.filter(
            grupo=grupo,
            estado=CefDocenteGrupo.Estado.ACTIVO,
        ).exists()
        if alumnos_activos or docentes_activos:
            raise ValidationError(
                "No se puede reactivar el grupo porque conserva alumnos o "
                "profesores activos de forma inconsistente."
            )

        fecha_reactivacion = fecha_reactivacion or timezone.localdate()
        motivo_baja_actual = (grupo.motivo_baja or "").strip()
        ultimo_movimiento = (
            CefGrupoEstadoMovimiento.objects.filter(grupo=grupo)
            .order_by("-creado_en", "-pk")
            .first()
        )
        baja_actual_registrada = (
            ultimo_movimiento
            and ultimo_movimiento.estado_resultante == CefGrupo.Estado.BAJA
            and ultimo_movimiento.fecha == grupo.fecha_baja
            and ultimo_movimiento.motivo == motivo_baja_actual
        )
        if not baja_actual_registrada:
            CefGrupoEstadoMovimiento.objects.create(
                grupo=grupo,
                estado_resultante=CefGrupo.Estado.BAJA,
                fecha=grupo.fecha_baja,
                motivo=motivo_baja_actual,
                creado_por=grupo.actualizado_por or user,
                actualizado_por=grupo.actualizado_por or user,
            )

        CefGrupoEstadoMovimiento.objects.create(
            grupo=grupo,
            estado_resultante=CefGrupo.Estado.ACTIVO,
            fecha=fecha_reactivacion,
            motivo="",
            creado_por=user,
            actualizado_por=user,
        )

        grupo.estado = CefGrupo.Estado.ACTIVO
        grupo.fecha_baja = None
        grupo.motivo_baja = ""
        grupo.actualizado_por = user
        grupo.save()
        return grupo
