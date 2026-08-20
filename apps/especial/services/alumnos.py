# apps/especial/services/alumnos.py
# -*- coding: utf-8 -*-

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from ..models import (
    PADRON_DB_ALIAS,
    AlumnoSeccion,
    EspecialAlumnoBanco,
    EspecialPadronOferta,
    cueanexo_tiene_oferta_comun,
    cueanexo_tiene_oferta_matricula_compartida,
    normalizar_cueanexo,
)


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
        alumno_banco_bloqueado.matricula_compartida = None

        fields = {
            field.name for field in EspecialAlumnoBanco._meta.concrete_fields
        }
        update_fields = [
            "estado",
            "fecha_baja",
            "motivo_baja",
            "matricula_compartida",
        ]
        if "actualizado_por" in fields:
            alumno_banco_bloqueado.actualizado_por = user
            update_fields.append("actualizado_por")
        if "actualizado_en" in fields:
            update_fields.append("actualizado_en")
        alumno_banco_bloqueado.save(update_fields=update_fields)
        return alumno_banco_bloqueado


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
        if not cueanexo_tiene_oferta_comun(matricula_compartida, padron_queryset):
            raise ValidationError(
                "El CUE-Anexo asociado debe existir en el padrón y tener al menos una oferta Común."
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
        oferta_cache = {}
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
