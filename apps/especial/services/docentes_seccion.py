# apps/especial/services/docentes_seccion.py
# -*- coding: utf-8 -*-
"""Funciones reutilizables para gestionar altas y bajas de docentes en una sección."""

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone

from ..models import DocenteSeccion, SeccionEspecial


def dar_alta_docente_seccion(asignacion, user, rol=None, observaciones=None):
    """
    Reactiva una asignación de docente que estaba en baja.
    Lanza ValidationError si ya existe otra asignación activa para ese rol.
    """
    with transaction.atomic():
        seccion = SeccionEspecial.objects.select_for_update().get(
            pk=asignacion.seccion_id
        )
        asignacion_bloqueada = DocenteSeccion.objects.select_for_update().get(
            pk=asignacion.pk,
            seccion=seccion,
        )
        if asignacion_bloqueada.estado == DocenteSeccion.Estado.ACTIVO:
            raise ValidationError("La asignación ya está activa.")

        if rol:
            asignacion_bloqueada.rol = rol
        if observaciones is not None:
            asignacion_bloqueada.observaciones = observaciones

        duplicado = DocenteSeccion.objects.filter(
            seccion=seccion,
            rol=asignacion_bloqueada.rol,
            estado=DocenteSeccion.Estado.ACTIVO,
        ).exclude(pk=asignacion_bloqueada.pk).exists()

        if duplicado:
            raise ValidationError(
                f"Ya existe un docente activo con rol «{asignacion_bloqueada.get_rol_display()}» "
                f"en esta sección. Dalo de baja antes de reasignar."
            )

        asignacion_bloqueada.estado = DocenteSeccion.Estado.ACTIVO
        asignacion_bloqueada.fecha_hasta = None
        asignacion_bloqueada.actualizado_por = user
        try:
            asignacion_bloqueada.save(
                update_fields=[
                    "rol", "estado", "fecha_hasta", "observaciones",
                    "actualizado_por", "actualizado_en",
                ]
            )
        except IntegrityError as exc:
            raise ValidationError(
                "No se pudo reactivar la asignación porque existe un conflicto con otra asignación activa."
            ) from exc
        return asignacion_bloqueada


def dar_baja_docente_seccion(asignacion, user):
    """
    Marca una asignación de docente como baja y registra la fecha de baja.
    Lanza ValidationError si la asignación ya está en baja.
    """
    if asignacion.estado == DocenteSeccion.Estado.BAJA:
        raise ValidationError("La asignación ya está en baja.")

    with transaction.atomic():
        asignacion_bloqueada = DocenteSeccion.objects.select_for_update().get(
            pk=asignacion.pk,
            seccion_id=asignacion.seccion_id,
        )
        if asignacion_bloqueada.estado == DocenteSeccion.Estado.BAJA:
            raise ValidationError("La asignaciÃ³n ya estÃ¡ en baja.")
        asignacion_bloqueada.estado = DocenteSeccion.Estado.BAJA
        asignacion_bloqueada.fecha_hasta = timezone.localdate()
        asignacion_bloqueada.actualizado_por = user
        asignacion_bloqueada.save(update_fields=["estado", "fecha_hasta", "actualizado_por", "actualizado_en"])
        return asignacion_bloqueada
