# apps/especial/views_docentes_seccion.py
# -*- coding: utf-8 -*-
"""
Funciones reutilizables para dar alta y baja de docentes en una sección.
Equivalente a apps/cef/views_docentes_grupo.py.
Son llamadas desde gestionar_seccion (vía AJAX) y desde views_docentes.py.
"""

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from .models import DocenteSeccion


def dar_alta_docente_seccion(asignacion, user):
    """
    Reactiva una asignación de docente que estaba en baja.
    Lanza ValidationError si ya existe otra asignación activa para ese rol.
    """
    if asignacion.estado == DocenteSeccion.Estado.ACTIVO:
        raise ValidationError("La asignación ya está activa.")

    # Verificar que no haya otro activo en el mismo rol para la misma sección
    duplicado = DocenteSeccion.objects.filter(
        grupo=asignacion.grupo,
        rol=asignacion.rol,
        estado=DocenteSeccion.Estado.ACTIVO,
    ).exclude(pk=asignacion.pk).exists()

    if duplicado:
        raise ValidationError(
            f"Ya existe un docente activo con rol «{asignacion.get_rol_display()}» "
            f"en esta sección. Dalo de baja antes de reasignar."
        )

    with transaction.atomic():
        asignacion.estado = DocenteSeccion.Estado.ACTIVO
        asignacion.fecha_hasta = None
        asignacion.actualizado_por = user
        asignacion.save(update_fields=["estado", "fecha_hasta", "actualizado_por", "actualizado_en"])


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
