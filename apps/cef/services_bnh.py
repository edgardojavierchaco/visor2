"""Pertenencia docente de CEF: BNH Personas es la única autoridad institucional."""

import re

from django.core.exceptions import ValidationError
from django.db import DatabaseError

from apps.bnhpersonas.models import Personas, RegistroActividades


def _digitos(valor):
    return re.sub(r"\D", "", str(valor or ""))


def _identificador(valor, longitud):
    normalizado = _digitos(valor)
    return normalizado if len(normalizado) == longitud else ""


def vinculaciones_bnh(cuil=None, cueanexo=None):
    queryset = RegistroActividades.objects.filter(
        eliminado=False,
        persona__archivada=False,
    )
    if cuil is not None:
        cuil = _identificador(cuil, 11)
        if not cuil:
            return queryset.none()
        queryset = queryset.filter(persona__cuil=cuil)
    if cueanexo is not None:
        cueanexo = _identificador(cueanexo, 9)
        if not cueanexo:
            return queryset.none()
        queryset = queryset.filter(cueanexo=cueanexo)
    return queryset


def persona_bnh_existente(cuil):
    cuil = _identificador(cuil, 11)
    return bool(cuil and Personas.objects.filter(cuil=cuil, archivada=False).exists())


def docente_vinculado_bnh(cuil, cueanexo):
    cuil = _identificador(cuil, 11)
    cueanexo = _identificador(cueanexo, 9)
    return bool(cuil and cueanexo and vinculaciones_bnh(cuil, cueanexo).exists())


def validar_docente_vinculado_bnh(cuil, cueanexo):
    cuil = _identificador(cuil, 11)
    cueanexo = _identificador(cueanexo, 9)
    if not cuil:
        raise ValidationError("El CUIL del profesor no es válido.")
    if not cueanexo:
        raise ValidationError("El CUE-Anexo seleccionado no es válido.")
    try:
        if not persona_bnh_existente(cuil):
            raise ValidationError("El profesor no existe en BNH Personas.")
        if not docente_vinculado_bnh(cuil, cueanexo):
            raise ValidationError(
                "El profesor existe en BNH Personas, pero no está "
                "vinculado al CUE-Anexo seleccionado. No es posible asignarlo a este grupo."
            )
    except DatabaseError as exc:
        raise ValidationError(
            "No se pudo consultar BNH Personas. La asignación no se guardó."
        ) from exc
    return cuil


def cueanexos_docente_bnh(cuil):
    cuil = _identificador(cuil, 11)
    if not cuil:
        return []
    return sorted({
        str(cueanexo)
        for cueanexo in (
            vinculaciones_bnh(cuil).values_list("cueanexo", flat=True).distinct()
        )
        if _identificador(cueanexo, 9) == str(cueanexo)
    })


def cuiles_docentes_bnh(cueanexo):
    cueanexo = _identificador(cueanexo, 9)
    if not cueanexo:
        return []
    return sorted({
        str(cuil)
        for cuil in (
            vinculaciones_bnh(cueanexo=cueanexo)
            .values_list("persona__cuil", flat=True).distinct()
        )
        if _identificador(cuil, 11) == str(cuil)
    })


def pares_docente_cue_bnh(cuiles, cueanexos):
    cuiles = {
        cuil for valor in cuiles if (cuil := _identificador(valor, 11))
    }
    cueanexos = {
        cue for valor in cueanexos if (cue := _identificador(valor, 9))
    }
    if not cuiles or not cueanexos:
        return set()
    return set(
        RegistroActividades.objects.filter(
            persona__cuil__in=cuiles,
            cueanexo__in=cueanexos,
            eliminado=False,
            persona__archivada=False,
        ).values_list("persona__cuil", "cueanexo").distinct()
    )


def buscar_docente_bnh(cuil, cueanexo):
    cuil = validar_docente_vinculado_bnh(cuil, cueanexo)
    return Personas.objects.filter(cuil=cuil, archivada=False).first()


def docentes_bnh(cueanexo):
    return Personas.objects.filter(
        cuil__in=cuiles_docentes_bnh(cueanexo), archivada=False,
    ).only("cuil", "apellido", "nombre", "dni", "estado").order_by(
        "apellido", "nombre", "cuil",
    )
