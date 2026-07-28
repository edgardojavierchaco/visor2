import re

from django.db import connections

from .niveles import oferta_es_compatible_con_reunida
from .niveles_service import (
    NIVELES_VALIDOS,
    normalizar_nivel,
    normalizar_texto_comparable,
    obtener_nombre_nivel,
)


MATERIALIZADAS_DB = "default"

REGIONES_EDUCATIVAS_POF = (
    "R.E. 1",
    "SUB. R.E. 1-A",
    "R.E. 2",
    "SUB. R.E. 2",
    "R.E. 3",
    "SUB. R.E. 3",
    "R.E. 4-A",
    "R.E. 4-B",
    "R.E. 5",
    "SUB. R.E. 5",
    "R.E. 6",
    "R.E. 7",
    "R.E. 8-A",
    "R.E. 8-B",
    "R.E. 9",
    "R.E. 10-A",
    "R.E. 10-B",
    "R.E. 10-C",
    "SUB. R.E. 1-B",
)
_REGION_CANONICA_POR_CLAVE = {
    region.casefold(): region
    for region in REGIONES_EDUCATIVAS_POF
}
_REGION_REPETIDA_GUION_RE = re.compile(r"^(.+)-\1$")
_REGION_REPETIDA_COMA_RE = re.compile(r"^(.+),\s*\1$")


def normalizar_texto(valor):
    if valor is None:
        return ""
    return str(valor).strip()


def normalizar_region_padron(valor):
    texto = re.sub(r"\s+", " ", normalizar_texto(valor))
    if not texto:
        return ""

    for patron in (_REGION_REPETIDA_GUION_RE, _REGION_REPETIDA_COMA_RE):
        repetida = patron.fullmatch(texto)
        if repetida:
            texto = normalizar_texto(repetida.group(1))
            break

    return _REGION_CANONICA_POR_CLAVE.get(texto.casefold(), "")


def resolver_region_padron(oferta_regional, regional_actual):
    return (
        normalizar_region_padron(oferta_regional)
        or normalizar_region_padron(regional_actual)
    )


def obtener_variantes_region_padron(valor):
    region = normalizar_region_padron(valor)
    if not region:
        return ()
    return (
        region,
        f"{region}-{region}",
        f"{region}, {region}",
        f"{region},{region}",
    )


def _solo_digitos(valor):
    return re.sub(r"\D", "", normalizar_texto(valor))


def dictfetchall(cursor):
    columnas = [columna[0] for columna in cursor.description]
    return [dict(zip(columnas, fila)) for fila in cursor.fetchall()]


def normalizar_anexo(anexo):
    digitos = _solo_digitos(anexo)
    if not digitos:
        return "00"
    return digitos[-2:].zfill(2)


def construir_cueanexo_sin_guion(cue, anexo):
    cue_limpio = _solo_digitos(cue)
    if not cue_limpio:
        return ""
    return f"{cue_limpio}{normalizar_anexo(anexo)}"


def _normalizar_limite(limite):
    try:
        limite = int(limite)
    except (TypeError, ValueError):
        return 50
    if limite < 1:
        return 50
    return min(limite, 200)


def _primer_texto(*valores):
    for valor in valores:
        texto = normalizar_texto(valor)
        if texto:
            return texto
    return ""


def _normalizar_nivel_desde_textos(*valores):
    for valor in valores:
        nivel = normalizar_nivel(valor)
        if nivel:
            return nivel

    niveles_ordenados = sorted(
        NIVELES_VALIDOS,
        key=lambda codigo: len(normalizar_texto_comparable(NIVELES_VALIDOS[codigo])),
        reverse=True,
    )
    for valor in valores:
        texto = normalizar_texto_comparable(valor).replace("_", " ")
        if not texto:
            continue

        texto_con_bordes = f" {texto} "
        for codigo in niveles_ordenados:
            alias = {
                codigo.replace("_", " "),
                NIVELES_VALIDOS[codigo],
            }
            for opcion in alias:
                opcion_normalizada = normalizar_texto_comparable(opcion).replace("_", " ")
                if opcion_normalizada and f" {opcion_normalizada} " in texto_con_bordes:
                    return codigo

    return ""


def normalizar_nivel_oferta_padron(padron):
    if not isinstance(padron, dict):
        return ""

    return _normalizar_nivel_desde_textos(
        padron.get("nivel_oferta"),
        padron.get("nivel_oferta_nombre"),
        padron.get("nivel"),
        padron.get("nivel_nombre"),
        padron.get("oferta"),
        padron.get("loc_tipo_oferta"),
        padron.get("tipo_oferta"),
        padron.get("loc_ofertas_resumen"),
        padron.get("ofertas_resumen"),
        padron.get("nombre_titulo"),
        padron.get("etiqueta"),
        padron.get("acronimo"),
    )


def buscar_ofertas_padron(cueanexo=None, cue=None, cuof=None, limite=50, nivel_reunida=""):
    """
    Busca ofertas de padrón y marca sugerencias según la cabecera cuando aplica.

    - Para Reunidas usa el helper central de compatibilidad entre ofertas y nivel.
    - Si se informa nivel, conserva todas las ofertas reales y agrega `oferta_sugerida`.
    - Si no se informa nivel, mantiene el comportamiento general útil para Proyecto Especial.
    - Nunca devuelve padrón general cuando no hay criterios de búsqueda.
    """
    cueanexo_limpio = _solo_digitos(cueanexo)
    cue_limpio = _solo_digitos(cue)
    cuof_limpio = normalizar_texto(cuof)
    limite = _normalizar_limite(limite)
    nivel_reunida_normalizado = normalizar_nivel(nivel_reunida)

    filtros = []
    parametros = []

    if cueanexo_limpio:
        filtros.append(
            """
            CONCAT(
                REGEXP_REPLACE(COALESCE(vl.cue::text, ''), '[^0-9]', '', 'g'),
                RIGHT('00' || REGEXP_REPLACE(COALESCE(vl.anexo::text, ''), '[^0-9]', '', 'g'), 2)
            ) = %s
            """
        )
        parametros.append(cueanexo_limpio)

    if cue_limpio:
        filtros.append("REGEXP_REPLACE(COALESCE(vl.cue::text, ''), '[^0-9]', '', 'g') = %s")
        parametros.append(cue_limpio)

    if cuof_limpio:
        filtros.append(
            """
            COALESCE(
                NULLIF(TRIM(ol.cuof::text), ''),
                NULLIF(TRIM(vl.cuof::text), ''),
                ''
            ) = %s
            """
        )
        parametros.append(cuof_limpio)

    if not filtros:
        return []

    where_sql = " AND ".join(filtros)

    sql = f"""
        SELECT
            vl.id_localizacion AS id_localizacion,
            vl.id_establecimiento AS id_establecimiento,
            vl.cue AS cue,
            vl.anexo AS anexo,
            vl.cue_anexo AS cue_anexo,
            vl.ambito AS loc_ambito,
            vl.establecimiento AS loc_establecimiento,
            vl.establecimiento_nombre AS loc_establecimiento_nombre,
            vl.estado AS loc_estado,
            vl.estado_localizacion AS estado_localizacion,
            vl.sector AS loc_sector,
            vl.localidad AS loc_localidad,
            vl.localidad_nombre AS loc_localidad_nombre,
            vl.departamento AS loc_departamento,
            vl.departamento_nombre AS loc_departamento_nombre,
            vl.calle AS calle,
            vl.nro AS numero,
            vl.referencia AS referencia,
            vl.domicilio_ppal AS domicilio_ppal,
            vl.tipo_oferta AS loc_tipo_oferta,
            vl.ofertas_resumen AS loc_ofertas_resumen,
            vl.regional_actual AS regional_actual,
            vl.cuof AS loc_cuof,
            vl.cui AS loc_cui,
            vl.cua AS loc_cua,
            ve.nombre AS est_nombre,
            ve.estado AS estado_establecimiento,
            ve.nro_establecimiento AS nro_establecimiento,
            ve.cp_numeroestablecimiento AS cp_numeroestablecimiento,
            ve.categoria AS est_categoria,
            ve.sector AS est_sector,
            ve.localidad AS est_localidad,
            ve.departamento AS est_departamento,
            ol.id_oferta_local AS id_oferta_local,
            ol.oferta AS oferta,
            ol.nombre_titulo AS nombre_titulo,
            ol.estado AS oferta_estado,
            ol.estado_ofertalocal AS estado_ofertalocal,
            ol.jornada AS jornada,
            ol.jornada_ofertalocal AS jornada_ofertalocal,
            ol.acronimo AS acronimo,
            ol.categoria AS oferta_categoria,
            ol.cui AS oferta_cui,
            ol.cua AS oferta_cua,
            ol.cuof AS oferta_cuof,
            ol.regional AS oferta_regional,
            ol.ambito AS oferta_ambito,
            ol.sector AS oferta_sector
        FROM padroninterno.mv_localizaciones vl
        LEFT JOIN padroninterno.mv_establecimientos ve
            ON ve.id_establecimiento = vl.id_establecimiento
        LEFT JOIN padroninterno.mv_ofertaslocales ol
            ON ol.id_localizacion = vl.id_localizacion
        WHERE {where_sql}
        ORDER BY vl.cue, vl.anexo, ol.oferta
        LIMIT %s
    """
    parametros.append(limite)

    with connections[MATERIALIZADAS_DB].cursor() as cursor:
        cursor.execute(sql, parametros)
        filas = dictfetchall(cursor)

    resultados = [armar_resultado_compatible(fila) for fila in filas]
    if not nivel_reunida_normalizado:
        return resultados

    for resultado in resultados:
        resultado["oferta_sugerida"] = oferta_es_compatible_con_reunida(
            resultado.get("oferta_real") or resultado.get("oferta"),
            nivel_reunida_normalizado,
            resultado.get("acronimo"),
            resultado.get("tipo_oferta"),
            resultado.get("nivel_oferta"),
        )

    return resultados


OPCIONES_FILTROS_VISUALIZACION = {
    "region": "COALESCE(NULLIF(TRIM(ol.regional::text), ''), NULLIF(TRIM(vl.regional_actual::text), ''))",
    "localidad": "COALESCE(NULLIF(TRIM(vl.localidad_nombre::text), ''), NULLIF(TRIM(vl.localidad::text), ''), NULLIF(TRIM(ve.localidad::text), ''))",
    "departamento": "COALESCE(NULLIF(TRIM(vl.departamento_nombre::text), ''), NULLIF(TRIM(vl.departamento::text), ''), NULLIF(TRIM(ve.departamento::text), ''))",
    "ambito": "COALESCE(NULLIF(TRIM(ol.ambito::text), ''), NULLIF(TRIM(vl.ambito::text), ''))",
    "categoria": "COALESCE(NULLIF(TRIM(ol.categoria::text), ''), NULLIF(TRIM(ve.categoria::text), ''))",
    "jornada": "COALESCE(NULLIF(TRIM(ol.jornada::text), ''), NULLIF(TRIM(ol.jornada_ofertalocal::text), ''))",
    "oferta": "COALESCE(NULLIF(TRIM(ol.oferta::text), ''), NULLIF(TRIM(vl.tipo_oferta::text), ''), NULLIF(TRIM(vl.ofertas_resumen::text), ''))",
    "acronimo": "NULLIF(TRIM(ol.acronimo::text), '')",
    "estado_localizacion_padron": "NULLIF(TRIM(vl.estado_localizacion::text), '')",
    "estado_oferta_padron": "NULLIF(TRIM(ol.estado_ofertalocal::text), '')",
    "estado_establecimiento_padron": "NULLIF(TRIM(ve.estado::text), '')",
}

CATALOGOS_INGRESO_MANUAL_POF = (
    "region",
    "localidad",
    "departamento",
    "oferta",
    "acronimo",
    "ambito",
    "categoria",
    "jornada",
)


def obtener_opciones_filtros_visualizacion_padron():
    """
    Devuelve catalogos globales desde las materializadas de Padron Interno.

    Mantiene la misma normalizacion semantica que armar_resultado_compatible()
    para que los valores coincidan con lo guardado en snapshots POF.
    """
    opciones = {campo: [] for campo in OPCIONES_FILTROS_VISUALIZACION}
    from_sql = """
        FROM padroninterno.mv_localizaciones vl
        LEFT JOIN padroninterno.mv_establecimientos ve
            ON ve.id_establecimiento = vl.id_establecimiento
        LEFT JOIN padroninterno.mv_ofertaslocales ol
            ON ol.id_localizacion = vl.id_localizacion
    """

    with connections[MATERIALIZADAS_DB].cursor() as cursor:
        for campo, expresion in OPCIONES_FILTROS_VISUALIZACION.items():
            if campo == "region":
                cursor.execute(f"""
                    SELECT DISTINCT
                        NULLIF(TRIM(ol.regional::text), '') AS oferta_regional,
                        NULLIF(TRIM(vl.regional_actual::text), '') AS regional_actual
                    {from_sql}
                """)
                regiones_presentes = {
                    resolver_region_padron(oferta_regional, regional_actual)
                    for oferta_regional, regional_actual in cursor.fetchall()
                    if resolver_region_padron(oferta_regional, regional_actual)
                }
                opciones[campo] = [
                    region
                    for region in REGIONES_EDUCATIVAS_POF
                    if region in regiones_presentes
                ]
                continue

            sql = f"""
                SELECT valor
                FROM (
                    SELECT DISTINCT {expresion} AS valor
                    {from_sql}
                ) opciones
                WHERE valor IS NOT NULL AND valor <> ''
                ORDER BY valor
            """
            cursor.execute(sql)
            opciones[campo] = [
                normalizar_texto(fila[0])
                for fila in cursor.fetchall()
                if normalizar_texto(fila[0])
            ]

    return opciones


def obtener_catalogos_padron_ingreso_manual_pof():
    """
    Devuelve catálogos controlados para ingreso manual POF desde las mismas
    materializadas usadas por Visualización de Cargos por Localización.
    """
    opciones = obtener_opciones_filtros_visualizacion_padron()
    return {
        campo: opciones.get(campo, [])
        for campo in CATALOGOS_INGRESO_MANUAL_POF
    }


def resolver_fila_padron_oficial(cueanexo, cuof, id_localizacion=None, id_oferta_local=None):
    """
    Resuelve una única fila real de padrón para validaciones de guardado backend.

    - Busca siempre por `cueanexo + cuof` para no confiar en descripciones enviadas por frontend.
    - Usa `id_oferta_local` e `id_localizacion` solo como apoyo para desambiguar resultados reales.
    - Devuelve error claro si no existe una fila segura o si la selección enviada no coincide con padrón.
    """
    resultados = buscar_ofertas_padron(cueanexo=cueanexo, cuof=cuof)
    if not resultados:
        return {
            "ok": False,
            "fila": None,
            "mensaje": "La localización/oferta indicada no existe en el padrón materializado.",
        }

    id_oferta_local_texto = normalizar_texto(id_oferta_local)
    if id_oferta_local_texto:
        resultados_por_oferta = [
            resultado
            for resultado in resultados
            if normalizar_texto(resultado.get("id_oferta_local")) == id_oferta_local_texto
        ]
        if len(resultados_por_oferta) == 1:
            return {"ok": True, "fila": resultados_por_oferta[0], "mensaje": ""}
        if not resultados_por_oferta:
            return {
                "ok": False,
                "fila": None,
                "mensaje": "La oferta seleccionada no coincide con una fila real del padrón materializado.",
            }

    id_localizacion_texto = normalizar_texto(id_localizacion)
    if id_localizacion_texto:
        resultados_por_localizacion = [
            resultado
            for resultado in resultados
            if normalizar_texto(resultado.get("id_localizacion")) == id_localizacion_texto
        ]
        if len(resultados_por_localizacion) == 1:
            return {"ok": True, "fila": resultados_por_localizacion[0], "mensaje": ""}
        if not resultados_por_localizacion:
            return {
                "ok": False,
                "fila": None,
                "mensaje": "La localización seleccionada no coincide con una fila real del padrón materializado.",
            }

    if len(resultados) == 1:
        return {"ok": True, "fila": resultados[0], "mensaje": ""}

    return {
        "ok": False,
        "fila": None,
        "mensaje": (
            "La búsqueda por CUEANEXO y CUOF devolvió más de una fila real del padrón y no se pudo resolver "
            "de forma segura."
        ),
    }


def armar_resultado_compatible(row):
    anexo = normalizar_anexo(row.get("anexo"))
    padron_cueanexo = construir_cueanexo_sin_guion(row.get("cue"), anexo)
    id_oferta_local = row.get("id_oferta_local")
    id_localizacion = row.get("id_localizacion")
    oferta_real = normalizar_texto(row.get("oferta"))
    tipo_oferta = _primer_texto(row.get("loc_tipo_oferta"), row.get("loc_ofertas_resumen"))
    nivel_oferta = normalizar_nivel_oferta_padron(row)

    return {
        "id": id_oferta_local or id_localizacion,
        "id_localizacion": id_localizacion,
        "id_establecimiento": row.get("id_establecimiento"),
        "id_oferta_local": id_oferta_local,
        "padron_cueanexo": padron_cueanexo,
        "cueanexo": padron_cueanexo,
        "cue_anexo": normalizar_texto(row.get("cue_anexo")),
        "cue": normalizar_texto(row.get("cue")),
        "anexo": anexo,
        "nom_est": _primer_texto(
            row.get("loc_establecimiento_nombre"),
            row.get("loc_establecimiento"),
            row.get("est_nombre"),
        ),
        "nro_est": _primer_texto(row.get("nro_establecimiento"), row.get("cp_numeroestablecimiento")),
        "acronimo": normalizar_texto(row.get("acronimo")),
        "oferta_real": oferta_real,
        "oferta": _primer_texto(oferta_real, tipo_oferta),
        "tipo_oferta": tipo_oferta,
        "nivel_oferta": nivel_oferta,
        "nivel_oferta_nombre": obtener_nombre_nivel(nivel_oferta, ""),
        "etiqueta": normalizar_texto(row.get("nombre_titulo")),
        "ambito": _primer_texto(row.get("oferta_ambito"), row.get("loc_ambito")),
        "sector": _primer_texto(row.get("oferta_sector"), row.get("loc_sector"), row.get("est_sector")),
        "region_loc": resolver_region_padron(
            row.get("oferta_regional"),
            row.get("regional_actual"),
        ),
        "ref_loc": normalizar_texto(row.get("referencia")),
        "domicilio_ppal": normalizar_texto(row.get("domicilio_ppal")),
        "calle": normalizar_texto(row.get("calle")),
        "numero": normalizar_texto(row.get("numero")),
        "localidad": _primer_texto(
            row.get("loc_localidad_nombre"),
            row.get("loc_localidad"),
            row.get("est_localidad"),
        ),
        "departamento": _primer_texto(
            row.get("loc_departamento_nombre"),
            row.get("loc_departamento"),
            row.get("est_departamento"),
        ),
        "estado_loc": normalizar_texto(row.get("estado_localizacion")),
        "est_oferta": normalizar_texto(row.get("estado_ofertalocal")),
        "estado_est": normalizar_texto(row.get("estado_establecimiento")),
        "categoria": _primer_texto(row.get("oferta_categoria"), row.get("est_categoria")),
        "cui_loc": _primer_texto(row.get("oferta_cui"), row.get("loc_cui")),
        "cua_loc": _primer_texto(row.get("oferta_cua"), row.get("loc_cua")),
        "cuof_loc": _primer_texto(row.get("oferta_cuof"), row.get("loc_cuof")),
        "jornada": _primer_texto(row.get("jornada"), row.get("jornada_ofertalocal")),
    }


def asegurar_resultado_compatible(row):
    if not isinstance(row, dict):
        return {}
    if "padron_cueanexo" in row and "estado_loc" in row and "cuof_loc" in row:
        return row
    return armar_resultado_compatible(row)


def armar_localizacion_payload(row):
    resultado = asegurar_resultado_compatible(row)
    return {
        "cueanexo": resultado.get("padron_cueanexo", ""),
        "cuof": resultado.get("cuof_loc", ""),
        "cui": resultado.get("cui_loc", ""),
    }


def armar_snapshot_payload(row):
    resultado = asegurar_resultado_compatible(row)
    ubicacion = _primer_texto(
        resultado.get("ref_loc"),
        resultado.get("domicilio_ppal"),
        resultado.get("calle"),
    )
    ubicacion_completa = ", ".join(
        parte for parte in [ubicacion, resultado.get("localidad"), resultado.get("departamento")] if parte
    )

    return {
        "origen_datos": "PADRON",
        "estado_padron": "VIGENTE",
        "estado_localizacion_padron": resultado.get("estado_loc", ""),
        "estado_oferta_padron": resultado.get("est_oferta", ""),
        "estado_establecimiento_padron": resultado.get("estado_est", ""),
        "oferta": resultado.get("oferta", ""),
        "acronimo": resultado.get("acronimo", ""),
        "nombre_establecimiento": resultado.get("nom_est", ""),
        "numero_establecimiento": resultado.get("nro_est", ""),
        "region": resultado.get("region_loc", ""),
        "localidad": resultado.get("localidad", ""),
        "departamento": resultado.get("departamento", ""),
        "ambito": resultado.get("ambito", ""),
        "categoria": resultado.get("categoria", ""),
        "jornada": resultado.get("jornada", ""),
        "ubicacion": ubicacion,
        "ubicacion_localidad_departamento": ubicacion_completa,
        "datos_padron": resultado,
    }
