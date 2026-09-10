# apps/especial/services/docentes_seccion.py
# -*- coding: utf-8 -*-
"""Funciones reutilizables para gestionar altas y bajas de docentes en una sección."""

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone

from ..models import DocenteSeccion, EspecialDocenteBanco, SeccionEspecial


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

        rol_nuevo = rol or asignacion_bloqueada.rol
        observaciones_nuevas = (
            asignacion_bloqueada.observaciones
            if observaciones is None
            else observaciones
        )

        duplicado = DocenteSeccion.objects.filter(
            seccion=seccion,
            docente_cuil=asignacion_bloqueada.docente_cuil,
            estado=DocenteSeccion.Estado.ACTIVO,
        ).exists()

        if duplicado:
            raise ValidationError(
                f"Ya existe un docente activo con rol «{asignacion_bloqueada.get_rol_display()}» "
                f"en esta sección. Dalo de baja antes de reasignar."
            )

        try:
            return DocenteSeccion.objects.create(
                seccion=seccion,
                docente_banco=(
                    EspecialDocenteBanco.objects.filter(
                        cueanexo=seccion.cueanexo,
                        ciclo=seccion.ciclo,
                        docente_cuil=asignacion_bloqueada.docente_cuil,
                        estado=EspecialDocenteBanco.Estado.ACTIVO,
                    ).order_by("-pk").first()
                ),
                docente_cuil=asignacion_bloqueada.docente_cuil,
                rol=rol_nuevo,
                estado=DocenteSeccion.Estado.ACTIVO,
                fecha_desde=timezone.localdate(),
                observaciones=observaciones_nuevas,
                creado_por=user,
                actualizado_por=user,
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
        asignacion_bloqueada = DocenteSeccion.objects.select_for_update().get(
            pk=asignacion.pk,
            seccion_id=asignacion.seccion_id,
        )
        if asignacion_bloqueada.estado == DocenteSeccion.Estado.BAJA:
            raise ValidationError("La asignación ya está en baja.")
        asignacion_bloqueada.estado = DocenteSeccion.Estado.BAJA
        asignacion_bloqueada.fecha_hasta = timezone.localdate()
        asignacion_bloqueada.actualizado_por = user
        asignacion_bloqueada.save(update_fields=["estado", "fecha_hasta", "actualizado_por", "actualizado_en"])
        return asignacion_bloqueada
