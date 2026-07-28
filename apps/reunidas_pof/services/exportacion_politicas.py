import re

from .grilla_pof.columnas import obtener_clave_columna


_CAMPOS_CLAVE_SECCION = {
    "PRIMARIA": ("N", "CUOF", "CUE - CUI", "Nombre"),
    "INICIAL": ("ESTAB. N", "CUOF", "CUE", "SUB CUE", "CUI", "NOMBRE", "TIPO"),
    "ADULTOS": ("CUOF", "CUE", "SUB-CUE", "CUI", "N", "Nombre"),
    "TERCIARIO": ("CUOF", "CUE - CUI", "Establecimiento"),
    "BIBLIOTECA": ("CUOF", "BP", "CUE", "CUI", "Nombre"),
    "FISICA": ("CUOF", "CUE", "CUI", "Centro de Educacion Fisica N"),
    "ESPECIAL": ("CUOF", "CUE", "SUBCUE", "CUI", "Establecimiento"),
}

_CAMPOS_TITULO_SECCION = {
    "PRIMARIA": ("N", "Nombre", "CUE - CUI"),
    "INICIAL": ("ESTAB. N", "NOMBRE", "TIPO"),
    "ADULTOS": ("N", "Nombre", "Sede / Anexo"),
    "TERCIARIO": ("Establecimiento", "CUE - CUI"),
    "BIBLIOTECA": ("BP", "Nombre"),
    "FISICA": ("Centro de Educacion Fisica N", "Nombre"),
    "ESPECIAL": ("Establecimiento", "Nombre"),
}

_CAMPOS_CLAVE_SECCION_FALLBACK = ("CUOF", "CUE", "CUI")
_NIVELES_AGRUPADOS_POR_CUE_ANEXO = {"PRIMARIA", "INICIAL"}


def _texto_orden(valor):
    """
    Normaliza un valor textual para usarlo como clave de orden estable.

    - Convierte `None` en cadena vacia.
    - Elimina espacios laterales.
    - Mantiene el contenido listo para comparacion lexicografica.
    """
    return str(valor or "").strip()


def _entero_orden(valor):
    """
    Convierte una clave potencialmente numerica a entero seguro.

    - Devuelve `0` si el valor no puede convertirse.
    - Evita fallos por `None` o cadenas vacias.
    - Conserva el orden numerico actual de CEIC.
    """
    try:
        return int(valor)
    except (TypeError, ValueError):
        return 0


def obtener_numero_anexo_orden(localizacion):
    """
    Obtiene el numero de anexo usado por la politica especial de Primaria e Inicial.

    - Prioriza `anexo_localizacion` cuando ya viene como digito.
    - Si no existe, lo deriva desde `cueanexo`.
    - Devuelve `0` como respaldo para mantener el orden actual.
    """
    anexo = _texto_orden(getattr(localizacion, "anexo_localizacion", ""))
    if anexo.isdigit():
        return int(anexo)

    cueanexo = _texto_orden(getattr(localizacion, "cueanexo", ""))
    digitos = re.sub(r"\D+", "", cueanexo)
    if len(digitos) >= 2:
        return int(digitos[-2:])

    return 0


def ordenar_cargos_exportacion(cargos_queryset, nivel_codigo=None):
    """
    Ordena cargos para Exportacion segun la politica vigente del nivel.

    - Mantiene la regla especial de Primaria e Inicial por `cue_base`, anexo, `cuof`, `ceic`, `id`.
    - Mantiene el fallback general por `cueanexo`, `cuof`, `ceic`, `id`.
    - No consulta datos nuevos ni altera el contenido de los cargos.
    """
    cargos = list(cargos_queryset)
    if nivel_codigo in _NIVELES_AGRUPADOS_POR_CUE_ANEXO:
        return sorted(
            cargos,
            key=lambda cargo: (
                _texto_orden(getattr(getattr(cargo, "localizacion", None), "cue_base", "")),
                obtener_numero_anexo_orden(getattr(cargo, "localizacion", None)),
                _texto_orden(getattr(getattr(cargo, "localizacion", None), "cuof", "")),
                _entero_orden(getattr(cargo, "ceic", "")),
                getattr(cargo, "id", 0) or 0,
            ),
        )

    return sorted(
        cargos,
        key=lambda cargo: (
            _texto_orden(getattr(getattr(cargo, "localizacion", None), "cueanexo", "")),
            _texto_orden(getattr(getattr(cargo, "localizacion", None), "cuof", "")),
            _entero_orden(getattr(cargo, "ceic", "")),
            getattr(cargo, "id", 0) or 0,
        ),
    )


def obtener_clave_columna_exportacion(columna):
    """
    Resuelve una etiqueta visible a la clave logica usada por Exportacion.

    - Normaliza acentos, mayusculas y puntuacion de labels historicos.
    - Conserva compatibilidad con labels inconsistentes por nivel.
    - Sirve como base comun para preview y filas exportables.
    """
    return obtener_clave_columna(columna)


def obtener_celda_exportacion(fila, columnas, *nombres_columnas):
    """
    Lee una celda desde la fila exportable usando labels visibles o claves logicas.

    - Primero intenta coincidencia directa por label.
    - Si no encuentra, usa la clave normalizada del label buscado.
    - Devuelve siempre texto limpio para componer claves y titulos.
    """
    for nombre in nombres_columnas:
        if nombre in columnas:
            indice = columnas.index(nombre)
            if indice < len(fila):
                return str(fila[indice] or "").strip()

        nombre_limpio = str(nombre or "").strip()
        clave_nombre = obtener_clave_columna_exportacion(nombre)
        for indice, columna in enumerate(columnas):
            if indice >= len(fila):
                continue
            if str(columna or "").strip() == nombre_limpio:
                return str(fila[indice] or "").strip()
            if obtener_clave_columna_exportacion(columna) == clave_nombre:
                return str(fila[indice] or "").strip()

    return ""


def _obtener_campos_por_nivel(mapa, nivel_codigo, fallback):
    """
    Resuelve la lista de campos visibles asociada a una politica de nivel.

    - Devuelve la configuracion especifica si existe.
    - Usa un fallback estable para niveles sin politica dedicada.
    - Evita duplicar ramas `if/elif` en el coordinador.
    """
    return mapa.get(nivel_codigo, fallback)


def obtener_clave_seccion_exportacion(nivel_codigo, columnas, fila):
    """
    Construye la clave visible de seccion para el preview de Exportacion.

    - Mantiene las composiciones historicas por nivel.
    - Reusa labels visibles del schema para no tocar templates.
    - Conserva el fallback general por `CUOF`, `CUE`, `CUI`.
    """
    partes = [
        obtener_celda_exportacion(fila, columnas, nombre)
        for nombre in _obtener_campos_por_nivel(
            _CAMPOS_CLAVE_SECCION,
            nivel_codigo,
            _CAMPOS_CLAVE_SECCION_FALLBACK,
        )
    ]
    partes = [parte for parte in partes if parte]
    return " | ".join(partes)


def obtener_titulo_seccion_exportacion(nivel_codigo, columnas, fila):
    """
    Construye el titulo visible de cada seccion del preview.

    - Usa las combinaciones historicas por nivel cuando existen.
    - Si el nivel no tiene titulo propio, reutiliza la clave de seccion.
    - No modifica el contenido de filas ni los totales del exportable.
    """
    campos_titulo = _CAMPOS_TITULO_SECCION.get(nivel_codigo)
    if not campos_titulo:
        return obtener_clave_seccion_exportacion(nivel_codigo, columnas, fila)

    return " - ".join(filter(None, [
        obtener_celda_exportacion(fila, columnas, nombre)
        for nombre in campos_titulo
    ]))


def obtener_clave_seccion_normalizada_exportacion(nivel_codigo, datos_normalizados):
    """
    Devuelve una clave de seccion basada en datos normalizados cuando aplica.

    - Mantiene la excepcion actual de Primaria e Inicial por `cue`.
    - Permite agrupar secciones sin depender solo del texto renderizado.
    - Devuelve vacio para el fallback actual de los demas niveles.
    """
    if nivel_codigo in _NIVELES_AGRUPADOS_POR_CUE_ANEXO:
        return str(datos_normalizados.get("cue", "") or "").strip()

    return ""
