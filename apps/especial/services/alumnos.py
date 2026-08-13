# apps/especial/services/alumnos.py
# -*- coding: utf-8 -*-

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from ..models import AlumnoSeccion, EspecialAlumnoBanco


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
        update_fields = ["estado", "fecha_baja", "motivo_baja"]
        if "actualizado_por" in fields:
            alumno_banco_bloqueado.actualizado_por = user
            update_fields.append("actualizado_por")
        if "actualizado_en" in fields:
            update_fields.append("actualizado_en")
        alumno_banco_bloqueado.save(update_fields=update_fields)
        return alumno_banco_bloqueado
