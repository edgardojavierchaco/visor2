from collections import defaultdict
from decimal import Decimal, InvalidOperation

from ..models import CargoPof


COLUMNAS_CARGO_NO_VACIAR = {
    "ceic",
    "cargo",
    "cantidad",
    "cantidad_cargos",
    "cantidad_horas",
    "puntos",
    "total",
}

COLUMNAS_TOTALES_POR_GRUPO_TOTAL = {
    "total_general",
    "total_general_exportacion",
    "total_horas_catedra",
    "puntos_horas_catedra",
    "total_puntos",
}


def texto(valor):
    if valor is None:
        return ""
    return str(valor).strip()


def _decimal_o_cero(valor):
    if valor in (None, ""):
        return Decimal("0")
    if isinstance(valor, Decimal):
        return valor
    try:
        return Decimal(str(valor))
    except (InvalidOperation, TypeError, ValueError):
        return Decimal("0")


def _decimal_dos_decimales(valor):
    return _decimal_o_cero(valor).quantize(Decimal("0.01"))


def _cantidad_entera(valor):
    decimal = _decimal_o_cero(valor)
    if decimal == decimal.to_integral_value():
        return int(decimal)
    return decimal


def _cue_desde_cueanexo(valor):
    """
    Deriva el CUE base desde un CUE-Anexo cuando el campo canonico no viene poblado.

    - Usa solo CUEANEXO de 9 digitos para no inventar identificadores parciales.
    - Devuelve cadena vacia si no puede obtener un CUE confiable.
    - Permite unificar agrupaciones de exportacion por CUE real.
    """
    cueanexo = "".join(caracter for caracter in texto(valor) if caracter.isdigit())
    if len(cueanexo) >= 7:
        return cueanexo[:7]
    return ""


def _resolver_cue_exportacion(localizacion):
    """
    Resuelve el CUE operativo usado por la exportacion y sus totales.

    - Prioriza `cue_base` cuando la localizacion ya lo tiene almacenado.
    - Si falta, lo deriva desde `cueanexo` para mantener agrupacion por CUE.
    - Nunca usa CUOF como sustituto del CUE.
    """
    cue = texto(getattr(localizacion, "cue_base", ""))
    if cue:
        return cue
    return _cue_desde_cueanexo(getattr(localizacion, "cueanexo", ""))


def _unir_partes(*partes):
    partes_limpias = [texto(parte) for parte in partes if texto(parte)]
    return " - ".join(partes_limpias)


def _texto_consolidacion(valor):
    return " ".join(texto(valor).upper().split())


def obtener_snapshot_vigente(cargo):
    localizacion = getattr(cargo, "localizacion", None)
    snapshots = getattr(localizacion, "snapshots_vigentes", [])
    return snapshots[0] if snapshots else None


def _obtener_tipo_anexo(localizacion):
    anexo = texto(getattr(localizacion, "anexo_localizacion", ""))
    if not anexo:
        return ""
    if anexo == "00":
        return "Sede"
    return f"Anexo {anexo}"


def _es_hora_catedra(cargo):
    unidad = texto(getattr(cargo, "unidad_cantidad", "")).upper()
    valor_hora = texto(CargoPof.UnidadCantidad.HORA_CATEDRA).upper()
    return unidad == valor_hora or "HORA" in unidad


def _es_afectado(cargo):
    return getattr(cargo, "estado_pof", "") == CargoPof.EstadoPof.AFECTADO


def _calcular_total_cargo(cargo):
    total = getattr(cargo, "total", None)
    if total not in (None, ""):
        return _decimal_o_cero(total)
    return _decimal_o_cero(getattr(cargo, "cantidad", None)) * _decimal_o_cero(
        getattr(cargo, "puntos_asignados", None)
    )


def _valor_snapshot_o_localizacion(snapshot, localizacion, campo):
    if snapshot:
        valor = texto(getattr(snapshot, campo, ""))
        if valor:
            return valor
    return texto(getattr(localizacion, campo, ""))


def construir_datos_normalizados_cargo(cargo, total_general=None, totales_especiales=None):
    localizacion = getattr(cargo, "localizacion", None)
    reunida = getattr(localizacion, "reunida", None)
    proyecto = getattr(localizacion, "proyecto_especial", None)
    snapshot = obtener_snapshot_vigente(cargo)
    subcue = texto(getattr(localizacion, "cueanexo", ""))
    cueanexo = subcue
    cue = _resolver_cue_exportacion(localizacion)
    anexo = texto(getattr(localizacion, "anexo_localizacion", ""))
    cui = texto(getattr(localizacion, "cui", ""))
    cuof = texto(getattr(localizacion, "cuof", ""))
    region = _valor_snapshot_o_localizacion(snapshot, localizacion, "region")
    numero_establecimiento = _valor_snapshot_o_localizacion(
        snapshot,
        localizacion,
        "numero_establecimiento",
    )
    nombre = _valor_snapshot_o_localizacion(snapshot, localizacion, "nombre_establecimiento")
    categoria = _valor_snapshot_o_localizacion(snapshot, localizacion, "categoria")
    jornada = _valor_snapshot_o_localizacion(snapshot, localizacion, "jornada")
    modalidad = _valor_snapshot_o_localizacion(snapshot, localizacion, "acronimo")
    if not modalidad:
        modalidad = _valor_snapshot_o_localizacion(snapshot, localizacion, "oferta")
    ambito = _valor_snapshot_o_localizacion(snapshot, localizacion, "ambito")
    ubicacion = _valor_snapshot_o_localizacion(snapshot, localizacion, "ubicacion")
    localidad = _valor_snapshot_o_localizacion(snapshot, localizacion, "localidad")
    departamento = _valor_snapshot_o_localizacion(snapshot, localizacion, "departamento")
    ubicacion_completa = _valor_snapshot_o_localizacion(
        snapshot,
        localizacion,
        "ubicacion_localidad_departamento",
    ) or _unir_partes(ubicacion, localidad, departamento)
    cantidad = _cantidad_entera(getattr(cargo, "cantidad", None))
    puntos = _decimal_o_cero(getattr(cargo, "puntos_asignados", None))
    total = _calcular_total_cargo(cargo)
    cantidad_horas = cantidad if _es_hora_catedra(cargo) else ""
    cantidad_cargos = "" if _es_hora_catedra(cargo) else cantidad

    datos = {
        "anio": getattr(reunida, "anio", "") or getattr(proyecto, "anio", ""),
        "proyecto_especial": texto(getattr(proyecto, "nombre", "")),
        "resolucion": texto(getattr(proyecto, "resolucion", "")),
        "region": region,
        "region_anexo": region,
        "ex_region": region,
        "cuof": cuof,
        "sub_cuof": anexo,
        "cue": cue,
        "subcue": subcue,
        "cueanexo": cueanexo,
        "cue_bloque_final": cue,
        "cue_anexo": cueanexo or cue,
        "cui": cui,
        "cui_bloque_final": cui,
        "cui_anexo": cui,
        "cue_cui": _unir_partes(cue, cui),
        "numero_establecimiento": numero_establecimiento,
        "establecimiento": _unir_partes(numero_establecimiento, nombre),
        "nombre": nombre,
        "categoria": categoria,
        "jornada": jornada,
        "categoria_jornada": _unir_partes(categoria, jornada),
        "modalidad": modalidad,
        "tipo_anexo": _obtener_tipo_anexo(localizacion),
        "ambito": ambito,
        "ubicacion": ubicacion,
        "ubicacion_anexo": ubicacion,
        "domicilio": ubicacion,
        "localidad": localidad,
        "localidad_anexo": localidad,
        "departamento": departamento,
        "departamento_anexo": departamento,
        "ubicacion_completa": ubicacion_completa,
        "zona": ambito,
        "ceic": getattr(cargo, "ceic", ""),
        "cargo": texto(getattr(cargo, "cargo", "")),
        "cantidad": cantidad,
        "cantidad_cargos": cantidad_cargos,
        "cantidad_horas": cantidad_horas,
        "puntos": puntos,
        "total": total,
        "total_general": _decimal_o_cero(total_general),
        "total_general_exportacion": _decimal_o_cero(total_general),
        "total_horas_catedra": cantidad_horas,
        "puntos_horas_catedra": puntos if cantidad_horas != "" else "",
        "total_puntos": total,
        "blank": "",
        "anexo": anexo,
        "oferta": _valor_snapshot_o_localizacion(snapshot, localizacion, "oferta"),
        "unidad": texto(cargo.get_unidad_cantidad_display()) if hasattr(cargo, "get_unidad_cantidad_display") else "",
        "localizacion_id": getattr(cargo, "localizacion_id", "") or getattr(localizacion, "id", ""),
        "unidad_cantidad": texto(getattr(cargo, "unidad_cantidad", "")),
        "cargo_id": getattr(cargo, "id", ""),
        "cargo_ids": [getattr(cargo, "id", "")] if getattr(cargo, "id", None) else [],
        "estado_pof_codigo": texto(getattr(cargo, "estado_pof", "")),
        "estado_pof": texto(cargo.get_estado_pof_display()) if hasattr(cargo, "get_estado_pof_display") else "",
        "observacion_cargo": texto(getattr(cargo, "observacion", "")),
        "_observaciones_cargo": (
            [texto(getattr(cargo, "observacion", ""))]
            if texto(getattr(cargo, "observacion", ""))
            else []
        ),
    }

    if totales_especiales:
        datos.update(totales_especiales)

    return datos


def _construir_clave_consolidacion(
    localizacion_id,
    estado_pof,
    ceic,
    unidad_cantidad,
    cargo,
    puntos,
):
    return (
        localizacion_id,
        texto(estado_pof),
        texto(ceic),
        texto(unidad_cantidad),
        _texto_consolidacion(cargo),
        _decimal_o_cero(puntos),
    )


def _clave_consolidacion_exportacion(fila):
    return _construir_clave_consolidacion(
        fila.get("localizacion_id", ""),
        fila.get("estado_pof_codigo", ""),
        fila.get("ceic", ""),
        fila.get("unidad_cantidad", ""),
        fila.get("cargo", ""),
        fila.get("puntos"),
    )


def obtener_clave_consolidacion_cargo(cargo):
    return _construir_clave_consolidacion(
        getattr(cargo, "localizacion_id", ""),
        getattr(cargo, "estado_pof", ""),
        getattr(cargo, "ceic", ""),
        getattr(cargo, "unidad_cantidad", ""),
        getattr(cargo, "cargo", ""),
        getattr(cargo, "puntos_asignados", ""),
    )


def _sumar_campo_numerico(fila_destino, fila_origen, campo):
    if campo not in fila_destino or campo not in fila_origen:
        return
    if fila_destino.get(campo) in ("", None) and fila_origen.get(campo) in ("", None):
        return

    fila_destino[campo] = _cantidad_entera(
        _decimal_o_cero(fila_destino.get(campo)) + _decimal_o_cero(fila_origen.get(campo))
    )


def _actualizar_total_consolidado(fila):
    total = _decimal_o_cero(fila.get("cantidad")) * _decimal_o_cero(fila.get("puntos"))
    fila["total"] = _decimal_dos_decimales(total)
    fila["total_puntos"] = fila["total"]


def _consolidar_filas_normalizadas(filas):
    consolidadas = {}
    orden_claves = []

    for indice, fila in enumerate(filas):
        clave = (
            _clave_consolidacion_exportacion(fila)
            if _es_fila_afectada(fila)
            else ("__sin_consolidar__", indice)
        )

        if clave not in consolidadas:
            consolidadas[clave] = fila.copy()
            orden_claves.append(clave)
            continue

        fila_consolidada = consolidadas[clave]
        fila_consolidada["cargo_ids"] = sorted({
            *fila_consolidada.get("cargo_ids", []),
            *fila.get("cargo_ids", []),
        })
        observaciones = []
        for observacion in (
            *fila_consolidada.get("_observaciones_cargo", []),
            *fila.get("_observaciones_cargo", []),
        ):
            if observacion and observacion not in observaciones:
                observaciones.append(observacion)
        fila_consolidada["_observaciones_cargo"] = observaciones
        fila_consolidada["observacion_cargo"] = " | ".join(observaciones)
        _sumar_campo_numerico(fila_consolidada, fila, "cantidad")
        _sumar_campo_numerico(fila_consolidada, fila, "cantidad_cargos")
        _sumar_campo_numerico(fila_consolidada, fila, "cantidad_horas")
        _sumar_campo_numerico(fila_consolidada, fila, "total_horas_catedra")
        _actualizar_total_consolidado(fila_consolidada)

    filas_consolidadas = [consolidadas[clave] for clave in orden_claves]
    for fila in filas_consolidadas:
        fila.pop("_observaciones_cargo", None)
    return filas_consolidadas


def construir_filas_normalizadas(cargos, nivel_codigo=None, schema=None):
    cargos = list(cargos)

    filas = _consolidar_filas_normalizadas([
        construir_datos_normalizados_cargo(cargo)
        for cargo in cargos
    ])

    totales_por_localizacion = defaultdict(lambda: Decimal("0"))
    for fila in filas:
        if _es_fila_afectada(fila):
            totales_por_localizacion[fila.get("localizacion_id", "")] += _decimal_o_cero(
                fila.get("total")
            )

    for fila in filas:
        total_general = totales_por_localizacion.get(
            fila.get("localizacion_id", ""),
            Decimal("0"),
        )
        fila["total_general"] = total_general
        fila["total_general_exportacion"] = total_general

    if nivel_codigo:
        totales_por_grupo = defaultdict(lambda: Decimal("0"))
        for fila in filas:
            if _es_fila_afectada(fila):
                clave_total = obtener_clave_total_general(fila, schema or {})
                totales_por_grupo[clave_total] += _decimal_o_cero(fila.get("total"))

        for fila in filas:
            total_general_exportacion = totales_por_grupo.get(
                obtener_clave_total_general(fila, schema or {}),
                Decimal("0"),
            )
            fila["total_general"] = total_general_exportacion
            fila["total_general_exportacion"] = total_general_exportacion

    return filas


def renderizar_fila_schema(datos_normalizados, schema):
    return [
        datos_normalizados.get(columna["key"], "")
        for columna in schema["columnas"]
    ]


def _obtener_clave_con_fallback(datos_normalizados, grupo):
    if list(grupo) == ["cueanexo", "cuof"]:
        cuof = datos_normalizados.get("cuof", "")
        cueanexo = datos_normalizados.get("cueanexo", "")
        if cueanexo:
            return (cueanexo, cuof)
        return (datos_normalizados.get("cue", ""), cuof)

    if list(grupo) == ["cue", "cuof"]:
        cuof = datos_normalizados.get("cuof", "")
        cue = datos_normalizados.get("cue", "")
        if cue:
            return (cue, cuof)
        return (datos_normalizados.get("cueanexo", ""), cuof)

    if list(grupo) == ["cue"]:
        cue = texto(datos_normalizados.get("cue", "")) or _cue_desde_cueanexo(
            datos_normalizados.get("cueanexo", "")
        )
        if cue:
            return (cue,)
        return (texto(datos_normalizados.get("localizacion_id", "")),)

    return tuple(datos_normalizados.get(clave, "") for clave in grupo)


def obtener_clave_grupo_visual(datos_normalizados, schema):
    grupo = schema.get("grupo") or ("cueanexo", "cuof")
    return _obtener_clave_con_fallback(datos_normalizados, grupo)


def obtener_clave_total_general(datos_normalizados, schema):
    grupo = schema.get("grupo_total_general") or ("cue", "cuof")
    return _obtener_clave_con_fallback(datos_normalizados, grupo)


def obtener_clave_grupo(datos_normalizados, schema):
    return obtener_clave_grupo_visual(datos_normalizados, schema)


def _es_fila_hora_catedra(datos_normalizados):
    return datos_normalizados.get("cantidad_horas") not in ("", None)


def _es_fila_afectada(datos_normalizados):
    return datos_normalizados.get("estado_pof_codigo") == CargoPof.EstadoPof.AFECTADO


def _sumar_decimal(valor_actual, valor_nuevo):
    return _decimal_o_cero(valor_actual) + _decimal_o_cero(valor_nuevo)


def _calcular_totales_especiales_por_grupo(filas_normalizadas, schema):
    keys_schema = {columna["key"] for columna in schema["columnas"]}
    requiere_horas_tecnica = {
        "total_horas_catedra",
        "puntos_horas_catedra",
        "total_puntos",
    }.issubset(keys_schema)

    if not requiere_horas_tecnica:
        return {}

    totales = defaultdict(lambda: {
        "total_horas_catedra": Decimal("0"),
        "puntos_horas_catedra": Decimal("0"),
        "total_puntos": Decimal("0"),
    })

    for fila in filas_normalizadas:
        if not _es_fila_afectada(fila):
            continue

        clave_grupo = obtener_clave_total_general(fila, schema)
        totales[clave_grupo]["total_puntos"] = _sumar_decimal(
            totales[clave_grupo]["total_puntos"],
            fila.get("total"),
        )
        if _es_fila_hora_catedra(fila):
            totales[clave_grupo]["total_horas_catedra"] = _sumar_decimal(
                totales[clave_grupo]["total_horas_catedra"],
                fila.get("cantidad_horas"),
            )
            totales[clave_grupo]["puntos_horas_catedra"] = _sumar_decimal(
                totales[clave_grupo]["puntos_horas_catedra"],
                fila.get("total"),
            )

    for total in totales.values():
        total["total_horas_catedra"] = _cantidad_entera(total["total_horas_catedra"])

    return dict(totales)


def aplicar_vaciado_repetidos(filas_normalizadas, schema):
    filas = [fila.copy() for fila in filas_normalizadas]
    keys_vaciables = set(schema.get("vaciar_repetidos", [])) - COLUMNAS_CARGO_NO_VACIAR
    keys_totales = keys_vaciables & COLUMNAS_TOTALES_POR_GRUPO_TOTAL
    keys_vaciables_visuales = keys_vaciables - keys_totales
    totales_especiales_por_grupo = _calcular_totales_especiales_por_grupo(filas, schema)
    grupos_visuales_vistos = set()
    grupos_totales_vistos = set()

    for fila in filas:
        clave_visual = obtener_clave_grupo_visual(fila, schema)
        clave_total = obtener_clave_total_general(fila, schema)
        if clave_total in totales_especiales_por_grupo:
            fila.update(totales_especiales_por_grupo[clave_total])

        if clave_visual in grupos_visuales_vistos:
            for key in keys_vaciables_visuales:
                fila[key] = ""
        else:
            grupos_visuales_vistos.add(clave_visual)

        if clave_total in grupos_totales_vistos:
            for key in keys_totales:
                fila[key] = ""
        else:
            grupos_totales_vistos.add(clave_total)

    return filas


def construir_filas_exportacion(schema, filas_normalizadas, espejo=True):
    filas_render = (
        aplicar_vaciado_repetidos(filas_normalizadas, schema)
        if espejo
        else [fila.copy() for fila in filas_normalizadas]
    )
    return [renderizar_fila_schema(fila, schema) for fila in filas_render]
