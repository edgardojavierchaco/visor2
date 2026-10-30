# -*- coding: utf-8 -*-

from datetime import date

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.utils import timezone
from django.utils.dateparse import parse_date

from .models import (
    CefAlumnoCef,
    CefAsistencia,
    CefCiclo,
    CefDocenteBnh,
    CefDocenteCef,
    CefDocenteGrupo,
    CefGrupo,
    CefGrupoEstadoMovimiento,
    CefInscripcion,
    CefJornadaAsistencia,
    PADRON_DB_ALIAS,
    solo_digitos,
    usuario_puede_rectificar_cef,
    validar_docente_grupo_activo,
    validar_cupo_maximo,
)


from .services_bnh import validar_docente_vinculado_bnh


class ConflictoHorarioInscripcionError(ValidationError):
    def __init__(self, message, conflictos):
        super().__init__(message)
        self.conflictos = conflictos


def motivo_bloqueo_inicio_ciclo(ciclo, *, hoy=None):
    """Explica la falta de habilitación ordinaria sin alterar ciclos cerrados."""

    if ciclo is None or ciclo.cerrado:
        return ""
    if ciclo.fecha_inicio is None:
        return (
            "Este ciclo todavía no tiene fecha de inicio oficial configurada. "
            "Solicitá su configuración al Administrador."
        )
    hoy = timezone.localdate() if hoy is None else hoy
    if hoy < ciclo.fecha_inicio:
        return (
            f"Las cargas del ciclo {ciclo.anio} estarán habilitadas a partir del "
            f"{ciclo.fecha_inicio:%d/%m/%Y}."
        )
    return ""


def validar_fechas_oficiales_ciclo(anio, fecha_inicio, fecha_fin=None):
    """Valida fechas administrativas; el inicio puede ser futuro."""

    fechas = {}
    errores = {}
    for campo, valor in (("fecha_inicio", fecha_inicio), ("fecha_fin", fecha_fin)):
        if valor is None or valor == "":
            fechas[campo] = None
            if campo == "fecha_inicio":
                errores[campo] = "Indicá la fecha de inicio oficial del ciclo."
            continue
        if isinstance(valor, str):
            try:
                valor = parse_date(valor.strip())
            except ValueError:
                valor = None
        if not isinstance(valor, date):
            errores[campo] = "Indicá una fecha válida."
        elif valor.year != anio:
            errores[campo] = f"La fecha debe pertenecer al año {anio}."
        fechas[campo] = valor
    if not errores and fechas["fecha_fin"] and fechas["fecha_fin"] < fechas["fecha_inicio"]:
        errores["fecha_fin"] = "La fecha de fin prevista no puede ser anterior al inicio oficial."
    if errores:
        raise ValidationError(errores)
    return fechas["fecha_inicio"], fechas["fecha_fin"]


def validar_cambio_inicio_ciclo(ciclo, fecha_inicio, *, fecha_inicio_anterior):
    """Impide dejar vigencias existentes por debajo del nuevo inicio."""

    if fecha_inicio == fecha_inicio_anterior:
        return
    if ciclo.cerrado:
        raise ValidationError("No se puede modificar el inicio oficial de un ciclo cerrado.")
    entidades = (
        (CefAlumnoCef, "ciclo", ("fecha_alta", "fecha_baja"), "períodos de alumnos"),
        (CefDocenteCef, "ciclo", ("fecha_alta", "fecha_baja"), "períodos de profesores"),
        (CefInscripcion, "grupo__ciclo", ("fecha_inscripcion", "fecha_baja"), "inscripciones"),
        (CefDocenteGrupo, "grupo__ciclo", ("fecha_desde", "fecha_hasta"), "asignaciones docentes"),
        (CefGrupo, "ciclo", ("fecha_baja",), "bajas de grupos"),
        (CefGrupoEstadoMovimiento, "grupo__ciclo", ("fecha",), "movimientos de grupos"),
        (CefJornadaAsistencia, "grupo__ciclo", ("fecha",), "jornadas de asistencia"),
    )
    for modelo, alcance, campos, nombre in entidades:
        anteriores = Q(**{f"{campos[0]}__lt": fecha_inicio})
        for campo in campos[1:]:
            anteriores |= Q(**{f"{campo}__lt": fecha_inicio})
        if modelo.objects.filter(**{alcance: ciclo}).filter(anteriores).exists():
            raise ValidationError(
                f"No se puede establecer el inicio oficial en {fecha_inicio:%d/%m/%Y}: "
                f"existen {nombre} con fechas efectivas anteriores. No se modificó ningún registro."
            )


def validar_ciclo_escribible(ciclo, user=None, *, cueanexo=None):
    """Valida el ciclo y la excepción administrativa de escritura histórica."""

    ciclo_id = getattr(ciclo, "pk", ciclo)
    if not ciclo_id:
        raise ValidationError("El ciclo seleccionado no es válido.")
    queryset = CefCiclo.objects.filter(pk=ciclo_id).only("cerrado", "anio", "fecha_inicio")
    if transaction.get_connection().in_atomic_block:
        queryset = queryset.select_for_update()
    ciclo_real = queryset.first()
    if ciclo_real is None:
        raise ValidationError("El ciclo seleccionado no es válido.")
    if ciclo_real.cerrado and not usuario_puede_rectificar_cef(
        user, cueanexo=cueanexo,
    ):
        raise ValidationError(
            "El ciclo está cerrado. La información se encuentra en modo sólo lectura."
        )
    bloqueo_inicio = motivo_bloqueo_inicio_ciclo(ciclo_real)
    if bloqueo_inicio:
        raise ValidationError(bloqueo_inicio)
    return ciclo_real


def fecha_operativa_predeterminada(ciclo):
    """Obtiene la fecha automática dentro del año funcional del ciclo."""

    hoy = timezone.localdate()
    if motivo_bloqueo_inicio_ciclo(ciclo, hoy=hoy):
        return None
    inicio = ciclo.fecha_inicio or date(ciclo.anio, 1, 1)
    fin = date(ciclo.anio, 12, 31)
    fecha = min(hoy, fin)
    return fecha if fecha >= inicio else None


def validar_fecha_operativa_ciclo(
    ciclo,
    fecha,
    *,
    obligatoria=True,
    mensaje_requerida="Indicá la fecha de la operación.",
    mensaje_invalida="Indicá una fecha válida para la operación.",
    mensaje_anio="La fecha de la operación debe pertenecer al año del ciclo.",
    fecha_minima=None,
    mensaje_anterior="La fecha de la operación no puede ser anterior a su inicio.",
    fecha_maxima=None,
    mensaje_posterior="La fecha de la operación no puede ser posterior al límite.",
):
    """Valida una fecha funcional sin corregir valores explícitos."""

    if fecha is None or (isinstance(fecha, str) and not fecha.strip()):
        if obligatoria:
            raise ValidationError(mensaje_requerida)
        return None
    if isinstance(fecha, str):
        try:
            fecha = parse_date(fecha.strip())
        except ValueError:
            fecha = None
    if not isinstance(fecha, date):
        raise ValidationError(mensaje_invalida)
    if fecha.year != ciclo.anio:
        raise ValidationError(mensaje_anio)
    if ciclo.fecha_inicio is not None and fecha < ciclo.fecha_inicio:
        raise ValidationError(
            "La fecha no puede ser anterior al inicio oficial del ciclo: "
            f"{ciclo.fecha_inicio:%d/%m/%Y}."
        )
    hoy = timezone.localdate()
    fecha_maxima = min(hoy, fecha_maxima) if fecha_maxima is not None else hoy
    if fecha_minima is not None and fecha < fecha_minima:
        raise ValidationError(
            f"{mensaje_anterior} Fecha mínima permitida: {fecha_minima:%d/%m/%Y}."
        )
    if fecha_maxima is not None and fecha > fecha_maxima:
        raise ValidationError(
            f"{mensaje_posterior} Fecha máxima permitida: {fecha_maxima:%d/%m/%Y}."
        )
    return fecha


def validar_fecha_interactiva_ciclo(
    ciclo, fecha, *, fecha_minima=None, fecha_maxima=None, **mensajes,
):
    """Aplica el techo de hoy a operaciones de vigencia interactivas."""

    hoy = timezone.localdate()
    if fecha_minima is not None and fecha_minima > hoy:
        raise ValidationError(
            "Esta operación todavía no puede registrarse: el historial exige "
            f"como mínimo {fecha_minima:%d/%m/%Y}, una fecha posterior a hoy."
        )
    fecha_maxima = min(hoy, fecha_maxima) if fecha_maxima is not None else hoy
    mensajes.setdefault(
        "mensaje_posterior", "No se puede registrar una fecha efectiva futura.",
    )
    return validar_fecha_operativa_ciclo(
        ciclo,
        fecha,
        fecha_minima=fecha_minima,
        fecha_maxima=fecha_maxima,
        **mensajes,
    )


def _normalizar_motivo_baja(motivo_baja):
    motivo = str(motivo_baja or "").strip()
    if len(motivo) > 255:
        raise ValidationError("El motivo de la baja no puede superar 255 caracteres.")
    return motivo


def _buscar_conflicto_horario_alumnos(
    *,
    alumnos_ids,
    grupo_destino_id,
    ciclo_id,
    cueanexo,
    hora_inicio,
    hora_fin,
    dias_ids,
):
    """Busca todos los conflictos horarios dentro del mismo CEF y ciclo."""

    alumnos_ids = list(dict.fromkeys(alumnos_ids or []))
    dias_ids = list(dict.fromkeys(dias_ids or []))
    if not alumnos_ids or not dias_ids or not hora_inicio or not hora_fin:
        return []

    return list(
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
        .values(
            "alumno_id",
            "alumno__apellidos",
            "alumno__nombres",
            "grupo_id",
            "grupo__actividad__nombre",
            "grupo__numero",
            "grupo__hora_inicio",
            "grupo__hora_fin",
            "grupo__dias_funcionamiento__dia_semana__nombre",
            "grupo__dias_funcionamiento__dia_semana__orden",
        )
        .order_by(
            "alumno__apellidos",
            "alumno__nombres",
            "grupo__actividad__nombre",
            "grupo__numero",
            "grupo__dias_funcionamiento__dia_semana__orden",
            "grupo_id",
        )
    )


def _agrupar_conflictos_horarios(conflictos):
    """Agrupa filas repetidas por día para informar cada grupo una sola vez."""

    agrupados = {}
    for conflicto in conflictos:
        clave = (conflicto["alumno_id"], conflicto["grupo_id"])
        if clave not in agrupados:
            agrupados[clave] = {
                "alumno_id": conflicto["alumno_id"],
                "alumno_apellidos": conflicto.get("alumno__apellidos") or "",
                "alumno_nombres": conflicto.get("alumno__nombres") or "",
                "grupo_id": conflicto["grupo_id"],
                "actividad": conflicto["grupo__actividad__nombre"] or "Actividad sin informar",
                "numero": conflicto["grupo__numero"],
                "hora_inicio": conflicto["grupo__hora_inicio"],
                "hora_fin": conflicto["grupo__hora_fin"],
                "dias": [],
            }

        dia = str(
            conflicto.get("grupo__dias_funcionamiento__dia_semana__nombre") or ""
        ).strip()
        if dia and dia not in agrupados[clave]["dias"]:
            agrupados[clave]["dias"].append(dia)

    return list(agrupados.values())


def _texto_dias_conflicto(dias):
    if not dias:
        return "día sin informar"
    if len(dias) == 1:
        return dias[0]
    return f"{', '.join(dias[:-1])} y {dias[-1]}"


def _detalle_conflicto_horario(conflicto, *, incluir_alumno=False):
    numero = conflicto["numero"]
    numero = numero if numero not in (None, "") else "-"
    dias = _texto_dias_conflicto(conflicto["dias"])
    hora_inicio = conflicto["hora_inicio"].strftime("%H:%M")
    hora_fin = conflicto["hora_fin"].strftime("%H:%M")
    detalle = (
        f"{conflicto['actividad']} N.° {numero} "
        f"({dias}, {hora_inicio} a {hora_fin})"
    )
    if not incluir_alumno:
        return detalle

    nombre = _nombre_alumno_conflicto(conflicto)
    return f"{nombre}: {detalle}"


def _nombre_alumno_conflicto(conflicto):
    nombre = ", ".join(
        parte
        for parte in (
            conflicto["alumno_apellidos"].strip(),
            conflicto["alumno_nombres"].strip(),
        )
        if parte
    )
    if not nombre:
        nombre = f"Alumno ID {conflicto['alumno_id']}"
    return nombre


def _nombre_grupo_horario(grupo):
    actividad = getattr(getattr(grupo, "actividad", None), "nombre", None)
    actividad = actividad or "Actividad sin informar"
    numero = getattr(grupo, "numero", None)
    numero = numero if numero not in (None, "") else "-"
    return f"{actividad} N.° {numero}"


def _mensaje_conflicto_horario(conflictos, *, edicion=False, grupo_destino=None):
    agrupados = _agrupar_conflictos_horarios(conflictos)

    if edicion:
        detalles = "; ".join(
            _detalle_conflicto_horario(conflicto, incluir_alumno=True)
            for conflicto in agrupados
        )
        cantidad = "un conflicto horario" if len(agrupados) == 1 else "conflictos horarios"
        return (
            f"No se puede modificar el grupo porque generaría {cantidad} "
            f"para alumnos ya inscriptos: {detalles}."
        )

    if len(agrupados) == 1:
        conflicto = agrupados[0]
        nombre = _nombre_alumno_conflicto(conflicto)
        destino = _nombre_grupo_horario(grupo_destino)
        numero = conflicto["numero"]
        numero = numero if numero not in (None, "") else "-"
        dias = _texto_dias_conflicto(conflicto["dias"])
        hora_inicio = conflicto["hora_inicio"].strftime("%H:%M")
        hora_fin = conflicto["hora_fin"].strftime("%H:%M")
        return (
            f"No se puede realizar la inscripción de {nombre}. Ya posee una inscripción en "
            f"{conflicto['actividad']} N.° {numero}, {dias} de {hora_inicio} a {hora_fin}, "
            f"y ese horario se superpone con el grupo seleccionado {destino}."
        )

    nombre = _nombre_alumno_conflicto(agrupados[0])
    destino = _nombre_grupo_horario(grupo_destino)
    detalles = "; ".join(
        _detalle_conflicto_horario(conflicto)
        for conflicto in agrupados
    )
    return (
        f"No se puede realizar la inscripción de {nombre}. Ya posee inscripciones cuyos "
        f"horarios se superponen con el grupo seleccionado {destino}: "
        f"{detalles}."
    )


def validar_disponibilidad_horaria_alumno(grupo, alumno):
    """Valida una inscripción contra grupos activos del mismo CEF y ciclo."""

    conflictos = _buscar_conflicto_horario_alumnos(
        alumnos_ids=[alumno.pk],
        grupo_destino_id=grupo.pk,
        ciclo_id=grupo.ciclo_id,
        cueanexo=grupo.cueanexo,
        hora_inicio=grupo.hora_inicio,
        hora_fin=grupo.hora_fin,
        dias_ids=grupo.dias_funcionamiento.values_list(
            "dia_semana_id",
            flat=True,
        ),
    )
    if conflictos:
        conflictos_agrupados = _agrupar_conflictos_horarios(conflictos)
        raise ConflictoHorarioInscripcionError(
            _mensaje_conflicto_horario(
                conflictos,
                grupo_destino=grupo,
            ),
            conflictos_agrupados,
        )


def validar_conflictos_horarios_edicion_grupo(
    grupo,
    *,
    hora_inicio,
    hora_fin,
    dias_ids,
    alumnos_ids,
):
    """Valida en bloque los alumnos activos con el estado propuesto del grupo."""

    conflictos = _buscar_conflicto_horario_alumnos(
        alumnos_ids=alumnos_ids,
        grupo_destino_id=grupo.pk,
        ciclo_id=grupo.ciclo_id,
        cueanexo=grupo.cueanexo,
        hora_inicio=hora_inicio,
        hora_fin=hora_fin,
        dias_ids=dias_ids,
    )
    if conflictos:
        raise ValidationError(
            _mensaje_conflicto_horario(conflictos, edicion=True)
        )


def _max_fecha(*fechas):
    """Devuelve el máximo de fechas conocidas, sin inventar las ausentes."""

    conocidas = [fecha for fecha in fechas if fecha is not None]
    return max(conocidas) if conocidas else None


def _ultimo_cierre(queryset, campo, excluir_pk=None):
    """Lee y bloquea el cierre efectivo más tardío del alcance solicitado."""

    if excluir_pk is not None:
        queryset = queryset.exclude(pk=excluir_pk)
    return (
        queryset.select_for_update()
        .exclude(**{f"{campo}__isnull": True})
        .order_by(f"-{campo}", "-pk")
        .values_list(campo, flat=True)
        .first()
    )


def _inscripciones_alumno_cef(alumno, cueanexo, ciclo):
    return CefInscripcion.objects.filter(
        alumno=alumno,
        grupo__cueanexo=cueanexo,
        grupo__ciclo=ciclo,
    )


def _asignaciones_docente_cef(docente_cuil, cueanexo, ciclo):
    return CefDocenteGrupo.objects.filter(
        docente_cuil=docente_cuil,
        grupo__cueanexo=cueanexo,
        grupo__ciclo=ciclo,
    )


def _fecha_activacion_grupo(grupo):
    """Combina la activación vigente por secuencia y el máximo evento efectivo."""

    fecha_activacion = (
        CefGrupoEstadoMovimiento.objects.select_for_update()
        .filter(grupo=grupo, estado_resultante=CefGrupo.Estado.ACTIVO)
        .order_by("-creado_en", "-pk")
        .values_list("fecha", flat=True)
        .first()
    )
    return _max_fecha(
        fecha_activacion,
        _ultimo_cierre(CefGrupoEstadoMovimiento.objects.filter(grupo=grupo), "fecha"),
    )


def _periodo_alumno_activo(grupo, alumno):
    periodo = (
        CefAlumnoCef.objects.select_for_update()
        .filter(
            cueanexo=grupo.cueanexo,
            ciclo=grupo.ciclo,
            alumno=alumno,
            estado=CefAlumnoCef.Estado.ACTIVO,
        )
        .order_by("pk")
        .first()
    )
    if periodo is None:
        raise ValidationError(
            "El alumno no está activo en el banco de alumnos de este CEF y ciclo. "
            "Reincorporalo antes de inscribirlo."
        )
    return periodo


def _periodo_docente_activo(grupo, docente_cuil):
    periodo = (
        CefDocenteCef.objects.select_for_update()
        .filter(
            cueanexo=grupo.cueanexo,
            ciclo=grupo.ciclo,
            docente_cuil=docente_cuil,
            estado=CefDocenteCef.Estado.ACTIVO,
        )
        .order_by("pk")
        .first()
    )
    if periodo is None:
        raise ValidationError(
            "El profesor no está activo en el banco de profesores de este CEF y ciclo. "
            "Reincorporalo antes de asignarlo."
        )
    return periodo


def _fecha_minima_inscripcion(grupo, alumno, periodo, excluir_pk=None):
    return _max_fecha(
        periodo.fecha_alta,
        _ultimo_cierre(
            CefAlumnoCef.objects.filter(
                cueanexo=grupo.cueanexo, ciclo=grupo.ciclo, alumno=alumno,
            ),
            "fecha_baja",
            excluir_pk=periodo.pk,
        ),
        _ultimo_cierre(
            CefInscripcion.objects.filter(grupo=grupo, alumno=alumno),
            "fecha_baja",
            excluir_pk=excluir_pk,
        ),
        _fecha_activacion_grupo(grupo),
    )


def _fecha_minima_asignacion(grupo, docente_cuil, rol, periodo, excluir_pk=None):
    cierre_rol = None
    if rol in {CefDocenteGrupo.Rol.TITULAR, CefDocenteGrupo.Rol.INTERINO}:
        cierre_rol = _ultimo_cierre(
            CefDocenteGrupo.objects.filter(grupo=grupo, rol=rol),
            "fecha_hasta",
            excluir_pk=excluir_pk,
        )
    return _max_fecha(
        periodo.fecha_alta,
        _ultimo_cierre(
            CefDocenteCef.objects.filter(
                cueanexo=grupo.cueanexo, ciclo=grupo.ciclo,
                docente_cuil=docente_cuil,
            ),
            "fecha_baja",
            excluir_pk=periodo.pk,
        ),
        _ultimo_cierre(
            CefDocenteGrupo.objects.filter(grupo=grupo, docente_cuil=docente_cuil),
            "fecha_hasta",
            excluir_pk=excluir_pk,
        ),
        cierre_rol,
        _fecha_activacion_grupo(grupo),
    )


def asegurar_alumno_banco_activo(alumno, cueanexo, ciclo, user, fecha_alta=None):
    """Devuelve el periodo activo del alumno o crea uno nuevo."""

    try:
        with transaction.atomic():
            ciclo_real = validar_ciclo_escribible(ciclo, user, cueanexo=cueanexo)
            if fecha_alta is not None:
                fecha_alta = validar_fecha_interactiva_ciclo(ciclo_real, fecha_alta)
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

            fecha_minima = _max_fecha(
                *(periodo.fecha_baja for periodo in periodos),
                _ultimo_cierre(
                    _inscripciones_alumno_cef(alumno, cueanexo, ciclo),
                    "fecha_baja",
                ),
            )
            if fecha_alta is None:
                fecha_alta = _max_fecha(
                    fecha_operativa_predeterminada(ciclo_real), fecha_minima,
                )
            fecha_alta = validar_fecha_interactiva_ciclo(
                ciclo_real,
                fecha_alta,
                fecha_minima=fecha_minima,
                mensaje_anterior=(
                    "La fecha de alta no puede ser anterior al último cierre histórico."
                ),
            )
            periodo_activo = CefAlumnoCef.objects.create(
                cueanexo=cueanexo,
                ciclo=ciclo,
                alumno=alumno,
                estado=CefAlumnoCef.Estado.ACTIVO,
                fecha_alta=fecha_alta,
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


def asegurar_docente_banco_activo(docente_cuil, cueanexo, ciclo, user, fecha_alta=None):
    """Devuelve el periodo activo del docente o crea uno nuevo."""

    docente_cuil = solo_digitos(docente_cuil)
    try:
        with transaction.atomic():
            ciclo_real = validar_ciclo_escribible(ciclo, user, cueanexo=cueanexo)
            if fecha_alta is not None:
                fecha_alta = validar_fecha_interactiva_ciclo(ciclo_real, fecha_alta)
            docente_cuil = validar_docente_vinculado_bnh(docente_cuil, cueanexo)

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

            fecha_minima = _max_fecha(
                *(periodo.fecha_baja for periodo in periodos),
                _ultimo_cierre(
                    _asignaciones_docente_cef(docente_cuil, cueanexo, ciclo),
                    "fecha_hasta",
                ),
            )
            if fecha_alta is None:
                fecha_alta = _max_fecha(
                    fecha_operativa_predeterminada(ciclo_real), fecha_minima,
                )
            fecha_alta = validar_fecha_interactiva_ciclo(
                ciclo_real,
                fecha_alta,
                fecha_minima=fecha_minima,
                mensaje_anterior=(
                    "La fecha de alta no puede ser anterior al último cierre histórico."
                ),
            )
            periodo_activo = CefDocenteCef.objects.create(
                cueanexo=cueanexo,
                ciclo=ciclo,
                docente_cuil=docente_cuil,
                estado=CefDocenteCef.Estado.ACTIVO,
                fecha_alta=fecha_alta,
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


def validar_fecha_inscripcion_grupo(
    grupo, fecha_inscripcion, *, fecha_minima=None, fecha_maxima=None,
):
    """Valida la fecha efectiva de incorporación de un alumno a un grupo."""

    return validar_fecha_interactiva_ciclo(
        grupo.ciclo,
        fecha_inscripcion,
        mensaje_requerida="Indicá la fecha de incorporación al grupo.",
        mensaje_invalida="Indicá la fecha de incorporación al grupo.",
        mensaje_anio=(
            "La fecha de incorporación al grupo debe pertenecer al año del ciclo."
        ),
        fecha_minima=fecha_minima,
        fecha_maxima=fecha_maxima,
        mensaje_posterior=(
            "La fecha de incorporación no puede ser posterior a hoy "
            "ni a la primera asistencia registrada."
        ),
        mensaje_anterior=(
            "La fecha de incorporación no puede preceder al banco, "
            "al historial del alumno ni a la activación del grupo."
        ),
    )


def validar_cupo_grupo(grupo, cupo_maximo, *, nueva_inscripcion=False):
    """Se llama con ciclo y grupo bloqueados, antes de guardar o inscribir."""
    if nueva_inscripcion and cupo_maximo is None:
        raise ValidationError(
            "Este grupo todavía no tiene un cupo máximo configurado. "
            "Establecé un cupo para poder inscribir alumnos."
        )
    validar_cupo_maximo(cupo_maximo)
    activos = (
        CefInscripcion.objects.filter(
            grupo=grupo, estado=CefInscripcion.Estado.ACTIVO,
        ).count()
        if grupo.pk else 0
    )
    if nueva_inscripcion and activos >= cupo_maximo:
        raise ValidationError(
            "No se puede inscribir al alumno porque el grupo alcanzó su cupo "
            f"máximo ({activos} de {cupo_maximo} alumnos). Para incorporar otro "
            "alumno, aumentá el cupo o liberá una vacante."
        )
    if not nueva_inscripcion and activos > cupo_maximo:
        raise ValidationError({
            "cupo_maximo": (
                f"No se puede establecer un cupo de {cupo_maximo} alumnos porque "
                f"el grupo tiene {activos} inscripciones activas. El cupo debe "
                "ser igual o superior a esa cantidad."
            )
        })


def crear_inscripcion_activa(
    grupo,
    alumno,
    user,
    fecha_inscripcion=None,
    *,
    incorporar_banco=False,
):
    """Crea una inscripcion activa nueva sin reactivar periodos historicos."""

    try:
        with transaction.atomic():
            validar_ciclo_escribible(grupo.ciclo_id, user, cueanexo=grupo.cueanexo)
            grupo = CefGrupo.objects.select_for_update().get(pk=grupo.pk)
            fecha_inscripcion = validar_fecha_inscripcion_grupo(
                grupo,
                fecha_inscripcion,
            )
            if grupo.estado != CefGrupo.Estado.ACTIVO:
                raise ValidationError(
                    "No se puede inscribir alumnos en un grupo dado de baja."
                )

            validar_cupo_grupo(grupo, grupo.cupo_maximo, nueva_inscripcion=True)
            if incorporar_banco:
                asegurar_alumno_banco_activo(
                    alumno, grupo.cueanexo, grupo.ciclo, user,
                    fecha_alta=fecha_inscripcion,
                )
            periodo = _periodo_alumno_activo(grupo, alumno)
            fecha_inscripcion = validar_fecha_inscripcion_grupo(
                grupo,
                fecha_inscripcion,
                fecha_minima=_fecha_minima_inscripcion(grupo, alumno, periodo),
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


def _fecha_asistencia_inscripcion(inscripcion, *, ultima=False):
    """Obtiene el extremo efectivo de asistencias sin alterar su historia."""

    orden = "-jornada__fecha" if ultima else "jornada__fecha"
    return (
        CefAsistencia.objects.select_for_update()
        .filter(inscripcion=inscripcion)
        .order_by(orden, "pk")
        .values_list("jornada__fecha", flat=True)
        .first()
    )


def editar_inscripcion_activa(inscripcion, user, fecha_inscripcion, observaciones=""):
    """Edita sólo la relación activa, revalidando su historia bajo bloqueo."""

    with transaction.atomic():
        validar_ciclo_escribible(
            inscripcion.grupo.ciclo_id, user, cueanexo=inscripcion.grupo.cueanexo,
        )
        grupo = CefGrupo.objects.select_for_update().get(pk=inscripcion.grupo_id)
        inscripcion = CefInscripcion.objects.select_for_update().get(pk=inscripcion.pk)
        if inscripcion.estado != CefInscripcion.Estado.ACTIVO:
            raise ValidationError("La inscripción histórica no puede editarse.")
        if grupo.estado != CefGrupo.Estado.ACTIVO:
            raise ValidationError("El grupo está dado de baja y no puede editarse.")
        periodo = _periodo_alumno_activo(grupo, inscripcion.alumno)
        fecha_inscripcion = validar_fecha_inscripcion_grupo(
            grupo,
            fecha_inscripcion,
            fecha_minima=_fecha_minima_inscripcion(
                grupo, inscripcion.alumno, periodo, excluir_pk=inscripcion.pk,
            ),
            fecha_maxima=_fecha_asistencia_inscripcion(inscripcion),
        )
        inscripcion.fecha_inscripcion = fecha_inscripcion
        inscripcion.observaciones = observaciones
        inscripcion.actualizado_por = user
        inscripcion.save()
        return inscripcion


def dar_baja_inscripcion(
    inscripcion,
    user,
    motivo_baja,
    fecha_baja=None,
):
    """Finaliza una inscripcion activa sin eliminar ni reactivar filas."""

    with transaction.atomic():
        validar_ciclo_escribible(
            inscripcion.grupo.ciclo_id, user, cueanexo=inscripcion.grupo.cueanexo,
        )
        grupo = CefGrupo.objects.select_for_update().get(pk=inscripcion.grupo_id)
        inscripcion = CefInscripcion.objects.select_for_update().get(
            pk=inscripcion.pk
        )
        if inscripcion.estado != CefInscripcion.Estado.ACTIVO:
            raise ValidationError("La inscripción ya se encuentra dada de baja.")
        motivo_baja = _normalizar_motivo_baja(motivo_baja)

        fecha_minima = _max_fecha(
            inscripcion.fecha_inscripcion,
            _fecha_asistencia_inscripcion(inscripcion, ultima=True),
        )
        if fecha_baja is None:
            fecha_baja = _max_fecha(
                fecha_operativa_predeterminada(grupo.ciclo), fecha_minima,
            )
        fecha_baja = validar_fecha_interactiva_ciclo(
            inscripcion.grupo.ciclo,
            fecha_baja,
            mensaje_anio="La fecha de baja debe pertenecer al año del ciclo.",
            fecha_minima=fecha_minima,
            mensaje_anterior=(
                "La fecha de baja no puede preceder a la incorporación "
                "ni a la última asistencia registrada."
            ),
        )

        inscripcion.estado = CefInscripcion.Estado.BAJA
        inscripcion.fecha_baja = fecha_baja
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
    *,
    incorporar_banco=False,
):
    """Crea una asignacion docente activa nueva."""

    if not fecha_desde:
        raise ValidationError("Debe indicar la fecha de asignación del profesor.")

    docente_cuil = solo_digitos(docente_cuil)
    try:
        with transaction.atomic():
            validar_ciclo_escribible(grupo.ciclo_id, user, cueanexo=grupo.cueanexo)
            grupo = CefGrupo.objects.select_for_update().get(pk=grupo.pk)
            fecha_desde = validar_fecha_interactiva_ciclo(
                grupo.ciclo,
                fecha_desde,
                mensaje_requerida="Debe indicar la fecha de asignación del profesor.",
                mensaje_anio="La fecha de asignación debe pertenecer al año del ciclo.",
            )
            if grupo.estado != CefGrupo.Estado.ACTIVO:
                raise ValidationError(
                    "No se pueden asignar profesores a un grupo dado de baja."
                )

            docente_cuil = validar_docente_vinculado_bnh(
                docente_cuil, grupo.cueanexo,
            )
            asegurar_docente_banco_activo(
                docente_cuil, grupo.cueanexo, grupo.ciclo, user,
                fecha_alta=fecha_desde,
            )
            periodo = _periodo_docente_activo(grupo, docente_cuil)
            fecha_desde = validar_fecha_interactiva_ciclo(
                grupo.ciclo,
                fecha_desde,
                fecha_minima=_fecha_minima_asignacion(
                    grupo, docente_cuil, rol, periodo,
                ),
                mensaje_anterior=(
                    "La fecha de asignación no puede preceder al banco, "
                    "al historial del profesor/rol ni a la activación del grupo."
                ),
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


def editar_asignacion_docente_activa(
    asignacion, user, rol, fecha_desde, observaciones="",
):
    """Edita una asignación activa con los pisos del profesor y del nuevo rol."""

    with transaction.atomic():
        validar_ciclo_escribible(
            asignacion.grupo.ciclo_id, user, cueanexo=asignacion.grupo.cueanexo,
        )
        grupo = CefGrupo.objects.select_for_update().get(pk=asignacion.grupo_id)
        asignacion = CefDocenteGrupo.objects.select_for_update().get(pk=asignacion.pk)
        if asignacion.estado != CefDocenteGrupo.Estado.ACTIVO:
            raise ValidationError("La asignación histórica no puede editarse.")
        if grupo.estado != CefGrupo.Estado.ACTIVO:
            raise ValidationError("El grupo está dado de baja y no puede editarse.")
        validar_docente_vinculado_bnh(asignacion.docente_cuil, grupo.cueanexo)
        periodo = _periodo_docente_activo(grupo, asignacion.docente_cuil)
        fecha_desde = validar_fecha_interactiva_ciclo(
            grupo.ciclo,
            fecha_desde,
            mensaje_requerida="Debe indicar la fecha de asignación del profesor.",
            mensaje_anio="La fecha de asignación debe pertenecer al año del ciclo.",
            fecha_minima=_fecha_minima_asignacion(
                grupo, asignacion.docente_cuil, rol, periodo, excluir_pk=asignacion.pk,
            ),
            mensaje_anterior=(
                "La fecha de asignación no puede preceder al banco, "
                "al historial del profesor/rol ni a la activación del grupo."
            ),
        )
        validar_docente_grupo_activo(
            grupo, asignacion.docente_cuil, rol, excluir_pk=asignacion.pk,
        )
        asignacion.rol = rol
        asignacion.fecha_desde = fecha_desde
        asignacion.observaciones = observaciones
        asignacion.actualizado_por = user
        asignacion.save()
        return asignacion


def dar_baja_asignacion_docente(
    asignacion,
    user,
    motivo_baja,
    fecha_hasta=None,
):
    """Finaliza una asignacion activa sin eliminar la fila historica."""

    with transaction.atomic():
        validar_ciclo_escribible(
            asignacion.grupo.ciclo_id, user, cueanexo=asignacion.grupo.cueanexo,
        )
        asignacion = CefDocenteGrupo.objects.select_for_update().get(
            pk=asignacion.pk
        )
        if asignacion.estado != CefDocenteGrupo.Estado.ACTIVO:
            raise ValidationError("La asignación ya se encuentra dada de baja.")
        motivo_baja = _normalizar_motivo_baja(motivo_baja)

        if fecha_hasta is None:
            fecha_hasta = max(
                fecha_operativa_predeterminada(asignacion.grupo.ciclo),
                asignacion.fecha_desde,
            )
        fecha_hasta = validar_fecha_interactiva_ciclo(
            asignacion.grupo.ciclo,
            fecha_hasta,
            mensaje_anio="La fecha de finalización debe pertenecer al año del ciclo.",
            fecha_minima=asignacion.fecha_desde,
            mensaje_anterior=(
                "La fecha de finalización no puede ser anterior a la fecha de asignación."
            ),
        )

        asignacion.estado = CefDocenteGrupo.Estado.BAJA
        asignacion.fecha_hasta = fecha_hasta
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

    rol = rol or asignacion_origen.rol
    with transaction.atomic():
        validar_ciclo_escribible(
            asignacion_origen.grupo.ciclo_id, user, cueanexo=asignacion_origen.grupo.cueanexo,
        )
        grupo = CefGrupo.objects.select_for_update().get(pk=asignacion_origen.grupo_id)
        validar_docente_vinculado_bnh(
            asignacion_origen.docente_cuil, grupo.cueanexo,
        )
        if fecha_desde is None:
            periodo, _ = asegurar_docente_banco_activo(
                asignacion_origen.docente_cuil, grupo.cueanexo, grupo.ciclo, user,
            )
            fecha_minima = _fecha_minima_asignacion(
                grupo, asignacion_origen.docente_cuil, rol, periodo,
            )
            fecha_desde = validar_fecha_interactiva_ciclo(
                grupo.ciclo,
                _max_fecha(fecha_operativa_predeterminada(grupo.ciclo), fecha_minima),
                fecha_minima=fecha_minima,
            )
        return crear_asignacion_docente_activa(
            grupo=grupo,
            docente_cuil=asignacion_origen.docente_cuil,
            rol=rol,
            user=user,
            fecha_desde=fecha_desde,
        )


def validar_vigencia_historica_grupo(grupo, inicio, fin=None, *, bloquear=False):
    """Rechaza fechas o intervalos que atraviesen una baja efectiva registrada."""

    fin = inicio if fin is None else fin
    movimientos = CefGrupoEstadoMovimiento.objects.filter(grupo=grupo).order_by(
        "fecha", "creado_en", "pk",
    )
    if bloquear:
        movimientos = movimientos.select_for_update()
    baja_pendiente = None
    mensaje = "La fecha o el período corresponde a un intervalo de baja del grupo."
    for movimiento in movimientos:
        if movimiento.estado_resultante == CefGrupo.Estado.BAJA:
            if baja_pendiente is None:
                baja_pendiente = movimiento.fecha
        elif movimiento.estado_resultante == CefGrupo.Estado.ACTIVO:
            if (
                baja_pendiente is not None
                and baja_pendiente < movimiento.fecha
                and inicio < movimiento.fecha
                and fin > baja_pendiente
            ):
                raise ValidationError(mensaje)
            baja_pendiente = None
    if baja_pendiente is not None and fin > baja_pendiente:
        raise ValidationError(mensaje)
    if (
        grupo.estado == CefGrupo.Estado.BAJA
        and grupo.fecha_baja is not None
        and fin > grupo.fecha_baja
    ):
        raise ValidationError(mensaje)


def _validar_contencion_banco(periodos, inicio, fin, mensaje):
    """Exige un único período de banco que cubra ambos extremos inclusivos."""

    periodos = list(periodos.select_for_update().order_by("fecha_alta", "pk"))
    if not any(
        periodo.fecha_alta is not None
        and periodo.fecha_alta <= inicio
        and (periodo.fecha_baja is None or periodo.fecha_baja >= fin)
        for periodo in periodos
    ):
        raise ValidationError(mensaje)


def _validar_periodo_rectificado(
    periodo, inicio, fin, relacionados, campo_inicio, campo_fin,
):
    """Conserva los límites de los vecinos efectivos sin aplicar pisos de alta."""

    clave_original = (getattr(periodo, campo_inicio), periodo.pk)
    vecinos = list(
        relacionados.select_for_update().exclude(pk=periodo.pk)
        .order_by(campo_inicio, "pk")
    )
    for vecino in vecinos:
        fecha_inicio = getattr(vecino, campo_inicio)
        fecha_fin = getattr(vecino, campo_fin)
        if (fecha_inicio, vecino.pk) < clave_original:
            if fecha_fin is None:
                raise ValidationError(
                    "El período anterior permanece abierto y no permite esta rectificación."
                )
            if inicio < fecha_fin:
                raise ValidationError(
                    "La rectificación se superpone con un período anterior. "
                    f"Fecha mínima de inicio: {fecha_fin:%d/%m/%Y}."
                )
        elif fin > fecha_inicio:
            raise ValidationError(
                "La rectificación se superpone con un período posterior. "
                f"Fecha máxima de cierre: {fecha_inicio:%d/%m/%Y}."
            )


def rectificar_inscripcion_historica(
    inscripcion, user, fecha_inscripcion, fecha_baja, motivo_baja="", observaciones="",
):
    """Rectifica un período en baja sin reactivarlo ni modificar su identidad."""

    if not usuario_puede_rectificar_cef(user, cueanexo=inscripcion.grupo.cueanexo):
        raise ValidationError("No tenés permiso para rectificar inscripciones históricas.")
    with transaction.atomic():
        validar_ciclo_escribible(
            inscripcion.grupo.ciclo_id, user, cueanexo=inscripcion.grupo.cueanexo,
        )
        grupo = CefGrupo.objects.select_for_update().get(pk=inscripcion.grupo_id)
        inscripcion = CefInscripcion.objects.select_for_update().get(pk=inscripcion.pk)
        if inscripcion.estado != CefInscripcion.Estado.BAJA:
            raise ValidationError("Sólo se pueden rectificar inscripciones dadas de baja.")
        fecha_inscripcion = validar_fecha_interactiva_ciclo(
            grupo.ciclo, fecha_inscripcion,
            fecha_maxima=_fecha_asistencia_inscripcion(inscripcion),
            mensaje_posterior=(
                "La incorporación no puede ser posterior a hoy ni a la primera asistencia."
            ),
        )
        fecha_baja = validar_fecha_interactiva_ciclo(
            grupo.ciclo, fecha_baja,
            fecha_minima=_max_fecha(
                fecha_inscripcion, _fecha_asistencia_inscripcion(inscripcion, ultima=True),
            ),
            mensaje_anterior=(
                "La baja no puede preceder a la incorporación ni a la última asistencia."
            ),
        )
        _validar_contencion_banco(
            CefAlumnoCef.objects.filter(
                alumno=inscripcion.alumno, cueanexo=grupo.cueanexo, ciclo=grupo.ciclo,
            ),
            fecha_inscripcion, fecha_baja,
            "La inscripción rectificada debe quedar completamente comprendida "
            "dentro de un período válido del alumno en el banco del CEF.",
        )
        validar_vigencia_historica_grupo(
            grupo, fecha_inscripcion, fecha_baja, bloquear=True,
        )
        _validar_periodo_rectificado(
            inscripcion, fecha_inscripcion, fecha_baja,
            CefInscripcion.objects.filter(grupo=grupo, alumno=inscripcion.alumno),
            "fecha_inscripcion", "fecha_baja",
        )
        inscripcion.fecha_inscripcion = fecha_inscripcion
        inscripcion.fecha_baja = fecha_baja
        inscripcion.motivo_baja = _normalizar_motivo_baja(motivo_baja)
        inscripcion.observaciones = observaciones
        inscripcion.actualizado_por = user
        inscripcion.save()
        return inscripcion


def rectificar_asignacion_historica(
    asignacion, user, rol, fecha_desde, fecha_hasta, motivo_baja="", observaciones="",
):
    """Rectifica un período docente cerrado, preservando persona, grupo y estado."""

    if not usuario_puede_rectificar_cef(user, cueanexo=asignacion.grupo.cueanexo):
        raise ValidationError("No tenés permiso para rectificar asignaciones históricas.")
    if rol not in dict(CefDocenteGrupo.Rol.choices):
        raise ValidationError("Seleccioná un rol válido para el profesor.")
    with transaction.atomic():
        validar_ciclo_escribible(
            asignacion.grupo.ciclo_id, user, cueanexo=asignacion.grupo.cueanexo,
        )
        grupo = CefGrupo.objects.select_for_update().get(pk=asignacion.grupo_id)
        asignacion = CefDocenteGrupo.objects.select_for_update().get(pk=asignacion.pk)
        if asignacion.estado != CefDocenteGrupo.Estado.BAJA:
            raise ValidationError("Sólo se pueden rectificar asignaciones dadas de baja.")
        fecha_desde = validar_fecha_interactiva_ciclo(grupo.ciclo, fecha_desde)
        fecha_hasta = validar_fecha_interactiva_ciclo(
            grupo.ciclo, fecha_hasta, fecha_minima=fecha_desde,
            mensaje_anterior="La finalización no puede preceder al inicio de la asignación.",
        )
        _validar_contencion_banco(
            CefDocenteCef.objects.filter(
                docente_cuil=asignacion.docente_cuil,
                cueanexo=grupo.cueanexo, ciclo=grupo.ciclo,
            ),
            fecha_desde, fecha_hasta,
            "La asignación rectificada debe quedar completamente comprendida "
            "dentro de un período válido del profesor en el banco del CEF.",
        )
        validar_vigencia_historica_grupo(
            grupo, fecha_desde, fecha_hasta, bloquear=True,
        )
        filtro = Q(docente_cuil=asignacion.docente_cuil)
        if rol in {CefDocenteGrupo.Rol.TITULAR, CefDocenteGrupo.Rol.INTERINO}:
            filtro |= Q(rol=rol)
        _validar_periodo_rectificado(
            asignacion, fecha_desde, fecha_hasta,
            CefDocenteGrupo.objects.filter(filtro, grupo=grupo),
            "fecha_desde", "fecha_hasta",
        )
        asignacion.rol = rol
        asignacion.fecha_desde = fecha_desde
        asignacion.fecha_hasta = fecha_hasta
        asignacion.motivo_baja = _normalizar_motivo_baja(motivo_baja)
        asignacion.observaciones = observaciones
        asignacion.actualizado_por = user
        asignacion.save()
        return asignacion


def dar_baja_alumno_banco(alumno_cef, user, motivo_baja, fecha_baja=None):
    """Finaliza un periodo del banco si no conserva inscripciones activas."""

    with transaction.atomic():
        validar_ciclo_escribible(alumno_cef.ciclo_id, user, cueanexo=alumno_cef.cueanexo)
        alumno_cef = CefAlumnoCef.objects.select_for_update().get(pk=alumno_cef.pk)
        if alumno_cef.estado != CefAlumnoCef.Estado.ACTIVO:
            raise ValidationError("El alumno ya se encuentra dado de baja del banco de alumnos del CEF.")
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

        fecha_minima = _max_fecha(
            alumno_cef.fecha_alta,
            _ultimo_cierre(
                _inscripciones_alumno_cef(
                    alumno_cef.alumno, alumno_cef.cueanexo, alumno_cef.ciclo,
                ),
                "fecha_baja",
            ),
        )
        if fecha_baja is None:
            fecha_baja = _max_fecha(
                fecha_operativa_predeterminada(alumno_cef.ciclo), fecha_minima,
            )
        fecha_baja = validar_fecha_interactiva_ciclo(
            alumno_cef.ciclo,
            fecha_baja,
            mensaje_anio="La fecha de baja debe pertenecer al año del ciclo.",
            fecha_minima=fecha_minima,
            mensaje_anterior=(
                "La fecha de baja no puede preceder al alta ni al cierre "
                "de las relaciones históricas del banco."
            ),
        )

        alumno_cef.estado = CefAlumnoCef.Estado.BAJA
        alumno_cef.fecha_baja = fecha_baja
        alumno_cef.motivo_baja = motivo_baja
        alumno_cef.actualizado_por = user
        alumno_cef.save()
        return alumno_cef


def dar_baja_docente_banco(docente_cef, user, motivo_baja, fecha_baja=None):
    """Finaliza un periodo del banco si no conserva asignaciones activas."""

    with transaction.atomic():
        validar_ciclo_escribible(docente_cef.ciclo_id, user, cueanexo=docente_cef.cueanexo)
        docente_cef = CefDocenteCef.objects.select_for_update().get(pk=docente_cef.pk)
        if docente_cef.estado != CefDocenteCef.Estado.ACTIVO:
            raise ValidationError("El profesor ya se encuentra dado de baja del banco de profesores del CEF.")
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

        fecha_minima = _max_fecha(
            docente_cef.fecha_alta,
            _ultimo_cierre(
                _asignaciones_docente_cef(
                    docente_cef.docente_cuil, docente_cef.cueanexo, docente_cef.ciclo,
                ),
                "fecha_hasta",
            ),
        )
        if fecha_baja is None:
            fecha_baja = _max_fecha(
                fecha_operativa_predeterminada(docente_cef.ciclo), fecha_minima,
            )
        fecha_baja = validar_fecha_interactiva_ciclo(
            docente_cef.ciclo,
            fecha_baja,
            mensaje_anio="La fecha de baja debe pertenecer al año del ciclo.",
            fecha_minima=fecha_minima,
            mensaje_anterior=(
                "La fecha de baja no puede preceder al alta ni al cierre "
                "de las relaciones históricas del banco."
            ),
        )

        docente_cef.estado = CefDocenteCef.Estado.BAJA
        docente_cef.fecha_baja = fecha_baja
        docente_cef.motivo_baja = motivo_baja
        docente_cef.actualizado_por = user
        docente_cef.save()
        return docente_cef


def validar_estructura_grupo_con_historia(grupo_original, grupo_propuesto, dias_ids):
    """Preserva la actividad que identifica a un grupo con historia operativa."""

    if grupo_original.actividad_id == grupo_propuesto.actividad_id:
        return
    tiene_historia = (
        grupo_original.estado == CefGrupo.Estado.BAJA
        or CefInscripcion.objects.filter(grupo=grupo_original).exists()
        or CefDocenteGrupo.objects.filter(grupo=grupo_original).exists()
        or CefGrupoEstadoMovimiento.objects.filter(grupo=grupo_original).exists()
        or CefJornadaAsistencia.objects.filter(grupo=grupo_original).exists()
    )
    if tiene_historia:
        raise ValidationError(
            "La actividad no puede modificarse porque el grupo ya posee historial "
            "operativo. Si corresponde otra actividad, debe utilizarse otro grupo."
        )


def _fecha_minima_transicion_grupo(grupo):
    """Conserva el orden de movimientos y cierres efectivos registrados."""

    return _max_fecha(
        _ultimo_cierre(CefGrupoEstadoMovimiento.objects.filter(grupo=grupo), "fecha"),
        grupo.fecha_baja,
        _ultimo_cierre(CefInscripcion.objects.filter(grupo=grupo), "fecha_baja"),
        _ultimo_cierre(CefDocenteGrupo.objects.filter(grupo=grupo), "fecha_hasta"),
    )


def dar_baja_grupo(grupo, user, motivo_baja, fecha_baja=None):
    """Registra la baja actual de un grupo vacío y conserva su transición."""

    with transaction.atomic():
        validar_ciclo_escribible(grupo.ciclo_id, user, cueanexo=grupo.cueanexo)
        grupo = CefGrupo.objects.select_for_update().get(pk=grupo.pk)
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

        fecha_minima = _fecha_minima_transicion_grupo(grupo)
        if fecha_baja is None:
            fecha_baja = _max_fecha(
                fecha_operativa_predeterminada(grupo.ciclo), fecha_minima,
            )
        fecha_baja = validar_fecha_interactiva_ciclo(
            grupo.ciclo,
            fecha_baja,
            mensaje_anio="La fecha de baja debe pertenecer al año del ciclo.",
            fecha_minima=fecha_minima,
            mensaje_anterior=(
                "La fecha de baja no puede preceder al último evento efectivo del grupo."
            ),
        )
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
        validar_ciclo_escribible(grupo.ciclo_id, user, cueanexo=grupo.cueanexo)
        grupo = CefGrupo.objects.select_for_update().get(pk=grupo.pk)
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

        fecha_minima = _fecha_minima_transicion_grupo(grupo)
        if fecha_reactivacion is None:
            fecha_reactivacion = _max_fecha(
                fecha_operativa_predeterminada(grupo.ciclo), fecha_minima,
            )
        fecha_reactivacion = validar_fecha_interactiva_ciclo(
            grupo.ciclo,
            fecha_reactivacion,
            mensaje_anio="La fecha de reactivación debe pertenecer al año del ciclo.",
            fecha_minima=fecha_minima,
            mensaje_anterior=(
                "La fecha de reactivación no puede preceder a la baja "
                "ni al último evento efectivo del grupo."
            ),
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