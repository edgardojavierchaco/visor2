from decimal import Decimal

from ...models import CargoPof


INFO_CUE_DETALLE_CAMPOS = (
    ("Ubicación", "ubicacion"),
    ("Localidad", "localidad"),
    ("Departamento", "departamento"),
    ("Zona", "zona"),
    ("Región", "region"),
)


def _obtener_valor_politica(fila_normalizada, descriptor):
    """
    Lee un valor desde una fila normalizada respetando el alias declarado en politica.

    - Prioriza el campo operativo definido por la politica cuando existe.
    - Usa `origen_actual` para compatibilizar la estructura futura con la fila vigente.
    - No transforma ni reordena datos fuera de lo ya normalizado por la grilla.
    """
    campo = descriptor.get("campo", "")
    origen_actual = descriptor.get("origen_actual") or campo
    return fila_normalizada.get(origen_actual, fila_normalizada.get(campo, ""))


def _derivar_cue_y_anexo(cueanexo):
    """
    Deriva `cue` y `anexo` desde el dato canonico `cueanexo`.

    - Usa `cueanexo[:7]` y `cueanexo[7:9]` solo cuando hay 9 digitos validos.
    - Devuelve vacio para ambos si el valor no cumple el formato esperado.
    - Conserva `cueanexo` como fuente canonica sin inventar reemplazos.
    """
    valor = str(cueanexo or "").strip()
    if len(valor) == 9 and valor.isdigit():
        return valor[:7], valor[7:9]
    return "", ""


def _normalizar_valor_info_cue(valor):
    """
    Normaliza un valor candidato para el modal informativo de CUE.

    - Quita espacios externos y colapsa espacios internos repetidos.
    - Devuelve vacio para valores nulos o sin contenido real.
    - Usa una clave case-insensitive para detectar conflictos entre anexos.
    """
    texto = " ".join(str(valor or "").strip().split())
    return texto, texto.casefold()


def _registrar_valores_info_cue(valores_por_campo, fila_normalizada):
    """
    Acumula valores candidatos comunes para el modal Info CUE.

    - Recorre solo campos descriptivos comunes del CUE.
    - Ignora vacios para que no se rendericen bloques sin dato.
    - Conserva los distintos valores normalizados para detectar conflictos.
    """
    for _label, campo in INFO_CUE_DETALLE_CAMPOS:
        valor, clave = _normalizar_valor_info_cue(fila_normalizada.get(campo, ""))
        if not clave:
            continue
        valores_por_campo.setdefault(campo, {})[clave] = valor


def _construir_info_cue(valores_por_campo):
    """
    Construye los items publicos del modal Info CUE para un grupo CUE.

    - Incluye un campo solo cuando tiene un unico valor no vacio en todo el CUE.
    - Omite campos con valores distintos entre anexos/snapshots del mismo CUE.
    - No expone estructuras internas de comparacion al template.
    """
    info_cue = []
    for label, campo in INFO_CUE_DETALLE_CAMPOS:
        valores = valores_por_campo.get(campo, {})
        if len(valores) != 1:
            continue
        info_cue.append({
            "label": label,
            "valor": next(iter(valores.values())),
        })
    return info_cue


def _construir_cargo_expandible(fila_normalizada, descriptores, acciones_fila):
    """
    Proyecta una fila normalizada al nodo de cargo definido por la politica.

    - Usa exclusivamente las columnas declaradas en `cargo_expandible`.
    - Mantiene `acciones_fila` como metadata aun sin uso en template.
    - Conserva los valores ya consolidados y ordenados por la grilla actual.
    - Expone los flags de historial de cantidad, observación y Estado POF como booleanos.
    """
    cargo = {
        descriptor["campo"]: _obtener_valor_politica(fila_normalizada, descriptor)
        for descriptor in descriptores
        if descriptor.get("campo") != "acciones_fila"
    }
    cargo["acciones_fila"] = acciones_fila
    cargo["cargo_ids"] = list(fila_normalizada.get("cargo_ids", []))
    cargo["tiene_modificacion_cantidad"] = bool(
        fila_normalizada.get("tiene_modificacion_cantidad")
    )
    cargo["tiene_modificacion_observacion"] = bool(
        fila_normalizada.get("tiene_modificacion_observacion")
    )
    cargo["tiene_modificacion_estado"] = bool(
        fila_normalizada.get("tiene_modificacion_estado")
    )
    return cargo


def _serializar_acciones(acciones):
    """
    Convierte la metadata de acciones a un objeto JSON liviano y estable.

    - Usa el nombre de accion como clave publica para el frontend futuro.
    - Conserva solo metadata declarativa sin ejecutar permisos ni efectos.
    - Devuelve un diccionario vacio cuando no hay acciones configuradas.
    """
    return {
        accion.get("accion", ""): {
            "alcance": accion.get("alcance", ""),
            "habilitada": bool(accion.get("habilitada", False)),
        }
        for accion in acciones
        if accion.get("accion")
    }


def _serializar_valor_json(valor):
    """
    Convierte un valor normalizado a una representacion JSON liviana y estable.

    - Devuelve cadena vacia para `None` o vacios usados por la grilla actual.
    - Conserva enteros y decimales como texto para no perder formato de negocio.
    - Evita exponer tipos Python internos en la respuesta AJAX.
    """
    if valor in (None, ""):
        return ""
    return str(valor)


def construir_grupos_operativos_detalle(*, filas_normalizadas, detalle_politicas):
    """
    Construye la estructura operativa futura del Detalle sin alterar el render actual.

    - Agrupa por `cue` y luego por `cueanexo` respetando el orden recibido.
    - Deriva `cue` y `anexo` desde `cueanexo`, que sigue siendo el dato canonico.
    - Mantiene el criterio actual de puntos: suma `total` solo para filas `AFECTADO`.
    """
    if not detalle_politicas:
        return []

    grupo_cue_descriptores = detalle_politicas.get("grupo_cue", {}).get("encabezado", ())
    grupo_anexo_descriptores = detalle_politicas.get("grupo_anexo_cuof", {}).get("resumen", ())
    cargo_descriptores = detalle_politicas.get("cargo_expandible", {}).get("columnas", ())
    acciones_grupo_cue = detalle_politicas.get("acciones_futuras_grupo_cue", ())
    acciones_grupo_anexo = detalle_politicas.get("acciones_futuras_grupo_anexo_cuof", ())
    acciones_fila = detalle_politicas.get("acciones_futuras_fila_cargo", ())

    grupos_cue = []
    grupos_cue_por_clave = {}
    grupos_anexo_por_clave = {}
    anexos_vistos_por_cue = {}
    info_cue_valores_por_clave = {}

    for fila_normalizada in filas_normalizadas:
        cueanexo = str(fila_normalizada.get("cueanexo", "") or "").strip()
        cue_derivado, anexo_derivado = _derivar_cue_y_anexo(cueanexo)
        cue = cue_derivado
        clave_cue = cue
        clave_anexo = (clave_cue, cueanexo)

        if clave_cue not in grupos_cue_por_clave:
            grupo_cue = {
                descriptor["campo"]: (
                    cue
                    if descriptor.get("campo") == "cue"
                    else _obtener_valor_politica(fila_normalizada, descriptor)
                )
                for descriptor in grupo_cue_descriptores
            }
            grupo_cue["total_anexos"] = 0
            grupo_cue["total_cargos"] = 0
            grupo_cue["total_puntos"] = Decimal("0")
            grupo_cue["anexos"] = []
            grupo_cue["acciones_grupo"] = acciones_grupo_cue
            grupos_cue_por_clave[clave_cue] = grupo_cue
            anexos_vistos_por_cue[clave_cue] = set()
            info_cue_valores_por_clave[clave_cue] = {}
            grupos_cue.append(grupo_cue)

        grupo_cue = grupos_cue_por_clave[clave_cue]
        anexos_vistos = anexos_vistos_por_cue[clave_cue]
        _registrar_valores_info_cue(
            info_cue_valores_por_clave[clave_cue],
            fila_normalizada,
        )

        if clave_anexo not in grupos_anexo_por_clave:
            grupo_anexo = {
                descriptor["campo"]: (
                    anexo_derivado
                    if descriptor.get("campo") == "anexo"
                    else _obtener_valor_politica(fila_normalizada, descriptor)
                )
                for descriptor in grupo_anexo_descriptores
                if descriptor.get("campo") != "cantidad_cargos"
            }
            grupo_anexo["cui"] = fila_normalizada.get("cui", "")
            grupo_anexo["cantidad_cargos"] = 0
            grupo_anexo["cargos"] = []
            grupo_anexo["acciones_grupo"] = acciones_grupo_anexo
            grupos_anexo_por_clave[clave_anexo] = grupo_anexo
            grupo_cue["anexos"].append(grupo_anexo)
            if cueanexo not in anexos_vistos:
                anexos_vistos.add(cueanexo)
                grupo_cue["total_anexos"] += 1

        grupo_anexo = grupos_anexo_por_clave[clave_anexo]
        grupo_anexo["cargos"].append(
            _construir_cargo_expandible(fila_normalizada, cargo_descriptores, acciones_fila)
        )
        grupo_anexo["cantidad_cargos"] += 1
        grupo_cue["total_cargos"] += 1

        if fila_normalizada.get("estado_pof_codigo") == CargoPof.EstadoPof.AFECTADO:
            grupo_cue["total_puntos"] += fila_normalizada.get("total") or Decimal("0")

    for clave_cue, grupo_cue in grupos_cue_por_clave.items():
        grupo_cue["info_cue"] = _construir_info_cue(
            info_cue_valores_por_clave.get(clave_cue, {})
        )

    return grupos_cue


def obtener_grupo_operativo_detalle(grupos_operativos_detalle, *, cueanexo, cuof):
    """
    Busca un grupo Anexo dentro de la estructura operativa ya construida.

    - Recorre los grupos CUE respetando la estructura publica actual.
    - Devuelve el grupo cuyo `cueanexo` coincide; `cuof` queda como compatibilidad de enlaces viejos.
    - Retorna `None` cuando la clave solicitada no existe en la Reunida.
    """
    cueanexo_buscado = str(cueanexo or "").strip()

    for grupo_cue in grupos_operativos_detalle:
        for grupo_anexo in grupo_cue.get("anexos", []):
            if str(grupo_anexo.get("cueanexo", "") or "").strip() == cueanexo_buscado:
                return grupo_anexo

    return None


def serializar_grupo_operativo_detalle(grupo_operativo):
    """
    Serializa un grupo Anexo/CUOF al JSON liviano del endpoint de Detalle.

    - Mantiene `cueanexo` como dato canonico y deriva `cue`/`anexo` desde el grupo.
    - Devuelve solo los cargos del grupo solicitado con sus campos operativos.
    - Expone si cada fila tiene cambios reales de Estado POF para habilitar
      el historial bajo demanda.
    - Convierte la metadata de acciones a objetos simples para consumo AJAX futuro.
    """
    if not grupo_operativo:
        return {}

    cueanexo = grupo_operativo.get("cueanexo", "")
    cue, anexo_derivado = _derivar_cue_y_anexo(cueanexo)

    return {
        "cue": cue,
        "anexo": grupo_operativo.get("anexo", anexo_derivado),
        "cueanexo": cueanexo,
        "cuof": grupo_operativo.get("cuof", ""),
        "cantidad_cargos": grupo_operativo.get("cantidad_cargos", 0),
        "acciones_grupo": _serializar_acciones(grupo_operativo.get("acciones_grupo", ())),
        "cargos": [
            {
                "cargo_ids": list(cargo.get("cargo_ids", [])),
                "tiene_modificacion_cantidad": bool(cargo.get("tiene_modificacion_cantidad")),
                "tiene_modificacion_observacion": bool(cargo.get("tiene_modificacion_observacion")),
                "tiene_modificacion_estado": bool(cargo.get("tiene_modificacion_estado")),
                "ceic": _serializar_valor_json(cargo.get("ceic", "")),
                "cargo": _serializar_valor_json(cargo.get("cargo", "")),
                "cantidad": _serializar_valor_json(cargo.get("cantidad", "")),
                "unidad_cantidad": _serializar_valor_json(cargo.get("unidad_cantidad", "")),
                "puntos_asignados": _serializar_valor_json(cargo.get("puntos_asignados", "")),
                "total": _serializar_valor_json(cargo.get("total", "")),
                "observacion": _serializar_valor_json(cargo.get("observacion", "")),
                "estado": _serializar_valor_json(cargo.get("estado", "")),
                "acciones_fila": _serializar_acciones(cargo.get("acciones_fila", ())),
            }
            for cargo in grupo_operativo.get("cargos", [])
        ],
    }
