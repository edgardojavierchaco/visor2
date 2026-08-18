# -*- coding: utf-8 -*-
"""Baja general y aplicación de traslados de docentes de Educación Especial."""

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone

from ..models import (
    DocenteSeccion,
    EspecialDocenteBanco,
    EspecialTrasladoDocente,
)


def preparar_baja_docente(banco, cueanexo, ciclo):
    return list(
        DocenteSeccion.objects.filter(
            docente_cuil=banco.docente_cuil,
            seccion__cueanexo=cueanexo,
            seccion__ciclo=ciclo,
            estado=DocenteSeccion.Estado.ACTIVO,
        )
        .select_related("seccion", "seccion__turno")
        .order_by("seccion__nombre_seccion", "rol")
    )


def dar_baja_docente_banco(
    *,
    banco_id,
    cueanexo,
    ciclo,
    user,
    motivo_baja,
    observaciones="",
    cueanexo_destino="",
    ciclo_destino=None,
):
    """Da de baja el banco sólo si el servidor confirma que no quedan cargos activos."""
    with transaction.atomic():
        banco = (
            EspecialDocenteBanco.objects.select_for_update()
            .get(pk=banco_id, cueanexo=cueanexo, ciclo=ciclo)
        )
        if banco.estado != EspecialDocenteBanco.Estado.ACTIVO:
            raise ValidationError("El docente ya no se encuentra activo en este establecimiento y ciclo.")

        asignaciones = preparar_baja_docente(banco, cueanexo, ciclo)
        if asignaciones:
            raise ValidationError(
                "No se puede dar de baja al docente mientras conserve cargos o secciones activas en este establecimiento y ciclo."
            )

        hoy = timezone.localdate()
        banco.estado = EspecialDocenteBanco.Estado.BAJA
        banco.fecha_baja = hoy
        banco.motivo_baja = motivo_baja
        banco.observaciones = observaciones or ""
        banco.actualizado_por = user
        banco.save(update_fields=["estado", "fecha_baja", "motivo_baja", "observaciones", "actualizado_por", "actualizado_en"])

        if motivo_baja == "traslado":
            if not cueanexo_destino or not ciclo_destino:
                raise ValidationError("El traslado requiere CUE-Anexo y ciclo destino.")
            try:
                traslado, creado = EspecialTrasladoDocente.objects.get_or_create(
                    docente_cuil=banco.docente_cuil,
                    cueanexo_destino=cueanexo_destino,
                    ciclo_destino=ciclo_destino,
                    estado=EspecialTrasladoDocente.Estado.EN_TRANSITO,
                    defaults={
                        "docente_nombre_snapshot": banco.docente_nombre_snapshot,
                        "docente_dni_snapshot": banco.docente_dni_snapshot,
                        "cueanexo_origen": banco.cueanexo,
                        "ciclo_origen": banco.ciclo,
                        "observaciones": observaciones or "",
                        "creado_por": user,
                        "actualizado_por": user,
                    },
                )
            except IntegrityError as exc:
                raise ValidationError("Ya existe un traslado pendiente para ese docente y destino.") from exc
            if not creado:
                traslado.observaciones = observaciones or traslado.observaciones
                traslado.actualizado_por = user
                traslado.save(update_fields=["observaciones", "actualizado_por", "actualizado_en"])
        return banco


def aplicar_traslados_docentes(ciclo_destino, user, cueanexo=None):
    """Aplica traslados pendientes al crear el ciclo destino, sin copiar cargos."""
    filtros = {
        "estado": EspecialTrasladoDocente.Estado.EN_TRANSITO,
        "ciclo_destino": ciclo_destino,
    }
    if cueanexo:
        filtros["cueanexo_destino"] = cueanexo

    with transaction.atomic():
        traslados = list(
            EspecialTrasladoDocente.objects.select_for_update().filter(**filtros)
        )
        for traslado in traslados:
            banco, creado = EspecialDocenteBanco.objects.get_or_create(
                cueanexo=traslado.cueanexo_destino,
                ciclo=ciclo_destino,
                docente_cuil=traslado.docente_cuil,
                estado=EspecialDocenteBanco.Estado.ACTIVO,
                defaults={
                    "docente_nombre_snapshot": traslado.docente_nombre_snapshot,
                    "docente_dni_snapshot": traslado.docente_dni_snapshot,
                    "fecha_alta": timezone.localdate(),
                    "creado_por": user,
                    "actualizado_por": user,
                },
            )
            traslado.estado = EspecialTrasladoDocente.Estado.APLICADO
            traslado.fecha_aplicacion = timezone.localdate()
            traslado.actualizado_por = user
            traslado.save(update_fields=["estado", "fecha_aplicacion", "actualizado_por", "actualizado_en"])
    return len(traslados)
