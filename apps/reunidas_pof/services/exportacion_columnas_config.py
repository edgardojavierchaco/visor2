from .niveles_service import normalizar_nivel, normalizar_texto_comparable

# Políticas de repetición de columnas.
#
# Implementadas actualmente en la proyección de Exportar Reunida:
# - REPETIR_SIEMPRE: la columna se muestra en todas las filas.
# - REPETIR_POR_CUEANEXO: la columna se muestra solo en la primera fila
#   del mismo CUEANEXO/anexo y se vacía en las siguientes.
#
# Reservadas / legacy:
# - REPETIR_POR_CUE
# - REPETIR_POR_GRUPO_TOTAL
#
# Estas dos últimas quedan declaradas para compatibilidad o uso futuro,
# pero no deben asignarse a columnas activas hasta implementar su lógica
# correspondiente en exportacion_reunida.py.


REPETIR_SIEMPRE = "siempre"
REPETIR_POR_CUEANEXO = "por_cueanexo"
REPETIR_POR_CUE = "por_cue"
REPETIR_POR_GRUPO_TOTAL = "por_grupo_total"

REPETICIONES_VALIDAS = {
    REPETIR_SIEMPRE,
    REPETIR_POR_CUEANEXO,
    REPETIR_POR_CUE,
    REPETIR_POR_GRUPO_TOTAL,
}

SOURCES_EXPORTACION = {
    "anio": "Año",
    "proyecto_especial": "Proyecto especial",
    "resolucion": "Resolución",
    "region": "Región",
    "region_anexo": "Región anexo",
    "ex_region": "Ex región",
    "cuof": "CUOF",
    "sub_cuof": "SUB CUOF",
    "cue": "CUE",
    "subcue": "SUBCUE",
    "cueanexo": "CUEANEXO",
    "cue_bloque_final": "CUE bloque final",
    "cue_anexo": "CUE anexo",
    "cui": "CUI",
    "cui_bloque_final": "CUI bloque final",
    "cui_anexo": "CUI anexo",
    "cue_cui": "CUE - CUI",
    "numero_establecimiento": "Número de establecimiento",
    "establecimiento": "Establecimiento",
    "nombre": "Nombre",
    "categoria": "Categoría",
    "jornada": "Jornada",
    "categoria_jornada": "Categoría - Jornada",
    "modalidad": "Modalidad",
    "tipo_anexo": "Tipo anexo",
    "ambito": "Ámbito",
    "ubicacion": "Ubicación",
    "ubicacion_anexo": "Ubicación anexo",
    "domicilio": "Domicilio",
    "localidad": "Localidad",
    "localidad_anexo": "Localidad anexo",
    "departamento": "Departamento",
    "departamento_anexo": "Departamento anexo",
    "ubicacion_completa": "Ubicación - Localidad - Departamento",
    "zona": "Zona",
    "ceic": "CEIC",
    "cargo": "Cargo",
    "cantidad": "Cantidad",
    "cantidad_cargos": "Cantidad cargos",
    "cantidad_horas": "Cantidad horas",
    "puntos": "Puntos",
    "total": "Total",
    "total_general": "Total general",
    "total_general_exportacion": "Total general exportación",
    "total_horas_catedra": "Total horas cátedra",
    "puntos_horas_catedra": "Puntos horas cátedra",
    "total_puntos": "Total puntos",
    "blank": "Columna vacía",
    "anexo": "Anexo",
    "oferta": "Oferta",
    "unidad": "Unidad",
    "localizacion_id": "ID localización",
    "unidad_cantidad": "Unidad cantidad",
    "cargo_id": "ID cargo",
    "estado_pof_codigo": "Código estado POF",
    "estado_pof": "Estado POF",
}

SOURCES_REPETIR_SIEMPRE = {
    "oferta",
    "estado_oferta",
    "ceic",
    "cargo",
    "cargo_descripcion",
    "denominacion_cargo",
    "cantidad",
    "cantidad_cargos",
    "cantidad_horas",
    "unidad",
    "unidad_cantidad",
    "horas",
    "puntos",
    "puntos_asignados",
    "puntos_horas_catedra",
    "total",
    "total_horas_catedra",
    "total_puntos",
    "observacion_cargo",
    "estado_cargo",
}

CUEANEXO_PRINCIPAL_LABEL = "CUE-Anexo"
SOURCES_EQUIVALENTES_CUEANEXO = {
    "cueanexo",
    "subcue",
}

_ALIAS_NIVELES = {
    "ED FISICA": "FISICA",
    "ED. FISICA": "FISICA",
    "EDUCACION FISICA": "FISICA",
    "ED ESPECIAL": "ESPECIAL",
    "ED. ESPECIAL": "ESPECIAL",
    "EDUCACION ESPECIAL": "ESPECIAL",
    "SECUNDARIO": "SECUNDARIA",
    "TECNICA": "SECUNDARIA_TECNICA",
}


def _normalizar_codigo_config(nivel_codigo):
    codigo = normalizar_nivel(nivel_codigo)
    if codigo in COLUMNAS_REUNIDA_POR_NIVEL:
        return codigo

    nivel_comparable = normalizar_texto_comparable(nivel_codigo)
    return _ALIAS_NIVELES.get(nivel_comparable, "PRIMARIA")


def _repeticion_default(source):
    if source == "total_general":
        return REPETIR_POR_CUE
    if source in SOURCES_REPETIR_SIEMPRE:
        return REPETIR_SIEMPRE
    return REPETIR_POR_CUEANEXO


def _col(nivel_codigo, label, source, id_suffix=None, repetir=None, visible_default=True):
    return {
        "id": f"{nivel_codigo.lower()}_{id_suffix or source}",
        "label": label,
        "source": source,
        "repetir": repetir or _repeticion_default(source),
        "visible_default": visible_default,
    }


def _columnas_nivel(nivel_codigo, columnas):
    return tuple(_col(nivel_codigo, *columna) for columna in columnas)


def _marcar_columna_cueanexo_principal(columna):
    """
    Normaliza la columna canonica de CUE-Anexo para reuse en todos los niveles.

    - Reetiqueta columnas equivalentes como `CUE-Anexo` sin duplicar la fuente.
    - Fuerza el source a `cueanexo` para usar siempre el dato canonico real.
    - La deja visible y requerida para preview y Excel.
    """
    columna_normalizada = columna.copy()
    columna_normalizada["label"] = CUEANEXO_PRINCIPAL_LABEL
    columna_normalizada["source"] = "cueanexo"
    columna_normalizada["visible_default"] = True
    columna_normalizada["required"] = True
    return columna_normalizada


def _construir_columna_cueanexo_principal(nivel_codigo):
    """
    Crea la columna principal de CUE-Anexo cuando el nivel no trae una equivalente.

    - Usa el dato canonico `cueanexo` como fuente unica.
    - La ubica como columna visible obligatoria.
    - Mantiene el resto de la configuracion historica intacta.
    """
    columna = _col(
        nivel_codigo,
        CUEANEXO_PRINCIPAL_LABEL,
        "cueanexo",
        id_suffix="cueanexo_principal",
    )
    columna["required"] = True
    return columna


def _normalizar_columnas_cueanexo_principal(nivel_codigo, columnas):
    """
    Inserta `CUE-Anexo` como primera columna visible sin duplicar equivalentes directos.

    - Reutiliza una columna existente si ya expone `cueanexo` o `subcue`.
    - Si no existe, agrega una nueva columna canonica al inicio.
    - Conserva el resto del orden y labels historicos del nivel.
    """
    columnas_normalizadas = []
    columna_principal = None

    for columna in columnas:
        columna_copia = columna.copy()
        columna_copia.setdefault("required", False)
        if (
            columna_principal is None
            and columna_copia.get("source") in SOURCES_EQUIVALENTES_CUEANEXO
        ):
            columna_principal = _marcar_columna_cueanexo_principal(columna_copia)
            continue
        columnas_normalizadas.append(columna_copia)

    if columna_principal is None:
        columna_principal = _construir_columna_cueanexo_principal(nivel_codigo)

    return [columna_principal, *columnas_normalizadas]


COLUMNAS_REUNIDA_POR_NIVEL = {
    "PRIMARIA": _columnas_nivel(
        "PRIMARIA",
        (
            ("Región", "region"),
            ("Nº", "numero_establecimiento"),
            ("CUOF", "cuof"),
            (" CUE      CUI", "cue_cui"),
            ("Categoría - Jornada", "categoria_jornada"),
            ("    Nombre", "nombre"),
            (" Ubicación - Localidad - Departamento", "ubicacion_completa"),
            ("CEIC", "ceic"),
            ("Cantidad", "cantidad"),
            ("Cargos y horas cátedra", "cargo"),
            ("Puntos Asignados", "puntos"),
            ("Total", "total"),
            ("Total  General", "total_general"),
            ("Zona", "zona"),
            ("Categoría", "categoria"),
            ("Jornada", "jornada"),
            (" Ubicación", "ubicacion"),
            ("Localidad", "localidad"),
            ("Departamento", "departamento"),
            ("Región", "region_anexo"),
            ("CUE", "cue_bloque_final"),
            ("SUBCUE", "subcue"),
            ("CUI", "cui_bloque_final"),
            ("N Anexo", "anexo"),
            ("CUE", "cue_anexo"),
            ("CUI", "cui_anexo"),
            (" Ubicación", "ubicacion_anexo"),
            ("Localidad", "localidad_anexo"),
            ("Departamento", "departamento_anexo"),
        ),
    ),
    "FISICA": _columnas_nivel(
        "FISICA",
        (
            ("Región", "region"),
            ("CUOF", "cuof"),
            ("CUE", "cue"),
            ("CUI", "cui"),
            ("Centro de Educación Física Nº", "numero_establecimiento"),
            ("Nombre", "nombre"),
            ("Categoría", "categoria"),
            ("Ambito", "ambito"),
            ("Ubicación  -  Localidad  -  Departamento", "ubicacion_completa"),
            ("Domicilio", "domicilio"),
            ("Localidad", "localidad"),
            ("Departamento", "departamento"),
            ("CEIC", "ceic"),
            ("Cantidad ", "cantidad"),
            ("Cargos y Horas Cátedra", "cargo"),
            ("Puntos Asignados", "puntos"),
            ("Total", "total"),
            ("Total General", "total_general"),
        ),
    ),
    "BIBLIOTECA": _columnas_nivel(
        "BIBLIOTECA",
        (
            ("CUOF", "cuof"),
            ("SUB CUOF", "sub_cuof"),
            ("CUE", "cue"),
            ("CUI", "cui"),
            ("BP N°", "numero_establecimiento"),
            ("Nombre", "nombre"),
            ("Modalidad", "modalidad"),
            ("Categoría - Jornada", "categoria_jornada"),
            ("Ubicación - Localidad - Departamento", "ubicacion_completa"),
            ("CEIC", "ceic"),
            ("Cantidad", "cantidad"),
            ("Denominación Cargo", "cargo"),
            ("Puntos ", "puntos"),
            ("Total", "total"),
            ("Total general", "total_general"),
        ),
    ),
    "TERCIARIO": _columnas_nivel(
        "TERCIARIO",
        (
            ("Reg.", "region"),
            ("CUOF", "cuof"),
            ("       CUE    -     CUI", "cue_cui"),
            ("Establecimiento", "establecimiento"),
            ("Ubicación - Localidad - Departamento", "ubicacion_completa"),
            ("Ubicación", "ubicacion"),
            ("Localidad", "localidad"),
            ("Departamento", "departamento"),
            ("CEIC", "ceic"),
            ("Cantidad", "cantidad"),
            ("Cargos y Horas cátedras", "cargo"),
            ("Puntos Asignados", "puntos"),
            ("Total", "total"),
            ("Total  General", "total_general"),
            ("Zona", "zona"),
        ),
    ),
    "INICIAL": _columnas_nivel(
        "INICIAL",
        (
            ("Región", "region"),
            ("CUOF", "cuof"),
            ("SUB CUOF", "sub_cuof"),
            ("CUE", "cue"),
            ("SUB CUE", "subcue"),
            ("CUI", "cui"),
            ("ESTAB. Nº", "numero_establecimiento"),
            ("NOMBRE", "nombre"),
            ("TIPO", "tipo_anexo"),
            ("CATEGORÍA", "categoria"),
            ("JORNADA", "jornada"),
            ("UBICACIÓN - LOCALIDAD - DEPARTAMENTO", "ubicacion_completa"),
            ("CEIC", "ceic"),
            ("DENOMINACIÓN DEL CARGO", "cargo"),
            ("CANTIDAD CARGOS", "cantidad_cargos"),
            ("Puntos Asignados", "puntos"),
            ("Total", "total"),
            ("Total general", "total_general"),
            ("Localidad", "localidad"),
            ("Departamento", "departamento"),
            ("Zona", "zona"),
        ),
    ),
    "ADULTOS": _columnas_nivel(
        "ADULTOS",
        (
            ("Región", "region"),
            ("CUOF", "cuof"),
            ("CUE", "cue"),
            ("SUB-CUE", "subcue"),
            ("CUI", "cui"),
            ("Nº", "numero_establecimiento"),
            ("Nombre", "nombre"),
            ("Categoría", "categoria"),
            ("Jornada", "jornada"),
            ("  ---", "tipo_anexo"),
            ("      Ubicación - Localidad - Departamento", "ubicacion_completa"),
            ("CEIC", "ceic"),
            ("Cantidad", "cantidad"),
            ("Denominación del Cargo", "cargo"),
            ("Puntos", "puntos"),
            ("Total Puntos", "total_puntos"),
            ("Total General", "total_general"),
        ),
    ),
    "ESPECIAL": _columnas_nivel(
        "ESPECIAL",
        (
            ("exR", "ex_region"),
            ("Región", "region"),
            ("CUOF", "cuof"),
            ("CUE", "cue"),
            ("SUBCUE", "subcue"),
            ("CUI", "cui"),
            ("Establecimiento", "establecimiento"),
            ("Nombre ", "nombre"),
            ("Categoría", "categoria"),
            ("Modalidad", "modalidad"),
            ("Jornada", "jornada"),
            ("Ambito", "ambito"),
            ("Domicilio - Localidad - Departamento", "ubicacion_completa"),
            ("CEIC", "ceic"),
            ("Cargo", "cargo"),
            ("Puntos Asignados", "puntos"),
        ),
    ),
    "SECUNDARIA_TECNICA": _columnas_nivel(
        "SECUNDARIA_TECNICA",
        (
            ("Región", "region"),
            ("CUOF", "cuof"),
            ("CUE", "cue"),
            ("CUI", "cui"),
            ("Estab.Nº", "numero_establecimiento"),
            ("Categoría", "categoria"),
            ("Modalidad", "modalidad"),
            ("Nombre", "nombre"),
            ("Ubicación - Localidad - Departamento", "ubicacion_completa"),
            ("Ubicación", "ubicacion"),
            ("Localidad", "localidad"),
            ("Departamento", "departamento"),
            ("CEIC", "ceic"),
            ("Cantidad", "cantidad"),
            ("Denominación del Cargo", "cargo"),
            ("Puntos Asignados", "puntos"),
            ("Total", "total"),
            ("Total Horas Cátedra", "total_horas_catedra"),
            ("Puntos Horas Cátedra", "puntos_horas_catedra"),
            ("Total Puntos", "total_puntos"),
            ("Zona", "zona"),
        ),
    ),
    "SECUNDARIA": _columnas_nivel(
        "SECUNDARIA",
        (
            ("REGIÓN ", "region"),
            ("CUOF", "cuof"),
            ("SUB CUOF", "sub_cuof"),
            ("CUE", "cue"),
            ("SUBCUE", "subcue"),
            ("CUI", "cui"),
            ("Establ. N° ", "numero_establecimiento"),
            ("CATEGORÍA", "categoria"),
            ("MODALIDAD", "modalidad"),
            ("NOMBRE", "nombre"),
            ("UBICACIÓN - LOCALIDAD - DEPARTAMENTO", "ubicacion_completa"),
            ("Ubicación", "ubicacion"),
            ("Localidad", "localidad"),
            ("Departamento", "departamento"),
            ("CEIC", "ceic"),
            ("DENOMINACIÓN DEL CARGO", "cargo"),
            ("CANTIDAD CARGOS", "cantidad_cargos"),
            ("CANTIDAD HORAS", "cantidad_horas"),
            ("PUNTOS", "puntos"),
            ("TOTAL PUNTOS", "total_puntos"),
            ("TOTAL PUNTOS CARGOS/HORAS CÁTEDRA", "total_general"),
            ("ZONA", "zona"),
        ),
    ),
}

_SCHEMA_METADATA = {
    "PRIMARIA": {
        "titulo": "PRIMARIA",
        "grupo": ["cueanexo", "cuof"],
        "grupo_total_general": ["cue"],
        "vaciar_repetidos": [
            "region",
            "numero_establecimiento",
            "cuof",
            "cue_cui",
            "categoria_jornada",
            "nombre",
            "ubicacion_completa",
            "zona",
            "categoria",
            "jornada",
            "ubicacion",
            "localidad",
            "departamento",
            "region_anexo",
            "cue_bloque_final",
            "subcue",
            "cui_bloque_final",
            "anexo",
            "cue_anexo",
            "cui_anexo",
            "ubicacion_anexo",
            "localidad_anexo",
            "departamento_anexo",
            "total_general",
        ],
    },
    "FISICA": {
        "titulo": "ED. FISICA",
        "grupo": ["cueanexo", "cuof"],
        "grupo_total_general": ["cue", "cuof"],
        "vaciar_repetidos": [
            "region",
            "cuof",
            "cue",
            "cui",
            "numero_establecimiento",
            "nombre",
            "categoria",
            "ambito",
            "ubicacion_completa",
            "domicilio",
            "localidad",
            "departamento",
            "total_general",
        ],
    },
    "BIBLIOTECA": {
        "titulo": "BIBLIOTECA",
        "grupo": ["cueanexo", "cuof"],
        "grupo_total_general": ["cue", "cuof"],
        "vaciar_repetidos": [
            "cuof",
            "sub_cuof",
            "cue",
            "cui",
            "numero_establecimiento",
            "nombre",
            "modalidad",
            "categoria_jornada",
            "ubicacion_completa",
            "total_general",
        ],
    },
    "TERCIARIO": {
        "titulo": "TERCIARIO",
        "grupo": ["cueanexo", "cuof"],
        "grupo_total_general": ["cue", "cuof"],
        "vaciar_repetidos": [
            "region",
            "cuof",
            "cue_cui",
            "establecimiento",
            "ubicacion_completa",
            "ubicacion",
            "localidad",
            "departamento",
            "zona",
            "total_general",
        ],
    },
    "INICIAL": {
        "titulo": "INICIAL",
        "grupo": ["cueanexo", "cuof"],
        "grupo_total_general": ["cue"],
        "vaciar_repetidos": [
            "region",
            "cuof",
            "sub_cuof",
            "cue",
            "subcue",
            "cui",
            "numero_establecimiento",
            "nombre",
            "tipo_anexo",
            "categoria",
            "jornada",
            "ubicacion_completa",
            "localidad",
            "departamento",
            "zona",
            "total_general",
        ],
    },
    "ADULTOS": {
        "titulo": "ADULTOS",
        "grupo": ["cueanexo", "cuof"],
        "grupo_total_general": ["cue", "cuof"],
        "vaciar_repetidos": [
            "region",
            "cuof",
            "cue",
            "subcue",
            "cui",
            "numero_establecimiento",
            "nombre",
            "categoria",
            "jornada",
            "tipo_anexo",
            "ubicacion_completa",
            "total_general",
        ],
    },
    "ESPECIAL": {
        "titulo": "ED. ESPECIAL",
        "grupo": ["cueanexo", "cuof"],
        "grupo_total_general": ["cue", "cuof"],
        "vaciar_repetidos": [
            "ex_region",
            "region",
            "cuof",
            "cue",
            "subcue",
            "cui",
            "establecimiento",
            "nombre",
            "categoria",
            "modalidad",
            "jornada",
            "ambito",
            "ubicacion_completa",
        ],
    },
    "SECUNDARIA_TECNICA": {
        "titulo": "TÉCNICA",
        "grupo": ["cueanexo", "cuof"],
        "grupo_total_general": ["cue"],
        "vaciar_repetidos": [
            "region",
            "cuof",
            "cue",
            "cui",
            "numero_establecimiento",
            "categoria",
            "modalidad",
            "nombre",
            "ubicacion_completa",
            "ubicacion",
            "localidad",
            "departamento",
            "zona",
            "total_horas_catedra",
            "puntos_horas_catedra",
            "total_puntos",
        ],
    },
    "SECUNDARIA": {
        "titulo": "SECUNDARIO",
        "grupo": ["cueanexo", "cuof"],
        "grupo_total_general": ["cue", "cuof"],
        "vaciar_repetidos": [
            "region",
            "cuof",
            "sub_cuof",
            "cue",
            "subcue",
            "cui",
            "numero_establecimiento",
            "categoria",
            "modalidad",
            "nombre",
            "ubicacion_completa",
            "ubicacion",
            "localidad",
            "departamento",
            "zona",
            "total_general",
        ],
    },
}


def _copia_columna_config(columna):
    columna_copia = columna.copy()
    columna_copia.setdefault("required", False)
    return columna_copia


def _columna_para_template(columna):
    columna_template = columna.copy()
    columna_template["key"] = columna["id"]
    columna_template["titulo"] = columna["label"]
    columna_template["visible"] = columna["visible_default"]
    return columna_template


def _columna_para_schema_legacy(columna):
    columna_legacy = columna.copy()
    columna_legacy["key"] = columna["source"]
    return columna_legacy


def obtener_codigo_config_columnas(nivel_codigo):
    return _normalizar_codigo_config(nivel_codigo)


def obtener_columnas_config_nivel(nivel_codigo):
    codigo = obtener_codigo_config_columnas(nivel_codigo)
    columnas = [
        _copia_columna_config(columna)
        for columna in COLUMNAS_REUNIDA_POR_NIVEL[codigo]
    ]
    return _normalizar_columnas_cueanexo_principal(codigo, columnas)


def obtener_columnas_disponibles_nivel(nivel_codigo):
    return [
        _columna_para_template(columna)
        for columna in obtener_columnas_config_nivel(nivel_codigo)
    ]


def obtener_columnas_default_ids(nivel_codigo):
    return [
        columna["id"]
        for columna in obtener_columnas_config_nivel(nivel_codigo)
        if columna["visible_default"]
    ]


def obtener_ids_columnas_visible_col(nivel_codigo, valores_visible_col):
    columnas = obtener_columnas_config_nivel(nivel_codigo)
    valores = {
        str(valor or "").strip()
        for valor in valores_visible_col
        if str(valor or "").strip()
    }

    if not valores:
        return obtener_columnas_default_ids(nivel_codigo)

    return [
        columna["id"]
        for columna in columnas
        if columna["id"] in valores or columna["source"] in valores
    ]


def obtener_columnas_por_ids(nivel_codigo, ids):
    ids_set = set(ids)
    return [
        _columna_para_template(columna)
        for columna in obtener_columnas_config_nivel(nivel_codigo)
        if columna["id"] in ids_set
    ]


def obtener_labels_columnas_config(nivel_codigo):
    return [
        columna["label"]
        for columna in obtener_columnas_config_nivel(nivel_codigo)
    ]


def construir_schema_legacy(nivel_codigo):
    codigo = obtener_codigo_config_columnas(nivel_codigo)
    columnas_config = obtener_columnas_config_nivel(codigo)
    metadata = _SCHEMA_METADATA[codigo].copy()
    metadata["grupo_total_general"] = ["cue"]
    return {
        "titulo": metadata["titulo"],
        "columnas": [
            _columna_para_schema_legacy(columna)
            for columna in columnas_config
        ],
        "grupo": list(metadata["grupo"]),
        "grupo_total_general": list(metadata["grupo_total_general"]),
        "vaciar_repetidos": list(metadata["vaciar_repetidos"]),
    }


def construir_export_schemas_legacy_desde_config():
    return {
        codigo: construir_schema_legacy(codigo)
        for codigo in COLUMNAS_REUNIDA_POR_NIVEL
    }


EXPORT_SCHEMAS = construir_export_schemas_legacy_desde_config()


def obtener_schema_exportacion(nivel_codigo):
    return EXPORT_SCHEMAS[obtener_codigo_config_columnas(nivel_codigo)]


def obtener_columnas_schema(nivel_codigo):
    return list(obtener_schema_exportacion(nivel_codigo)["columnas"])


def obtener_labels_columnas(nivel_codigo):
    return [columna["label"] for columna in obtener_columnas_schema(nivel_codigo)]


def obtener_keys_columnas(nivel_codigo):
    return [columna["key"] for columna in obtener_columnas_schema(nivel_codigo)]


def validar_configuracion_columnas():
    errores = []

    for nivel_codigo, columnas in COLUMNAS_REUNIDA_POR_NIVEL.items():
        ids = set()
        for indice, columna in enumerate(columnas, start=1):
            prefijo = f"{nivel_codigo} columna {indice}"
            columna_id = columna.get("id", "")
            label = columna.get("label", "")
            source = columna.get("source", "")
            repetir = columna.get("repetir", "")

            if not columna_id:
                errores.append(f"{prefijo}: id vacío")
            elif columna_id in ids:
                errores.append(f"{prefijo}: id duplicado {columna_id}")
            ids.add(columna_id)

            if not label:
                errores.append(f"{prefijo}: label vacío")

            if not source:
                errores.append(f"{prefijo}: source vacío")
            elif source not in SOURCES_EXPORTACION:
                errores.append(f"{prefijo}: source no declarado {source}")

            if repetir not in REPETICIONES_VALIDAS:
                errores.append(f"{prefijo}: política repetir inválida {repetir}")

            if not isinstance(columna.get("visible_default"), bool):
                errores.append(f"{prefijo}: visible_default debe ser bool")

    return errores
