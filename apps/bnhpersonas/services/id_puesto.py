"""Generación robusta y concurrente de ``id_puesto`` para BNH Personas.

Formato definitivo:
    CUEANEXO_NIVEL_TITULACION_ESPACIO_GRADO_SECCION_CEIC_CONSECUTIVO

Regla de ausencia/no correspondencia de componentes curriculares:
    -2

Ejemplos:
    220123400_1003_25_245_7_1_123_0001
    220123400_-2_-2_-2_-2_-2_1500_0001
"""
from __future__ import annotations

from django.core.exceptions import ValidationError

from ..models import PuestoSecuencia
from .concurrency import advisory_xact_lock


NO_CORRESPONDE = "-2"
CONSECUTIVO_ANCHO = 4


def _valor(valor) -> str:
    """Normaliza un componente; None/vacío se representa con -2."""
    if valor is None:
        return NO_CORRESPONDE
    texto = str(valor).strip()
    return texto if texto else NO_CORRESPONDE


def codigo_espacio_curricular(actividad) -> str:
    """Devuelve el código funcional id_espacio_curricular, no el PK técnico."""
    if not actividad.espacio_curricular_id:
        return NO_CORRESPONDE

    espacio = getattr(actividad, "espacio_curricular", None)
    if espacio is None:
        return NO_CORRESPONDE

    return _valor(espacio.id_espacio_curricular)


def construir_puesto_base(actividad) -> str:
    """Construye la parte estable del identificador del puesto."""
    cueanexo = str(actividad.cueanexo or "").strip()
    if not cueanexo:
        raise ValidationError("No se puede generar ID Puesto sin CUEANEXO.")

    if not actividad.ceic_id:
        raise ValidationError("No se puede generar ID Puesto sin Cargo / CEIC.")

    componentes = (
        cueanexo,
        _valor(actividad.nivel_curricular_id),
        _valor(actividad.titulacion),
        codigo_espacio_curricular(actividad),
        _valor(actividad.grado_anio_id),
        _valor(actividad.secciones_id),
        _valor(actividad.ceic_id),
    )
    return "_".join(componentes)


def construir_id_puesto(puesto_base: str, consecutivo: int) -> str:
    if consecutivo < 1:
        raise ValidationError("El consecutivo del puesto debe ser mayor que cero.")
    return f"{puesto_base}_{consecutivo:0{CONSECUTIVO_ANCHO}d}"


def reservar_consecutivo(puesto_base: str) -> int:
    """Reserva el siguiente número de forma segura dentro de la transacción actual.

    ``_save_activity_impl`` ya corre dentro de ``transaction.atomic``. El advisory
    lock serializa únicamente a quienes intentan crear el mismo puesto_base.
    """
    advisory_xact_lock("bnh:id_puesto", puesto_base)

    secuencia, _ = PuestoSecuencia.objects.select_for_update().get_or_create(
        puesto_base=puesto_base,
        defaults={"ultimo_consecutivo": 0},
    )
    secuencia.ultimo_consecutivo += 1
    secuencia.save(update_fields=["ultimo_consecutivo", "actualizado_en"])
    return secuencia.ultimo_consecutivo


def asignar_id_puesto(actividad, *, anterior=None) -> None:
    """Asigna o conserva el ID puesto en un alta/edición.

    - Alta: reserva un nuevo consecutivo.
    - Edición sin cambio estructural: conserva el ID existente.
    - Edición con cambio estructural: reserva consecutivo para la nueva base.
    """
    nueva_base = construir_puesto_base(actividad)

    if (
        anterior is not None
        and anterior.puesto_base == nueva_base
        and anterior.puesto_consecutivo
        and anterior.id_puesto
    ):
        actividad.puesto_base = anterior.puesto_base
        actividad.puesto_consecutivo = anterior.puesto_consecutivo
        actividad.id_puesto = anterior.id_puesto
        return

    consecutivo = reservar_consecutivo(nueva_base)
    actividad.puesto_base = nueva_base
    actividad.puesto_consecutivo = consecutivo
    actividad.id_puesto = construir_id_puesto(nueva_base, consecutivo)
