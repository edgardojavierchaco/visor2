# apps/especial/views_docentes_seccion.py
# -*- coding: utf-8 -*-
"""
Funciones reutilizables para dar alta y baja de docentes en una sección.
Equivalente a apps/cef/views_docentes_grupo.py.
Son llamadas desde gestionar_seccion (vía AJAX) y desde views_docentes.py.
"""

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone

from .models import DocenteSeccion, SeccionEspecial


def dar_alta_docente_seccion(asignacion, user):
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
                update_fields=["estado", "fecha_hasta", "actualizado_por", "actualizado_en"]
            )
        except IntegrityError as exc:
            raise ValidationError(
                "No se pudo reactivar la asignación porque existe un conflicto con otra asignación activa."
            ) from exc


def dar_baja_docente_seccion(asignacion, user):
    """
    Marca una asignación de docente como baja y registra la fecha de baja.
    Lanza ValidationError si la asignación ya está en baja.
    """
    if asignacion.estado == DocenteSeccion.Estado.BAJA:
        raise ValidationError("La asignación ya está en baja.")

    with transaction.atomic():
        asignacion.estado = DocenteSeccion.Estado.BAJA
        asignacion.fecha_hasta = timezone.localdate()
        asignacion.actualizado_por = user
        asignacion.save(update_fields=["estado", "fecha_hasta", "actualizado_por", "actualizado_en"])
