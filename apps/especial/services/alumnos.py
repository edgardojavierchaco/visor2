# apps/especial/services/alumnos.py
# -*- coding: utf-8 -*-

import logging

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from ..models import (
    PADRON_DB_ALIAS,
    AlumnoSeccion,
    EspecialAlumnoBanco,
    EspecialPadronOferta,
    SeccionEspecial,
    cueanexo_tiene_oferta_no_especial,
    cueanexo_tiene_oferta_matricula_compartida,
    get_establecimientos_no_especiales_matricula_queryset,
    normalizar_cueanexo,
)


logger = logging.getLogger(__name__)


def obtener_alumno_banco_autorizado(alumno_banco_queryset, alumno_banco_id, *, for_update=False):
    """Obtiene un banco únicamente dentro del queryset autorizado recibido."""
    queryset = alumno_banco_queryset
    if for_update:
        queryset = queryset.select_for_update()
    return queryset.get(pk=alumno_banco_id)


def bloquear_alumno_banco_activo(
    *,
    alumno,
    cueanexo,
    ciclo,
    alumno_banco_queryset,
):
    """Bloquea los periodos autorizados del alumno y devuelve el activo actual."""
    alumno_id = getattr(alumno, "pk", alumno)
    ciclo_id = getattr(ciclo, "pk", ciclo)
    bancos = list(
        alumno_banco_queryset.select_for_update()
        .filter(
            alumno_id=alumno_id,
            cueanexo=cueanexo,
            ciclo_id=ciclo_id,
        )
        .order_by("-pk")
    )
    banco_activo = next(
        (
            banco
            for banco in bancos
            if banco.estado == EspecialAlumnoBanco.Estado.ACTIVO
        ),
        None,
    )
    if not banco_activo:
        raise ValidationError(
            "El alumno no está activo en el banco de este establecimiento y ciclo."
        )
    return banco_activo


def dar_baja_alumno_banco(
    *,
    alumno_banco,
    user,
    motivo_baja,
    alumno_banco_queryset,
):
    """Da de baja el banco autorizado sin alterar sus inscripciones históricas."""
    with transaction.atomic():
        alumno_banco_bloqueado = obtener_alumno_banco_autorizado(
            alumno_banco_queryset,
            alumno_banco.pk,
            for_update=True,
        )
        if alumno_banco_bloqueado.estado != EspecialAlumnoBanco.Estado.ACTIVO:
            raise ValidationError(
                "El alumno ya no se encuentra activo en este establecimiento y ciclo."
            )

        motivo = (motivo_baja or "").strip()
        if not motivo:
            raise ValidationError("Debe indicar el motivo de la baja.")

        motivo_field = EspecialAlumnoBanco._meta.get_field("motivo_baja")
        if motivo_field.max_length and len(motivo) > motivo_field.max_length:
            raise ValidationError(
                f"El motivo de baja no puede superar los {motivo_field.max_length} caracteres."
            )

        tiene_inscripciones_activas = AlumnoSeccion.objects.filter(
            alumno_id=alumno_banco_bloqueado.alumno_id,
            seccion__cueanexo=alumno_banco_bloqueado.cueanexo,
            seccion__ciclo_id=alumno_banco_bloqueado.ciclo_id,
            estado=AlumnoSeccion.Estado.ACTIVO,
        ).exists()
        if tiene_inscripciones_activas:
            raise ValidationError(
                "No se puede dar de baja al alumno del banco mientras tenga "
                "inscripciones activas en este establecimiento y ciclo. Primero "
                "debe dar de baja esas inscripciones desde la gestión de secciones."
            )

        alumno_banco_bloqueado.estado = EspecialAlumnoBanco.Estado.BAJA
        alumno_banco_bloqueado.fecha_baja = timezone.localdate()
        alumno_banco_bloqueado.motivo_baja = motivo
        fields = {
            field.name for field in EspecialAlumnoBanco._meta.concrete_fields
        }
        update_fields = [
            "estado",
            "fecha_baja",
            "motivo_baja",
        ]
        if "actualizado_por" in fields:
            alumno_banco_bloqueado.actualizado_por = user
            update_fields.append("actualizado_por")
        if "actualizado_en" in fields:
            update_fields.append("actualizado_en")
        alumno_banco_bloqueado.save(update_fields=update_fields)
        return alumno_banco_bloqueado


def _establecimiento_para_cue(cueanexo, padron_queryset=None):
    """Devuelve el nombre de un establecimiento no Especial vigente."""
    queryset = get_establecimientos_no_especiales_matricula_queryset(
        _padron_queryset(padron_queryset)
    )
    for campo in ("cueanexo", "padron_cueanexo"):
        nombre = (
            queryset.filter(**{campo: cueanexo})
            .exclude(nom_est__isnull=True)
            .exclude(nom_est__exact="")
            .values_list("nom_est", flat=True)
            .order_by("nom_est")
            .first()
        )
        if nombre:
            return nombre
    return ""


def _cue_anexo_existe(cueanexo, padron_queryset=None):
    queryset = _padron_queryset(padron_queryset)
    return any(
        queryset.filter(**{campo: cueanexo}).exists()
        for campo in ("cueanexo", "padron_cueanexo")
    )


def ultima_matricula_compartida(alumno, *, excluir_cueanexo="", padron_queryset=None):
    """Obtiene la última relación persistida como sugerencia, no como alta automática."""
    alumno_id = getattr(alumno, "pk", alumno)
    excluir_cueanexo = normalizar_cueanexo(excluir_cueanexo)
    queryset = (
        EspecialAlumnoBanco.objects.filter(
            alumno_id=alumno_id,
        )
        .exclude(matricula_compartida__isnull=True)
        .exclude(matricula_compartida__exact="")
        .select_related("ciclo")
        .order_by("-ciclo__anio", "-actualizado_en", "-pk")
    )
    for banco in queryset:
        cue = normalizar_cueanexo(banco.matricula_compartida)
        if not cue or cue == excluir_cueanexo:
            continue
        if not cueanexo_tiene_oferta_no_especial(cue, padron_queryset):
            continue
        establecimiento = _establecimiento_para_cue(cue, padron_queryset)
        if establecimiento:
            return {
                "cueanexo": cue,
                "establecimiento": establecimiento,
                "ciclo": getattr(banco.ciclo, "anio", ""),
                "banco_id": banco.pk,
            }
    return None


def _inscripciones_activas_alumno_ciclo(alumno_id, ciclo_id, *, using):
    return list(
        AlumnoSeccion.objects.using(using)
        .select_for_update()
        .select_related("seccion")
        .filter(
            alumno_id=alumno_id,
            seccion__ciclo_id=ciclo_id,
            estado=AlumnoSeccion.Estado.ACTIVO,
            seccion__estado=SeccionEspecial.Estado.ACTIVO,
        )
        .order_by("pk")
    )


def validar_matricula_compartida_seccion(
    *,
    alumno,
    seccion,
    cueanexo_asociado,
    padron_queryset=None,
):
    """Valida únicamente el dato de matrícula compartida seleccionado."""
    cue_destino = normalizar_cueanexo(seccion.cueanexo)
    cue_asociado = normalizar_cueanexo(cueanexo_asociado)
    if not cue_asociado:
        raise ValidationError(
            "Esta sección de Integración requiere indicar el CUE-Anexo asociado."
        )
    if cue_asociado == cue_destino:
        raise ValidationError(
            "El CUE-Anexo asociado no puede ser el mismo que el de la sección de Integración."
        )
    if not _cue_anexo_existe(cue_asociado, padron_queryset):
        raise ValidationError("El CUE-Anexo asociado no existe.")
    if not cueanexo_tiene_oferta_no_especial(cue_asociado, padron_queryset):
        raise ValidationError(
            "El CUE-Anexo asociado no corresponde a un establecimiento no Especial vigente."
        )

    return {"cueanexo": cue_asociado}


def _validar_inscripciones_para_seccion(
    *,
    alumno,
    seccion,
    inscripciones=None,
):
    """Aplica las reglas de duplicidad antes de crear la inscripción."""
    alumno_id = getattr(alumno, "pk", alumno)
    cue_destino = normalizar_cueanexo(seccion.cueanexo)
    inscripciones = inscripciones if inscripciones is not None else []
    for inscripcion in inscripciones:
        cue_actual = normalizar_cueanexo(inscripcion.seccion.cueanexo)
        if inscripcion.seccion_id == seccion.pk:
            raise ValidationError("El alumno ya se encuentra inscripto en esta sección.")
        if cue_actual == cue_destino:
            nombre = inscripcion.seccion.nombre_seccion
            raise ValidationError(
                f"El alumno ya está inscripto en otra sección del mismo CUE-Anexo "
                f"({nombre}, {cue_destino})."
            )
        if not seccion.es_oferta_integracion:
            raise ValidationError(
                f"El alumno ya está inscripto en otra sección "
                f"({inscripcion.seccion.nombre_seccion}, {cue_actual}). "
                "Una sección que no es Integración no puede tener una segunda inscripción activa."
            )
    return alumno_id


def inscribir_alumno_en_seccion(
    *,
    alumno,
    seccion,
    user,
    cueanexo_asociado=None,
    padron_queryset=None,
):
    """Crea/reactiva banco e inscripción desde una sección en una única transacción."""
    alumno_id = getattr(alumno, "pk", alumno)
    if not alumno_id:
        raise ValidationError("El alumno seleccionado no es válido.")
    using = EspecialAlumnoBanco.objects.db

    logger.info(
        "Servicio inscripción Especial: seccion_id=%s cue_asociado_recibido=%s cuil=%s",
        getattr(seccion, "pk", None),
        normalizar_cueanexo(cueanexo_asociado),
        getattr(alumno, "cuil", ""),
    )

    with transaction.atomic(using=using):
        seccion_bloqueada = (
            SeccionEspecial.objects.using(using)
            .select_for_update()
            .select_related("ciclo")
            .get(pk=seccion.pk)
        )
        if seccion_bloqueada.estado != SeccionEspecial.Estado.ACTIVO:
            raise ValidationError("La sección no está activa.")

        logger.info(
            "Servicio inscripción Especial contexto real: seccion_id=%s cue_especial=%s "
            "ciclo_id=%s integracion=%s",
            seccion_bloqueada.pk,
            seccion_bloqueada.cueanexo,
            seccion_bloqueada.ciclo_id,
            seccion_bloqueada.es_oferta_integracion,
        )

        alumno_bloqueado = _bloquear_alumno(alumno_id, using=using)
        bancos = _bancos_del_alumno_ciclo(alumno_id, seccion_bloqueada.ciclo_id, using=using)
        bancos_activos = [
            banco for banco in bancos
            if banco.estado == EspecialAlumnoBanco.Estado.ACTIVO
        ]
        inscripciones = _inscripciones_activas_alumno_ciclo(
            alumno_id,
            seccion_bloqueada.ciclo_id,
            using=using,
        )
        cue_asociado = None
        if seccion_bloqueada.es_oferta_integracion:
            relacion = validar_matricula_compartida_seccion(
                alumno=alumno_bloqueado,
                seccion=seccion_bloqueada,
                cueanexo_asociado=cueanexo_asociado,
                padron_queryset=padron_queryset,
            )
            cue_asociado = relacion["cueanexo"]
        elif cueanexo_asociado not in (None, ""):
            raise ValidationError(
                "Una sección que no es Integración no acepta matrícula compartida."
            )

        _validar_inscripciones_para_seccion(
            alumno=alumno_bloqueado,
            seccion=seccion_bloqueada,
            inscripciones=inscripciones,
        )

        cue_destino = normalizar_cueanexo(seccion_bloqueada.cueanexo)
        if not seccion_bloqueada.es_oferta_integracion:
            bancos_de_otro_cue = [
                banco for banco in bancos_activos
                if normalizar_cueanexo(banco.cueanexo) != cue_destino
            ]
        else:
            bancos_de_otro_cue = []
        if bancos_de_otro_cue:
            cues_de_otro_banco = sorted({
                normalizar_cueanexo(banco.cueanexo)
                for banco in bancos_de_otro_cue
            })
            raise ValidationError(
                "El alumno ya tiene un banco activo en otro CUE-Anexo "
                f"({', '.join(cues_de_otro_banco)})."
            )

        banco_destino = next(
            (
                banco for banco in bancos_activos
                if normalizar_cueanexo(banco.cueanexo)
                == normalizar_cueanexo(seccion_bloqueada.cueanexo)
            ),
            None,
        )
        if banco_destino is None:
            banco_destino = EspecialAlumnoBanco(
                cueanexo=seccion_bloqueada.cueanexo,
                ciclo_id=seccion_bloqueada.ciclo_id,
                alumno=alumno_bloqueado,
                estado=EspecialAlumnoBanco.Estado.ACTIVO,
                matricula_compartida=cue_asociado,
                creado_por=user,
                actualizado_por=user,
            )
            banco_destino.save()
        elif seccion_bloqueada.es_oferta_integracion:
            existente = normalizar_cueanexo(banco_destino.matricula_compartida)
            if existente != cue_asociado:
                banco_destino.matricula_compartida = cue_asociado
                banco_destino.actualizado_por = user
                banco_destino.save(update_fields=["matricula_compartida", "actualizado_por", "actualizado_en"])

        inscripcion_activa = next(
            (
                inscripcion for inscripcion in inscripciones
                if inscripcion.seccion_id == seccion_bloqueada.pk
            ),
            None,
        )
        if inscripcion_activa:
            raise ValidationError("El alumno ya se encuentra inscripto en esta sección.")

        inscripcion_baja = (
            AlumnoSeccion.objects.using(using)
            .select_for_update()
            .filter(
                seccion_id=seccion_bloqueada.pk,
                alumno_id=alumno_id,
                estado=AlumnoSeccion.Estado.BAJA,
            )
            .order_by("-pk")
            .first()
        )
        if inscripcion_baja:
            inscripcion_baja.estado = AlumnoSeccion.Estado.ACTIVO
            inscripcion_baja.fecha_baja = None
            inscripcion_baja.motivo_baja = ""
            inscripcion_baja.actualizado_por = user
            inscripcion_baja.save(update_fields=[
                "estado", "fecha_baja", "motivo_baja", "actualizado_por", "actualizado_en"
            ])
            return inscripcion_baja, False, banco_destino

        total_activos = AlumnoSeccion.objects.using(using).filter(
            seccion_id=seccion_bloqueada.pk,
            estado=AlumnoSeccion.Estado.ACTIVO,
        ).count()
        if total_activos >= seccion_bloqueada.capacidad_total:
            raise ValidationError("No se puede inscribir: la sección alcanzó su capacidad máxima.")

        inscripcion = AlumnoSeccion.objects.using(using).create(
            seccion=seccion_bloqueada,
            alumno=alumno_bloqueado,
            estado=AlumnoSeccion.Estado.ACTIVO,
            creado_por=user,
            actualizado_por=user,
        )
        return inscripcion, True, banco_destino


def dar_baja_inscripcion_y_matricula_compartida(inscripcion, user, *, motivo_baja="Baja desde gestión"):
    """Da de baja la inscripción y desactiva su relación compartida sin tocar la contraparte."""
    using = EspecialAlumnoBanco.objects.db
    with transaction.atomic(using=using):
        inscripcion_bloqueada = (
            AlumnoSeccion.objects.using(using)
            .select_for_update()
            .select_related("seccion", "seccion__ciclo")
            .get(pk=inscripcion.pk)
        )
        if inscripcion_bloqueada.estado == AlumnoSeccion.Estado.BAJA:
            raise ValidationError("La inscripción ya está dada de baja.")

        inscripcion_bloqueada.estado = AlumnoSeccion.Estado.BAJA
        inscripcion_bloqueada.fecha_baja = timezone.localdate()
        inscripcion_bloqueada.motivo_baja = (motivo_baja or "Baja desde gestión").strip()
        inscripcion_bloqueada.actualizado_por = user
        inscripcion_bloqueada.save(update_fields=[
            "estado", "fecha_baja", "motivo_baja", "actualizado_por", "actualizado_en"
        ])

        seccion = inscripcion_bloqueada.seccion
        if not seccion.es_oferta_integracion:
            return inscripcion_bloqueada

        otras_integracion = [
            otra for otra in _inscripciones_activas_alumno_ciclo(
                inscripcion_bloqueada.alumno_id,
                seccion.ciclo_id,
                using=using,
            )
            if otra.seccion_id != seccion.pk
            and normalizar_cueanexo(otra.seccion.cueanexo)
            == normalizar_cueanexo(seccion.cueanexo)
            and otra.seccion.es_oferta_integracion
        ]
        if otras_integracion:
            return inscripcion_bloqueada

        banco = (
            EspecialAlumnoBanco.objects.using(using)
            .select_for_update()
            .filter(
                alumno_id=inscripcion_bloqueada.alumno_id,
                cueanexo=seccion.cueanexo,
                ciclo_id=seccion.ciclo_id,
                estado=EspecialAlumnoBanco.Estado.ACTIVO,
            )
            .order_by("-pk")
            .first()
        )
        if banco is not None and banco.matricula_compartida:
            historial = EspecialAlumnoBanco(
                cueanexo=banco.cueanexo,
                ciclo_id=banco.ciclo_id,
                alumno_id=banco.alumno_id,
                estado=EspecialAlumnoBanco.Estado.BAJA,
                fecha_alta=banco.fecha_alta,
                fecha_baja=timezone.localdate(),
                motivo_baja=f"Matrícula compartida finalizada: {inscripcion_bloqueada.motivo_baja}",
                matricula_compartida=banco.matricula_compartida,
                alumno_nombre_snapshot=banco.alumno_nombre_snapshot,
                alumno_documento_snapshot=banco.alumno_documento_snapshot,
                alumno_cuil_snapshot=banco.alumno_cuil_snapshot,
                observaciones=banco.observaciones,
                creado_por=user,
                actualizado_por=user,
            )
            historial.save()
            banco.matricula_compartida = None
            banco.actualizado_por = user
            banco.save(update_fields=["matricula_compartida", "actualizado_por", "actualizado_en"])
        return inscripcion_bloqueada


def _padron_queryset(padron_queryset=None):
    if padron_queryset is not None:
        return padron_queryset
    return EspecialPadronOferta.objects.using(PADRON_DB_ALIAS)


def _normalizar_matricula_solicitada(valor):
    if valor is None or not str(valor).strip():
        return None
    matricula = normalizar_cueanexo(valor)
    if not matricula:
        raise ValidationError(
            "El CUE-Anexo de matrícula compartida debe tener 9 dígitos."
        )
    return matricula


def _matricula_guardada(banco):
    valor = getattr(banco, "matricula_compartida", None)
    if valor == "":
        raise ValidationError(
            "El banco tiene una matrícula compartida vacía; debe corregirse a NULL."
        )
    if valor is None:
        return None
    matricula = normalizar_cueanexo(valor)
    if not matricula or matricula != str(valor):
        raise ValidationError(
            "La matrícula compartida guardada no está normalizada."
        )
    return matricula


def _validar_banco_proyectado(
    *,
    cueanexo,
    matricula_compartida,
    padron_queryset,
    oferta_cache,
):
    cueanexo = normalizar_cueanexo(cueanexo)
    if not cueanexo:
        raise ValidationError("El CUE-Anexo del banco es inválido.")

    if cueanexo not in oferta_cache:
        oferta_cache[cueanexo] = cueanexo_tiene_oferta_matricula_compartida(cueanexo)
    tiene_integracion = oferta_cache[cueanexo]

    if tiene_integracion:
        if not matricula_compartida:
            return cueanexo, None
        if matricula_compartida == cueanexo:
            raise ValidationError(
                "El CUE-Anexo asociado no puede ser igual al CUE-Anexo actual."
            )
        if not cueanexo_tiene_oferta_no_especial(
            matricula_compartida,
            padron_queryset,
        ):
            raise ValidationError(
                "El CUE-Anexo asociado debe existir en el padrón y tener al menos una oferta vigente no Especial."
            )
    elif matricula_compartida is not None:
        raise ValidationError(
            "El CUE-Anexo sin oferta Integración no puede tener matrícula compartida."
        )

    return cueanexo, matricula_compartida


def _validar_bancos_activos(
    bancos,
    *,
    padron_queryset,
    oferta_cache=None,
    reemplazos=None,
):
    if len(bancos) > 2:
        raise ValidationError(
            "El alumno no puede tener más de dos bancos activos en el mismo ciclo."
        )

    oferta_cache = oferta_cache if oferta_cache is not None else {}
    reemplazos = reemplazos or {}
    estados = []
    for banco in bancos:
        cueanexo_guardado = getattr(banco, "cueanexo", None)
        cueanexo_normalizado = normalizar_cueanexo(cueanexo_guardado)
        if not cueanexo_normalizado or str(cueanexo_guardado) != cueanexo_normalizado:
            raise ValidationError(
                "El CUE-Anexo guardado del banco no está normalizado."
            )
        matricula = (
            reemplazos[banco.pk]
            if banco.pk in reemplazos
            else _matricula_guardada(banco)
        )
        cueanexo, matricula = _validar_banco_proyectado(
            cueanexo=banco.cueanexo,
            matricula_compartida=matricula,
            padron_queryset=padron_queryset,
            oferta_cache=oferta_cache,
        )
        estados.append((cueanexo, matricula))

    if len(estados) == 2:
        cues = {cueanexo for cueanexo, _ in estados}
        if len(cues) != 2:
            raise ValidationError(
                "Los bancos activos del alumno deben pertenecer a CUE-Anexos distintos."
            )
        matriculas = [matricula for _, matricula in estados]
        cues_integracion = {
            cueanexo
            for cueanexo, _ in estados
            if oferta_cache.get(cueanexo, False)
        }

        if len(cues_integracion) == 2:
            # Dos CUE-Anexos con oferta Integración pueden compartir el mismo
            # CUE-Anexo común de matrícula. La matrícula no debe apuntar al
            # otro CUE de Integración.
            matriculas_presentes = [matricula for matricula in matriculas if matricula]
            if matriculas_presentes and any(
                matricula != matriculas_presentes[0]
                for matricula in matriculas_presentes
            ):
                raise ValidationError(
                    "Los bancos de Integración del alumno deben compartir el mismo CUE-Anexo de educación común."
                )
        else:
            if not any(matriculas):
                raise ValidationError(
                    "Dos bancos activos deben estar relacionados por matrícula compartida."
                )
            for cueanexo, matricula in estados:
                if matricula is not None and matricula not in cues - {cueanexo}:
                    raise ValidationError(
                        "La matrícula compartida debe apuntar al otro CUE-Anexo activo."
                    )

    return estados


def _bloquear_alumno(alumno_id, *, using):
    alumno_model = EspecialAlumnoBanco._meta.get_field("alumno").remote_field.model
    return alumno_model.objects.using(using).select_for_update().get(pk=alumno_id)


def _bancos_del_alumno_ciclo(alumno_id, ciclo_id, *, using):
    return list(
        EspecialAlumnoBanco.objects.using(using)
        .select_for_update()
        .filter(alumno_id=alumno_id, ciclo_id=ciclo_id)
        .order_by("pk")
    )


def asegurar_alumno_banco(
    *,
    alumno,
    cueanexo,
    ciclo,
    user,
    matricula_compartida=None,
    padron_queryset=None,
    validar_relacion=True,
):
    """Crea de forma idempotente un banco respetando la matrícula compartida."""
    alumno_id = getattr(alumno, "pk", alumno)
    ciclo_id = getattr(ciclo, "pk", ciclo)
    cueanexo = normalizar_cueanexo(cueanexo)
    if not alumno_id:
        raise ValidationError("El alumno seleccionado no es válido.")
    if not cueanexo or not ciclo_id:
        raise ValidationError("El CUE-Anexo y el ciclo lectivo son obligatorios.")

    matricula_compartida = _normalizar_matricula_solicitada(matricula_compartida)
    padron_queryset = _padron_queryset(padron_queryset)
    using = EspecialAlumnoBanco.objects.db

    with transaction.atomic(using=using):
        alumno_bloqueado = _bloquear_alumno(alumno_id, using=using)
        bancos = _bancos_del_alumno_ciclo(alumno_id, ciclo_id, using=using)
        bancos_activos = [
            banco
            for banco in bancos
            if banco.estado == EspecialAlumnoBanco.Estado.ACTIVO
        ]
        bancos_de_otro_cue = [
            banco
            for banco in bancos_activos
            if banco.cueanexo != cueanexo
        ]
        if bancos_de_otro_cue:
            cues_activos = sorted(
                {normalizar_cueanexo(banco.cueanexo) for banco in bancos_de_otro_cue}
            )
            cues_activos = [cue for cue in cues_activos if cue]
            if len(cues_activos) == 1:
                detalle_cue = f"el CUE-Anexo {cues_activos[0]}"
                instruccion_baja = "ese CUE-Anexo"
            else:
                detalle_cue = "los CUE-Anexos " + ", ".join(cues_activos)
                instruccion_baja = "esos CUE-Anexos"
            raise ValidationError(
                f"El alumno ya está activo en {detalle_cue}. Primero debe "
                f"darlo de baja de {instruccion_baja} antes de agregarlo a otra escuela."
            )
        oferta_cache = {}
        if validar_relacion:
            _validar_bancos_activos(
                bancos_activos,
                padron_queryset=padron_queryset,
                oferta_cache=oferta_cache,
            )
            _validar_banco_proyectado(
                cueanexo=cueanexo,
                matricula_compartida=matricula_compartida,
                padron_queryset=padron_queryset,
                oferta_cache=oferta_cache,
            )

        existente = next(
            (banco for banco in bancos_activos if banco.cueanexo == cueanexo),
            None,
        )
        if existente is not None:
            if _matricula_guardada(existente) != matricula_compartida:
                if not validar_relacion and matricula_compartida is None:
                    return existente, False
                raise ValidationError(
                    "El alumno ya está activo en este CUE-Anexo; use la actualización explícita "
                    "de matrícula compartida para modificarlo."
                )
            return existente, False

        banco = EspecialAlumnoBanco(
            cueanexo=cueanexo,
            ciclo_id=ciclo_id,
            alumno=alumno_bloqueado,
            estado=EspecialAlumnoBanco.Estado.ACTIVO,
            matricula_compartida=matricula_compartida,
            creado_por=user,
            actualizado_por=user,
        )
        if validar_relacion:
            _validar_bancos_activos(
                bancos_activos + [banco],
                padron_queryset=padron_queryset,
                oferta_cache=oferta_cache,
            )
        banco.save()
        return banco, True


def actualizar_matricula_compartida(
    *,
    alumno_banco,
    user,
    matricula_compartida,
    alumno_banco_queryset,
    padron_queryset=None,
):
    """Actualiza un banco autorizado validando el estado completo del alumno."""
    alumno_id = getattr(alumno_banco, "alumno_id", None)
    ciclo_id = getattr(alumno_banco, "ciclo_id", None)
    if not alumno_id or not ciclo_id:
        raise ValidationError("El banco de alumno no es válido.")

    matricula_compartida = _normalizar_matricula_solicitada(matricula_compartida)
    padron_queryset = _padron_queryset(padron_queryset)
    using = getattr(alumno_banco_queryset, "db", None) or EspecialAlumnoBanco.objects.db

    with transaction.atomic(using=using):
        _bloquear_alumno(alumno_id, using=using)
        banco_bloqueado = obtener_alumno_banco_autorizado(
            alumno_banco_queryset,
            alumno_banco.pk,
            for_update=True,
        )
        if banco_bloqueado.estado != EspecialAlumnoBanco.Estado.ACTIVO:
            raise ValidationError("El alumno ya no se encuentra activo en este banco.")

        bancos = _bancos_del_alumno_ciclo(alumno_id, ciclo_id, using=using)
        bancos_activos = [
            banco
            for banco in bancos
            if banco.estado == EspecialAlumnoBanco.Estado.ACTIVO
        ]
        if not any(banco.pk == banco_bloqueado.pk for banco in bancos_activos):
            raise ValidationError("El banco no está activo para este alumno y ciclo.")

        oferta_cache = {}
        _validar_bancos_activos(
            bancos_activos,
            padron_queryset=padron_queryset,
            oferta_cache=oferta_cache,
            reemplazos={banco_bloqueado.pk: matricula_compartida},
        )
        banco_bloqueado.matricula_compartida = matricula_compartida
        banco_bloqueado.actualizado_por = user
        banco_bloqueado.save()
        return banco_bloqueado
