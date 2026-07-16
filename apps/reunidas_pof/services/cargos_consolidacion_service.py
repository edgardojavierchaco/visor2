import logging
from decimal import Decimal, InvalidOperation

from django.core.exceptions import ValidationError

from ..models import CargoPof


logger = logging.getLogger(__name__)


def _texto(valor):
    return str(valor or "").strip()


def _decimal(valor):
    try:
        decimal = Decimal(str(valor))
    except (InvalidOperation, TypeError, ValueError):
        raise ValidationError({"cantidad": ["La cantidad debe ser un numero valido."]})
    if decimal <= 0:
        raise ValidationError({"cantidad": ["La cantidad debe ser mayor a 0."]})
    if decimal != decimal.to_integral_value():
        raise ValidationError({"cantidad": ["La cantidad debe ser un numero entero."]})
    return decimal.to_integral_value()


def _decimal_no_negativo(valor):
    try:
        decimal = Decimal(str(valor))
    except (InvalidOperation, TypeError, ValueError):
        raise ValidationError({"puntos_asignados": ["Los puntos asignados deben ser un numero valido."]})
    if decimal < 0:
        raise ValidationError({"puntos_asignados": ["Los puntos asignados no pueden ser negativos."]})
    return decimal


def normalizar_ceic(valor):
    texto = _texto(valor)
    if not texto:
        raise ValidationError({"ceic": ["El CEIC es obligatorio."]})
    try:
        ceic = int(texto)
    except (TypeError, ValueError):
        raise ValidationError({"ceic": ["El CEIC debe ser un numero entero."]})
    if ceic <= 0:
        raise ValidationError({"ceic": ["El CEIC debe ser mayor a 0."]})
    return ceic


def normalizar_unidad_cantidad(valor):
    unidad = _texto(valor).upper()
    unidades = {opcion for opcion, _ in CargoPof.UnidadCantidad.choices}
    if unidad not in unidades:
        raise ValidationError({"unidad_cantidad": ["La unidad de cantidad no es valida."]})
    return unidad


def clave_cargo_consolidable_desde_oficializacion(cargo_oficializado):
    return (
        normalizar_ceic(cargo_oficializado.get("ceic")),
        normalizar_unidad_cantidad(cargo_oficializado.get("unidad_cantidad")),
    )


def consolidar_cargos_oficializados(cargos_oficializados):
    """
    Consolida cargos ya oficializados por backend antes de persistirlos.

    - Recibe CEIC, cargo, puntos y snapshot ya resueltos desde la fuente oficial.
    - Trata cargo y puntos como obligatorios porque ya fueron oficializados.
    - Consolida repetidos por CEIC y unidad manteniendo los datos oficiales del primer registro.
    - No debe usarse con payload crudo del navegador.
    """
    consolidados = {}
    advertencias = []
    cantidad_original = len(cargos_oficializados or [])

    for cargo_oficializado in cargos_oficializados or []:
        clave = clave_cargo_consolidable_desde_oficializacion(cargo_oficializado)
        cantidad = _decimal(cargo_oficializado.get("cantidad"))
        puntos = _decimal_no_negativo(cargo_oficializado.get("puntos_asignados"))
        total = cantidad * puntos

        if clave not in consolidados:
            datos_oficializados = dict(cargo_oficializado)
            datos_oficializados["ceic"] = clave[0]
            datos_oficializados["unidad_cantidad"] = clave[1]
            datos_oficializados["cantidad"] = cantidad
            datos_oficializados["puntos_asignados"] = puntos
            datos_oficializados["total"] = total
            datos_oficializados["cargo"] = _texto(datos_oficializados.get("cargo"))
            if not datos_oficializados["cargo"]:
                raise ValidationError({"cargo": ["El nombre del cargo es obligatorio."]})
            datos_oficializados["observacion"] = _texto(datos_oficializados.get("observacion"))
            datos_oficializados["snapshot_ceic"] = (
                datos_oficializados.get("snapshot_ceic")
                if isinstance(datos_oficializados.get("snapshot_ceic"), dict)
                else {}
            )
            consolidados[clave] = datos_oficializados
            continue

        cargo_existente = consolidados[clave]
        if cargo_existente.get("cargo") != _texto(cargo_oficializado.get("cargo")):
            advertencias.append(
                f"CEIC {clave[0]} repetido con distinta descripcion; se conservo la primera."
            )
        if cargo_existente["puntos_asignados"] != puntos:
            advertencias.append(
                f"CEIC {clave[0]} repetido con distintos puntos; se conservaron los primeros."
            )

        cargo_existente["cantidad"] += cantidad
        cargo_existente["total"] = cargo_existente["cantidad"] * cargo_existente["puntos_asignados"]

    cargos_consolidados = list(consolidados.values())
    return {
        "cargos": cargos_consolidados,
        "total_cargos_procesados": cantidad_original,
        "total_cargos_consolidados": cantidad_original - len(cargos_consolidados),
        "advertencias": advertencias,
    }


def buscar_cargo_afectado_existente(localizacion, ceic, unidad_cantidad):
    cargos = list(
        CargoPof.objects.filter(
            localizacion=localizacion,
            ceic=normalizar_ceic(ceic),
            unidad_cantidad=normalizar_unidad_cantidad(unidad_cantidad),
            estado_pof=CargoPof.EstadoPof.AFECTADO,
        )
        .order_by("id")
        [:2]
    )
    if len(cargos) > 1:
        logger.warning(
            "Duplicados historicos de cargo afectado localizacion_id=%s ceic=%s unidad=%s; se usa menor id=%s",
            getattr(localizacion, "id", None),
            ceic,
            unidad_cantidad,
            cargos[0].id,
        )
    return cargos[0] if cargos else None


def _obtener_cargos_existentes_por_clave(localizacion, cargos_consolidados):
    ceics = {cargo["ceic"] for cargo in cargos_consolidados}
    unidades = {cargo["unidad_cantidad"] for cargo in cargos_consolidados}
    existentes = {}
    advertencias = []

    if not ceics or not unidades:
        return existentes, advertencias

    queryset = (
        CargoPof.objects.select_for_update()
        .filter(
            localizacion=localizacion,
            estado_pof=CargoPof.EstadoPof.AFECTADO,
            ceic__in=ceics,
            unidad_cantidad__in=unidades,
        )
        .order_by("id")
    )

    for cargo in queryset:
        clave = (cargo.ceic, cargo.unidad_cantidad)
        if clave in existentes:
            advertencias.append(
                (
                    "Existen duplicados historicos para CEIC "
                    f"{cargo.ceic} y unidad {cargo.unidad_cantidad}; se incremento el menor id."
                )
            )
            continue
        existentes[clave] = cargo

    return existentes, advertencias


def incrementar_cargo_existente(cargo_existente, cargo_consolidado):
    valores_anteriores = {
        "cantidad": str(cargo_existente.cantidad),
        "total": str(cargo_existente.total),
    }
    update_fields = ["cantidad", "total", "actualizado_en"]
    cargo_existente.cantidad = cargo_existente.cantidad + cargo_consolidado["cantidad"]
    if not _texto(cargo_existente.cargo) and cargo_consolidado.get("cargo"):
        cargo_existente.cargo = cargo_consolidado["cargo"]
        update_fields.append("cargo")
    cargo_existente.save(update_fields=update_fields)
    return {
        "cargo": cargo_existente,
        "valores_anteriores": valores_anteriores,
    }


def crear_cargo_desde_oficializacion(localizacion, lote_carga, cargo_oficializado):
    return CargoPof.objects.create(
        localizacion=localizacion,
        lote_carga=lote_carga,
        ceic=cargo_oficializado["ceic"],
        cargo=cargo_oficializado.get("cargo", ""),
        cantidad=cargo_oficializado["cantidad"],
        unidad_cantidad=cargo_oficializado["unidad_cantidad"],
        puntos_asignados=cargo_oficializado["puntos_asignados"],
        estado_pof=CargoPof.EstadoPof.AFECTADO,
        observacion=cargo_oficializado.get("observacion", ""),
        snapshot_ceic=cargo_oficializado.get("snapshot_ceic") or {},
    )


def aplicar_alta_consolidada(localizacion, lote_carga, cargos_oficializados, usuario=None):
    """
    Aplica altas e incrementos usando únicamente cargos ya oficializados por backend.

    - Nunca debe recibir payload crudo del navegador.
    - Consolida primero por CEIC y unidad con datos oficiales.
    - Persiste o incrementa manteniendo cargo, puntos y snapshot confiables.
    """
    resultado_consolidacion = consolidar_cargos_oficializados(cargos_oficializados)
    cargos_consolidados = resultado_consolidacion["cargos"]
    existentes, advertencias_existentes = _obtener_cargos_existentes_por_clave(
        localizacion,
        cargos_consolidados,
    )

    creados = []
    incrementados = []
    advertencias = list(resultado_consolidacion["advertencias"]) + advertencias_existentes

    for cargo_consolidado in cargos_consolidados:
        clave = (cargo_consolidado["ceic"], cargo_consolidado["unidad_cantidad"])
        cargo_existente = existentes.get(clave)
        if cargo_existente:
            if cargo_existente.puntos_asignados != cargo_consolidado["puntos_asignados"]:
                advertencias.append(
                    (
                        "El CEIC "
                        f"{cargo_consolidado['ceic']} ya existia con otros puntos; se conservaron los puntos actuales."
                    )
                )
            if _texto(cargo_existente.cargo) != _texto(cargo_consolidado.get("cargo")):
                advertencias.append(
                    (
                        "El CEIC "
                        f"{cargo_consolidado['ceic']} ya existia con otra descripcion; se conservo la actual."
                    )
                )
            incremento = incrementar_cargo_existente(cargo_existente, cargo_consolidado)
            incremento["cargo_data"] = cargo_consolidado
            incrementados.append(incremento)
            continue

        cargo = crear_cargo_desde_oficializacion(localizacion, lote_carga, cargo_consolidado)
        creados.append({"cargo": cargo, "cargo_data": cargo_consolidado})

    return {
        "creados": creados,
        "incrementados": incrementados,
        "total_cargos_procesados": resultado_consolidacion["total_cargos_procesados"],
        "total_cargos_consolidados": resultado_consolidacion["total_cargos_consolidados"],
        "advertencias": advertencias,
    }
