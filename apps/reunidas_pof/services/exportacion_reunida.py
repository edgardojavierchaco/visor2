import re
import unicodedata
from urllib.parse import urlencode

from django.db import OperationalError, ProgrammingError
from django.db.models import Prefetch

from ..models import CargoPof, ProyectosEspecialesPof, ReunidaPof, SnapshotPadronLocalizacionPof
from .exportacion_politicas import (
    obtener_clave_seccion_exportacion,
    obtener_clave_seccion_normalizada_exportacion,
    obtener_titulo_seccion_exportacion,
    ordenar_cargos_exportacion,
)
from .exportacion_rows import (
    aplicar_vaciado_repetidos,
    construir_filas_normalizadas,
)
from .exportacion_columnas_config import (
    REPETIR_POR_CUE,
    REPETIR_POR_CUEANEXO,
    obtener_codigo_config_columnas,
    obtener_columnas_default_ids,
    obtener_columnas_disponibles_nivel,
    obtener_columnas_por_ids,
    obtener_ids_columnas_visible_col,
)
from .exportacion_schemas import obtener_labels_columnas, obtener_schema_exportacion
from .grilla_pof import construir_grilla_pof_desde_cargos, obtener_cargos_grilla_reunida
from .grilla_pof.columnas import obtener_clave_columna
from .grilla_pof.proyecto_especial import (
    COLUMNAS_PROYECTO_ESPECIAL,
    armar_fila_proyecto_especial,
)
from .historial_service import (
    enriquecer_filas_con_historial_cantidad,
    enriquecer_filas_con_historial_observacion,
    enriquecer_filas_con_historial_estado,
)
from .niveles_service import (
    NIVELES_VALIDOS as NOMBRES_NIVEL,
    limpiar_texto,
    normalizar_nivel,
    obtener_nombre_nivel,
)
from .reunidas_service import (
    FILTROS_DETALLE_PROYECTO,
    _aplicar_filtros_cargo_detalle_reunida,
    _aplicar_filtros_detalle_reunida,
    _construir_querystring_detalle_con_filtros,
    _hay_filtros_detalle_reunida,
    _obtener_filtros_detalle_reunida,
)


COLUMNAS_POR_NIVEL = {
    codigo: obtener_labels_columnas(codigo)
    for codigo in NOMBRES_NIVEL
}

FUENTES_CANTIDAD_PREVIEW = {
    "cantidad",
    "cantidad_cargos",
    "cantidad_horas",
}


def _obtener_columna_oferta_exportacion():
    """
    Define Oferta como segunda columna obligatoria de Exportar Reunida.

    - Se muestra en todos los niveles de Reunidas comunes.
    - Repite el valor en cada fila de cargo.
    - No modifica los schemas compartidos ni Proyecto Especial.
    """
    return {
        "key": "oferta_exportacion",
        "source": "oferta",
        "titulo": "Oferta",
        "repetir": "siempre",
        "required": True,
        "visible_default": True,
        "visible": True,
    }


def _agregar_columna_oferta_exportacion(
    columnas_disponibles,
    columnas_default_keys,
    columnas_visibles_keys,
):
    """Inserta Oferta inmediatamente despues de la columna CUE-Anexo."""
    columna_oferta = _obtener_columna_oferta_exportacion()
    columna_key = columna_oferta["key"]

    columnas_disponibles_resultado = [
        columna
        for columna in columnas_disponibles
        if columna.get("key") != columna_key
    ]
    columnas_disponibles_resultado.insert(1, columna_oferta)

    columnas_default_resultado = [
        key for key in columnas_default_keys if key != columna_key
    ]
    columnas_default_resultado.insert(1, columna_key)

    columnas_visibles_resultado = [
        key for key in columnas_visibles_keys if key != columna_key
    ]
    columnas_visibles_resultado.insert(1, columna_key)

    return (
        columnas_disponibles_resultado,
        columnas_default_resultado,
        columnas_visibles_resultado,
        columna_oferta,
    )


def _obtener_columna_estado_pof_exportacion():
    """
    Define la columna administrativa Estado POF exclusiva de Exportar Reunida.

    - Se agrega al final de todas las Reunidas comunes.
    - Es visible por defecto, pero puede ocultarse desde el selector de columnas.
    - Usa `estado_pof` ya normalizado como única fuente de verdad.
    - No modifica los schemas compartidos ni otras vistas del módulo.
    """
    return {
        "key": "estado_pof_exportacion",
        "source": "estado_pof",
        "titulo": "Estado POF",
        "repetir": "siempre",
        "required": False,
        "visible_default": True,
        "visible": True,
    }


def _agregar_columna_estado_pof_exportacion(
    request,
    columnas_disponibles,
    columnas_default_keys,
    columnas_visibles_keys,
):
    """
    Agrega Estado POF al final de las columnas de Exportar Reunida.

    - Mantiene la columna visible por defecto.
    - Respeta `visible_col` cuando el usuario exporta la vista actual.
    - Permite incluirla al exportar todos los datos.
    - No muta las listas recibidas.
    """
    columna_estado = _obtener_columna_estado_pof_exportacion()

    visibles_solicitadas = {
        limpiar_texto(valor, 120)
        for valor in request.GET.getlist("visible_col")
        if limpiar_texto(valor, 120)
    }

    columnas_disponibles_resultado = [
        *columnas_disponibles,
        columna_estado,
    ]

    columnas_default_resultado = [
        *columnas_default_keys,
        columna_estado["key"],
    ]

    columnas_visibles_resultado = list(columnas_visibles_keys)

    estado_visible = (
        not visibles_solicitadas
        or columna_estado["key"] in visibles_solicitadas
        or columna_estado["source"] in visibles_solicitadas
    )

    if (
        estado_visible
        and columna_estado["key"] not in columnas_visibles_resultado
    ):
        columnas_visibles_resultado.append(columna_estado["key"])

    return (
        columnas_disponibles_resultado,
        columnas_default_resultado,
        columnas_visibles_resultado,
        columna_estado,
    )


def _obtener_columna_observacion_exportacion():
    return {
        "key": "observacion_cargo_exportacion",
        "source": "observacion_cargo",
        "titulo": "Observación",
        "repetir": "siempre",
        "required": False,
        "visible_default": True,
        "visible": True,
    }


def _agregar_columna_observacion_exportacion(
    request,
    columnas_disponibles,
    columnas_default_keys,
    columnas_visibles_keys,
):
    """Agrega Observación al final del exportable y respeta `visible_col`."""
    columna_observacion = _obtener_columna_observacion_exportacion()
    visibles_solicitadas = {
        limpiar_texto(valor, 120)
        for valor in request.GET.getlist("visible_col")
        if limpiar_texto(valor, 120)
    }

    columnas_disponibles_resultado = [
        *columnas_disponibles,
        columna_observacion,
    ]
    columnas_default_resultado = [
        *columnas_default_keys,
        columna_observacion["key"],
    ]
    columnas_visibles_resultado = list(columnas_visibles_keys)
    observacion_visible = (
        not visibles_solicitadas
        or columna_observacion["key"] in visibles_solicitadas
        or columna_observacion["source"] in visibles_solicitadas
    )
    if (
        observacion_visible
        and columna_observacion["key"] not in columnas_visibles_resultado
    ):
        columnas_visibles_resultado.append(columna_observacion["key"])

    return (
        columnas_disponibles_resultado,
        columnas_default_resultado,
        columnas_visibles_resultado,
        columna_observacion,
    )


def obtener_columnas_por_nivel(nivel_codigo):
    return obtener_labels_columnas(nivel_codigo)


def _asegurar_columna_cueanexo_visible(columnas_disponibles, columnas_visibles_keys):
    """
    Fuerza la columna principal `CUE-Anexo` como primera visible del exportable.

    - Reusa la configuracion ya normalizada marcada como requerida.
    - Evita que preview y Excel queden sin la clave operativa principal.
    - Conserva el resto del orden visible actual del usuario.
    """
    columna_cueanexo = next(
        (
            columna
            for columna in columnas_disponibles
            if columna.get("required") and columna.get("source") == "cueanexo"
        ),
        None,
    )
    if not columna_cueanexo:
        return columnas_visibles_keys

    columna_id = columna_cueanexo.get("key")
    resto = [
        columna_id_visible
        for columna_id_visible in columnas_visibles_keys
        if columna_id_visible != columna_id
    ]
    return [columna_id, *resto]


def _resolver_columnas_visibles(request, nivel_codigo):
    """
    Resuelve columnas visibles del exportable respetando defaults y requeridas.

    - Parte de la configuracion central por nivel.
    - Mantiene la compatibilidad con `visible_col` en la URL.
    - Garantiza `CUE-Anexo` como primera columna visible.
    """
    columnas_disponibles = obtener_columnas_disponibles_nivel(nivel_codigo)
    columnas_default_keys = obtener_columnas_default_ids(nivel_codigo)
    valores_visible_col = [
        limpiar_texto(value, 120)
        for value in request.GET.getlist("visible_col")
        if limpiar_texto(value, 120)
    ]

    columnas_visibles_keys = obtener_ids_columnas_visible_col(
        nivel_codigo,
        valores_visible_col,
    )
    columnas_visibles_keys = _asegurar_columna_cueanexo_visible(
        columnas_disponibles,
        columnas_visibles_keys,
    )

    return columnas_disponibles, columnas_default_keys, columnas_visibles_keys


def _marcar_columnas_disponibles(
    columnas_disponibles,
    columnas_default_keys,
    columnas_visibles_keys,
):
    default_set = set(columnas_default_keys)
    visibles_set = set(columnas_visibles_keys)
    columnas = []
    for columna in columnas_disponibles:
        columna_marcada = columna.copy()
        columna_marcada["visible_default"] = columna["key"] in default_set
        columna_marcada["visible"] = columna["key"] in visibles_set
        columnas.append(columna_marcada)
    return columnas


def _agregar_metadata_cantidad_preview(columnas):
    indices_cantidad = [
        indice
        for indice, columna in enumerate(columnas)
        if columna.get("source") in FUENTES_CANTIDAD_PREVIEW
    ]
    indice_ancla = indices_cantidad[-1] if indices_cantidad else None
    columnas_con_metadata = []

    for indice, columna in enumerate(columnas):
        columna_con_metadata = columna.copy()
        columna_con_metadata["es_columna_cantidad"] = indice in indices_cantidad
        columna_con_metadata["es_ancla_modificacion_cantidad"] = indice == indice_ancla
        columna_con_metadata["es_columna_observacion"] = (
            columna.get("source") == "observacion_cargo"
        )
        columnas_con_metadata.append(columna_con_metadata)

    return columnas_con_metadata


def _obtener_titulos_columnas(columnas):
    return [columna["titulo"] for columna in columnas]


def normalizar_cueanexo_exportacion(valor):
    texto = str(valor or "").strip()
    if not texto:
        return ""

    digitos = re.sub(r"\D+", "", texto)
    if len(digitos) == 9:
        return digitos
    return ""


def _agregar_metadata_grupo_visual_reunida(filas_normalizadas):
    filas = []
    for fila in filas_normalizadas:
        fila_con_metadata = fila.copy()
        fila_con_metadata["_grupo_visual_cueanexo"] = fila.get("cueanexo", "")
        filas.append(fila_con_metadata)
    return filas


def _obtener_separadores_grupo_visual_reunida(filas_normalizadas):
    separadores = []
    cue_anterior = None
    cueanexo_anterior = None
    filas_con_metadata = _agregar_metadata_grupo_visual_reunida(filas_normalizadas)

    for fila in filas_con_metadata:
        cueanexo_actual = normalizar_cueanexo_exportacion(
            fila.get("_grupo_visual_cueanexo", "")
        )
        cue_actual = cueanexo_actual[:7] if len(cueanexo_actual) >= 7 else ""
        es_inicio_cue = bool(
            separadores and cue_actual and cue_actual != cue_anterior
        )
        es_inicio_anexo = bool(
            separadores
            and not es_inicio_cue
            and cue_actual
            and cue_actual == cue_anterior
            and cueanexo_actual
            and cueanexo_actual != cueanexo_anterior
        )

        separadores.append({
            "es_inicio_cue": es_inicio_cue,
            "es_inicio_anexo": es_inicio_anexo,
        })
        cue_anterior = cue_actual or None
        cueanexo_anterior = cueanexo_actual or None

    return separadores


def _obtener_cue_grupo_visual_reunida(fila_dict):
    """
    Obtiene el CUE usado para agrupar visualmente totales generales de la Reunida.

    - Prioriza el campo `cue` ya normalizado.
    - Si falta, lo deriva desde `cueanexo` tomando sus primeros 7 digitos.
    - Devuelve vacio cuando no hay un CUE confiable para no inventar grupos.
    """
    cue = str(fila_dict.get("cue", "") or "").strip()
    if cue:
        return cue

    cueanexo = normalizar_cueanexo_exportacion(
        fila_dict.get("_grupo_visual_cueanexo", "") or fila_dict.get("cueanexo", "")
    )
    return cueanexo[:7] if len(cueanexo) >= 7 else ""


def obtener_clave_grupo_visual_reunida(fila_dict, indice=None):
    cueanexo = normalizar_cueanexo_exportacion(
        fila_dict.get("_grupo_visual_cueanexo", "")
    )
    if cueanexo:
        return cueanexo

    identificador = fila_dict.get("cargo_id") or indice
    return f"_sin_cueanexo_{identificador}"


def obtener_clave_total_general_visual_reunida(fila_dict, indice=None):
    """
    Resuelve la clave visual de Total General para mostrarlo una sola vez por CUE.

    - Usa el CUE normalizado o derivado desde `cueanexo`.
    - Si no existe CUE confiable, aísla la fila por localizacion/cargo para no mezclarla.
    - No usa CUOF ni CUE-Anexo como agrupador final del total.
    """
    cue = _obtener_cue_grupo_visual_reunida(fila_dict)
    if cue:
        return cue

    identificador = (
        fila_dict.get("localizacion_id")
        or fila_dict.get("cargo_id")
        or indice
    )
    return f"_sin_cue_{identificador}"


def _proyectar_filas_exportacion(nivel_codigo, filas_normalizadas, columnas):
    if not filas_normalizadas:
        return []

    if obtener_codigo_config_columnas(nivel_codigo) == "SECUNDARIA_TECNICA":
        filas_normalizadas = aplicar_vaciado_repetidos(
            filas_normalizadas,
            obtener_schema_exportacion(nivel_codigo),
        )

    filas = []
    clave_anterior = None
    clave_total_anterior = None
    filas_con_metadata = _agregar_metadata_grupo_visual_reunida(filas_normalizadas)

    for indice, fila in enumerate(filas_con_metadata):
        clave_actual = obtener_clave_grupo_visual_reunida(fila, indice=indice)
        clave_total_actual = obtener_clave_total_general_visual_reunida(
            fila,
            indice=indice,
        )
        misma_localizacion = clave_actual == clave_anterior
        mismo_cue = clave_total_actual == clave_total_anterior
        fila_render = []

        for columna in columnas:
            valor = fila.get(columna["source"], "")
            if (
                misma_localizacion
                and columna.get("repetir") == REPETIR_POR_CUEANEXO
            ):
                valor = ""
            elif (
                mismo_cue
                and columna.get("repetir") == REPETIR_POR_CUE
            ):
                valor = ""
            fila_render.append(valor)

        filas.append(fila_render)
        clave_anterior = clave_actual
        clave_total_anterior = clave_total_actual

    return filas


def _construir_fila_preview(
    fila,
    columnas_disponibles,
    columnas_visibles_keys,
    separador=None,
    fila_normalizada=None,
    ):
    visibles_set = set(columnas_visibles_keys)
    separador = separador or {}
    fila_normalizada = fila_normalizada or {}

    estado_pof_codigo = str(
        fila_normalizada.get("estado_pof_codigo", "") or ""
    ).strip().upper()

    if estado_pof_codigo == CargoPof.EstadoPof.AFECTADO.value:
        estado_pof_clase = "afectado"
    elif estado_pof_codigo == CargoPof.EstadoPof.DESAFECTADO.value:
        estado_pof_clase = "desafectado"
    else:
        estado_pof_clase = ""

    celdas = []
    for indice, columna in enumerate(columnas_disponibles):
        valor = fila[indice] if indice < len(fila) else ""
        es_columna_cantidad = bool(columna.get("es_columna_cantidad"))
        es_columna_estado_pof = columna.get("source") == "estado_pof"
        es_columna_observacion = bool(columna.get("es_columna_observacion"))

        celdas.append({
            "key": columna["key"],
            "source": columna.get("source", ""),
            "valor": valor,
            "visible": columna["key"] in visibles_set,
            "es_columna_cantidad": es_columna_cantidad,
            "es_columna_estado_pof": es_columna_estado_pof,
            "es_columna_observacion": es_columna_observacion,
            "estado_pof_clase": (
                estado_pof_clase
                if es_columna_estado_pof
                else ""
            ),
            "es_ancla_modificacion_cantidad": bool(
                columna.get("es_ancla_modificacion_cantidad")
            ),
            "tiene_valor_cantidad": (
                es_columna_cantidad
                and valor not in (None, "")
            ),
        })

    return {
        "es_inicio_cue": bool(separador.get("es_inicio_cue")),
        "es_inicio_anexo": bool(separador.get("es_inicio_anexo")),
        "cargo_ids": list(fila_normalizada.get("cargo_ids", [])),
        "tiene_modificacion_cantidad": bool(
            fila_normalizada.get("tiene_modificacion_cantidad")
        ),
        "tiene_modificacion_estado": bool(
            fila_normalizada.get("tiene_modificacion_estado")
        ),
        "tiene_modificacion_observacion": bool(
            fila_normalizada.get("tiene_modificacion_observacion")
        ),
        "celdas": celdas,
    }


def _construir_secciones_preview(
    secciones,
    columnas_disponibles,
    columnas_visibles_keys,
    separadores_filas=None,
    filas_normalizadas=None,
):
    separadores_filas = separadores_filas or []
    filas_normalizadas = filas_normalizadas or []
    secciones_preview = []
    for seccion in secciones:
        seccion_preview = seccion.copy()
        indices_filas = seccion.get("indices_filas") or []
        filas_preview = []
        for indice_local, fila in enumerate(seccion.get("filas", [])):
            indice_fila = (
                indices_filas[indice_local]
                if indice_local < len(indices_filas)
                else indice_local
            )
            filas_preview.append(
                _construir_fila_preview(
                    fila,
                    columnas_disponibles,
                    columnas_visibles_keys,
                    separadores_filas[indice_fila]
                    if indice_fila < len(separadores_filas)
                    else None,
                    filas_normalizadas[indice_fila]
                    if indice_fila < len(filas_normalizadas)
                    else None,
                )
            )
        seccion_preview["filas"] = filas_preview
        secciones_preview.append(seccion_preview)
    return secciones_preview


def _armar_excel_querystring_reunida(anio, nivel_codigo, columnas_visibles_keys):
    if not columnas_visibles_keys:
        return ""
    params = [
        ("anio", anio),
        ("nivel", nivel_codigo),
        ("accion", "excel"),
    ]
    params.extend(
        ("visible_col", key)
        for key in columnas_visibles_keys
    )
    return urlencode(params)



def obtener_clave_seccion(nivel_codigo, columnas, fila):
    return obtener_clave_seccion_exportacion(nivel_codigo, columnas, fila)

def obtener_titulo_seccion(nivel_codigo, columnas, fila):
    return obtener_titulo_seccion_exportacion(nivel_codigo, columnas, fila)

def obtener_clave_seccion_normalizada(nivel_codigo, datos_normalizados):
    return obtener_clave_seccion_normalizada_exportacion(nivel_codigo, datos_normalizados)

def agrupar_filas_por_seccion(nivel_codigo, columnas, filas, filas_normalizadas=None):
    """
    Agrupa las filas por bloque institucional/localización.
    No calcula totales generales de Reunida.
    Los campos Total, Total General y Puntos se mantienen solo como columnas del formato.
    """

    secciones = []
    indice_por_clave = {}
    filas_normalizadas = filas_normalizadas or []

    for indice_fila, fila in enumerate(filas):
        datos_normalizados = (
            filas_normalizadas[indice_fila]
            if indice_fila < len(filas_normalizadas)
            else {}
        )
        clave = (
            obtener_clave_seccion_normalizada_exportacion(nivel_codigo, datos_normalizados)
            or obtener_clave_seccion_exportacion(nivel_codigo, columnas, fila)
        )

        if not clave and secciones:
            indice = len(secciones) - 1
            secciones[indice]["filas"].append(fila)
            secciones[indice]["indices_filas"].append(indice_fila)
            secciones[indice]["cantidad_filas"] = len(secciones[indice]["filas"])
            continue

        if not clave:
            clave = f"SECCION-{len(secciones) + 1}"

        if clave not in indice_por_clave:
            indice_por_clave[clave] = len(secciones)

            secciones.append({
                "clave": clave,
                "titulo": obtener_titulo_seccion_exportacion(nivel_codigo, columnas, fila),
                "filas": [],
                "indices_filas": [],
                "cantidad_filas": 0,
            })

        indice = indice_por_clave[clave]
        secciones[indice]["filas"].append(fila)
        secciones[indice]["indices_filas"].append(indice_fila)
        secciones[indice]["cantidad_filas"] = len(secciones[indice]["filas"])

    return secciones


def _obtener_nombre_archivo(nivel_nombre, anio):
    nombre = f"POF_{nivel_nombre}_{anio}.xlsx".replace(" ", "_")
    nombre = "".join(
        caracter
        for caracter in unicodedata.normalize("NFD", nombre)
        if unicodedata.category(caracter) != "Mn"
    )
    nombre = re.sub(r"[^A-Za-z0-9_.-]+", "", nombre)
    return nombre or "POF.xlsx"


def _obtener_nombre_archivo_proyecto(proyecto):
    nombre = f"Proyecto_Especial_{proyecto.nombre}_{proyecto.anio}.xlsx".replace(" ", "_")
    nombre = "".join(
        caracter
        for caracter in unicodedata.normalize("NFD", nombre)
        if unicodedata.category(caracter) != "Mn"
    )
    nombre = re.sub(r"[^A-Za-z0-9_.-]+", "", nombre)
    return nombre or "Proyecto_Especial_POF.xlsx"


def _ordenar_cargos_exportacion(cargos_queryset, nivel_codigo=None):
    return ordenar_cargos_exportacion(cargos_queryset, nivel_codigo)


def _obtener_cargos_exportacion_queryset():
    snapshots_vigentes = SnapshotPadronLocalizacionPof.objects.filter(
        vigente=True
    ).order_by("-fecha_snapshot")

    return (
        CargoPof.objects
        .select_related(
            "localizacion",
            "localizacion__reunida",
            "localizacion__proyecto_especial",
            "lote_carga",
        )
        .prefetch_related(
            Prefetch(
                "localizacion__snapshots_padron",
                queryset=snapshots_vigentes,
                to_attr="snapshots_vigentes",
            )
        )
        .order_by(
            "localizacion__cuof",
            "localizacion__cueanexo",
            "ceic",
            "id",
        )
    )


def _obtener_cargos_exportacion(reunida):
    return obtener_cargos_grilla_reunida(reunida=reunida)


def _obtener_cargos_exportacion_proyecto(proyecto_especial_id):
    return _obtener_cargos_exportacion_queryset().filter(
        localizacion__proyecto_especial_id=proyecto_especial_id,
    )


def _obtener_filas_reales_exportacion(
    columnas,
    cargos_queryset,
    nivel_codigo=None,
    incluir_historial_cantidad=False,
    incluir_historial_observacion=False,
):
    cargos_ordenados = ordenar_cargos_exportacion(cargos_queryset, nivel_codigo)

    if nivel_codigo:
        grilla = construir_grilla_pof_desde_cargos(
            cargos=cargos_ordenados,
            nivel_codigo=nivel_codigo,
            contexto="REUNIDA",
            incluir_historial_cantidad=incluir_historial_cantidad,
        )
        filas_normalizadas = grilla["filas_normalizadas"]
        if incluir_historial_observacion:
            enriquecer_filas_con_historial_observacion(filas_normalizadas)
        return grilla["filas_exportacion"], filas_normalizadas

    filas_normalizadas = construir_filas_normalizadas(cargos_ordenados, nivel_codigo)
    if incluir_historial_cantidad:
        enriquecer_filas_con_historial_cantidad(filas_normalizadas)
    if incluir_historial_observacion:
        enriquecer_filas_con_historial_observacion(filas_normalizadas)
    return [
        armar_fila_proyecto_especial(columnas, datos_normalizados)
        for datos_normalizados in filas_normalizadas
    ], filas_normalizadas


def _construir_contexto_exportacion_proyecto(proyecto_especial_id, request=None):
    columnas_base = list(COLUMNAS_PROYECTO_ESPECIAL)
    columna_observacion = _obtener_columna_observacion_exportacion()
    columnas = [*columnas_base, columna_observacion["titulo"]]
    columnas_preview_config_base = [
        {
            "key": f"proyecto_especial_{indice}",
            "source": obtener_clave_columna(titulo),
            "titulo": titulo,
            "visible": True,
        }
        for indice, titulo in enumerate(columnas_base)
    ]
    columnas_preview_config_base.append({
        **columna_observacion,
        "key": "proyecto_especial_observacion",
        "visible": True,
    })
    columnas_preview_config = _agregar_metadata_cantidad_preview(
        columnas_preview_config_base
    )
    columnas_preview_keys = [
        columna["key"] for columna in columnas_preview_config
    ]
    mostrar_columna_modificacion_cantidad = any(
        columna.get("es_columna_cantidad")
        for columna in columnas_preview_config
    )
    mostrar_columna_modificacion_observacion = True
    columnas_visuales_extra = (
        (1 if mostrar_columna_modificacion_cantidad else 0)
        + 1
    )
    filas_exportacion = []
    filas_normalizadas_exportacion = []
    mensaje_exportacion = ""
    proyecto_obj = None
    filtros_detalle = _obtener_filtros_detalle_reunida(request) if request else {}
    filtros_detalle_activos = (
        _hay_filtros_detalle_reunida(filtros_detalle, FILTROS_DETALLE_PROYECTO)
        if request
        else False
    )

    if not proyecto_especial_id.isdigit():
        mensaje_exportacion = "Debe seleccionar un Proyecto Especial POF valido."
    else:
        try:
            proyecto_obj = ProyectosEspecialesPof.objects.get(pk=proyecto_especial_id)
            cargos_exportacion = _obtener_cargos_exportacion_proyecto(proyecto_especial_id)
            if request:
                cargos_exportacion, _mensaje_filtros, _errores_filtros = _aplicar_filtros_detalle_reunida(
                    cargos_exportacion,
                    filtros_detalle,
                    incluir_cui=True,
                )
                cargos_exportacion, _mensaje_cargo, _errores_cargo = _aplicar_filtros_cargo_detalle_reunida(
                    cargos_exportacion,
                    filtros_detalle,
                )
            filas_base, filas_normalizadas_exportacion = _obtener_filas_reales_exportacion(
                columnas_base,
                cargos_exportacion,
                nivel_codigo=None,
                incluir_historial_cantidad=(
                    request is not None
                    and request.GET.get("accion") != "excel"
                ),
                incluir_historial_observacion=(
                    request is not None
                    and request.GET.get("accion") != "excel"
                ),
            )
            filas_exportacion = [
                [*fila, datos.get("observacion_cargo", "")]
                for fila, datos in zip(
                    filas_base,
                    filas_normalizadas_exportacion,
                )
            ]
            if not filas_exportacion:
                mensaje_exportacion = (
                    "No hay datos para exportar con los filtros aplicados."
                    if filtros_detalle_activos
                    else "El Proyecto Especial existe, pero no tiene cargos cargados para exportar."
                )
        except ProyectosEspecialesPof.DoesNotExist:
            mensaje_exportacion = "No existe el Proyecto Especial POF seleccionado."
        except (ProgrammingError, OperationalError):
            mensaje_exportacion = "No se pudieron consultar los datos reales del Proyecto Especial POF."

    secciones_exportacion = agrupar_filas_por_seccion(
        nivel_codigo="PROYECTO_ESPECIAL",
        columnas=columnas,
        filas=filas_exportacion,
        filas_normalizadas=filas_normalizadas_exportacion,
    )
    secciones_preview = _construir_secciones_preview(
        secciones_exportacion,
        columnas_preview_config,
        columnas_preview_keys,
        filas_normalizadas=filas_normalizadas_exportacion,
    )
    anio = str(proyecto_obj.anio) if proyecto_obj else ""
    nombre = proyecto_obj.nombre if proyecto_obj else "-"
    resolucion = proyecto_obj.resolucion if proyecto_obj and proyecto_obj.resolucion else "Sin resolucion"
    base_params = (
        {
            "cabecera_tipo": "PROYECTO_ESPECIAL",
            "proyecto_especial_id": proyecto_obj.id,
        }
        if proyecto_obj
        else {}
    )
    cabecera_querystring = urlencode(base_params) if base_params else ""
    detalle_querystring = (
        _construir_querystring_detalle_con_filtros(
            filtros_detalle,
            base_params,
            FILTROS_DETALLE_PROYECTO,
        )
        if base_params
        else ""
    )
    excel_querystring = f"{detalle_querystring}&accion=excel" if detalle_querystring else ""
    titulo_excel = f"Proyecto Especial POF - {nombre} {anio}".strip()

    return {
        "anio_activo": anio,
        "nivel_codigo": "",
        "cabecera_tipo_activa": "PROYECTO_ESPECIAL",
        "proyecto_especial_id_activo": str(proyecto_obj.id) if proyecto_obj else "",
        "es_proyecto_especial": True,
        "cabecera_titulo": "Proyecto Especial",
        "titulo_exportacion": "EXPORTAR PROYECTO ESPECIAL",
        "descripcion_exportacion": "Valida los datos cargados y prepara la exportacion final del Proyecto Especial POF.",
        "cabecera_querystring": detalle_querystring or cabecera_querystring,
        "excel_querystring": excel_querystring,
        "reunida": {
            "anio": anio,
            "nivel": nombre,
            "nivel_codigo": "",
            "existe": bool(proyecto_obj),
        },
        "proyecto_especial": {
            "id": proyecto_obj.id if proyecto_obj else "",
            "anio": anio,
            "nombre": nombre,
            "resolucion": resolucion,
        },
        "columnas": columnas,
        "columnas_preview_config": columnas_preview_config,
        "columnas_disponibles": [],
        "columnas_visibles_keys": [],
        "columnas_default_keys": [],
        "filas_exportacion": filas_exportacion,
        "filas_normalizadas_exportacion": filas_normalizadas_exportacion,
        "secciones_exportacion": secciones_exportacion,
        "secciones_preview": secciones_preview,
        "columnas_preview_cantidad": len(columnas),
        "columnas_visuales_extra": columnas_visuales_extra,
        "columnas_preview_colspan": len(columnas) + columnas_visuales_extra,
        "mostrar_columna_modificacion_cantidad": mostrar_columna_modificacion_cantidad,
        "mostrar_columna_modificacion_observacion": mostrar_columna_modificacion_observacion,
        "cantidad_secciones": len(secciones_exportacion),
        "mensaje_exportacion": mensaje_exportacion,
        "nombre_archivo": _obtener_nombre_archivo_proyecto(proyecto_obj) if proyecto_obj else "Proyecto_Especial_POF.xlsx",
        "titulo_hoja": nombre,
        "titulo_excel": titulo_excel,
    }


def construir_contexto_exportacion(request):
    cabecera_tipo = str(request.GET.get("cabecera_tipo", "") or "").strip().upper()
    proyecto_especial_id = limpiar_texto(request.GET.get("proyecto_especial_id", ""), 20)
    if cabecera_tipo == "PROYECTO_ESPECIAL" or proyecto_especial_id:
        return _construir_contexto_exportacion_proyecto(proyecto_especial_id, request=request)

    anio = limpiar_texto(request.GET.get("anio", ""), 4)
    nivel_parametro = request.GET.get("nivel", "")
    nivel_codigo = normalizar_nivel(nivel_parametro)
    tiene_contexto = bool(anio.isdigit() and len(anio) == 4 and nivel_codigo)
    nivel_nombre = obtener_nombre_nivel(nivel_codigo, nivel_parametro) or "-"
    nivel_exportacion = nivel_codigo or "PRIMARIA"
    (
        columnas_disponibles_base,
        columnas_default_keys,
        columnas_visibles_keys,
    ) = _resolver_columnas_visibles(request, nivel_exportacion)

    (
        columnas_disponibles_base,
        columnas_default_keys,
        columnas_visibles_keys,
        columna_oferta,
    ) = _agregar_columna_oferta_exportacion(
        columnas_disponibles_base,
        columnas_default_keys,
        columnas_visibles_keys,
    )

    (
        columnas_disponibles_base,
        columnas_default_keys,
        columnas_visibles_keys,
        columna_estado_pof,
    ) = _agregar_columna_estado_pof_exportacion(
        request,
        columnas_disponibles_base,
        columnas_default_keys,
        columnas_visibles_keys,
    )

    (
        columnas_disponibles_base,
        columnas_default_keys,
        columnas_visibles_keys,
        columna_observacion,
    ) = _agregar_columna_observacion_exportacion(
        request,
        columnas_disponibles_base,
        columnas_default_keys,
        columnas_visibles_keys,
    )

    columnas_disponibles_base = _agregar_metadata_cantidad_preview(
        columnas_disponibles_base
    )
    columnas_disponibles = _marcar_columnas_disponibles(
        columnas_disponibles_base,
        columnas_default_keys,
        columnas_visibles_keys,
    )
    columnas_visibles = obtener_columnas_por_ids(
        nivel_exportacion,
        columnas_visibles_keys,
    )
    columnas_visibles.insert(1, columna_oferta)
    if columna_estado_pof["key"] in columnas_visibles_keys:
        columnas_visibles.append(columna_estado_pof)
    if columna_observacion["key"] in columnas_visibles_keys:
        columnas_visibles.append(columna_observacion)

    columnas = _obtener_titulos_columnas(columnas_visibles)
    columnas_preview = _obtener_titulos_columnas(columnas_disponibles_base)
    tiene_columna_modificacion_cantidad = any(
        columna.get("es_ancla_modificacion_cantidad")
        for columna in columnas_disponibles_base
    )
    mostrar_columna_modificacion_cantidad = any(
        columna.get("es_columna_cantidad") and columna.get("key") in columnas_visibles_keys
        for columna in columnas_disponibles_base
    )
    mostrar_columna_modificacion_observacion = (
        columna_observacion["key"] in columnas_visibles_keys
    )
    columnas_visuales_extra = (
        (1 if mostrar_columna_modificacion_cantidad else 0)
        + (1 if mostrar_columna_modificacion_observacion else 0)
    )
    filas_exportacion = []
    filas_exportacion_globales = []
    filas_normalizadas_exportacion = []
    separadores_filas_exportacion = []
    mensaje_exportacion = ""
    reunida_obj = None

    if not tiene_contexto:
        mensaje_exportacion = "Debe seleccionar una Reunida valida por anio y nivel."
    else:
        try:
            reunida_obj = ReunidaPof.objects.get(anio=int(anio), nivel=nivel_codigo)
            nivel_nombre = NOMBRES_NIVEL.get(nivel_codigo, reunida_obj.get_nivel_display())
            _filas_schema, filas_normalizadas_exportacion = _obtener_filas_reales_exportacion(
                obtener_columnas_por_nivel(nivel_exportacion),
                _obtener_cargos_exportacion(reunida_obj),
                nivel_codigo=nivel_codigo,
                incluir_historial_cantidad=(
                    request.GET.get("accion") != "excel"
                    and tiene_columna_modificacion_cantidad
                ),
                incluir_historial_observacion=(
                    request.GET.get("accion") != "excel"
                ),
            )
            if request.GET.get("accion") != "excel":
                enriquecer_filas_con_historial_estado(
                    filas_normalizadas_exportacion
                )
            filas_exportacion = _proyectar_filas_exportacion(
                nivel_exportacion,
                filas_normalizadas_exportacion,
                columnas_visibles,
            )
            filas_exportacion_globales = _proyectar_filas_exportacion(
                nivel_exportacion,
                filas_normalizadas_exportacion,
                columnas_disponibles_base,
            )
            separadores_filas_exportacion = _obtener_separadores_grupo_visual_reunida(
                filas_normalizadas_exportacion
            )
            if not filas_exportacion:
                mensaje_exportacion = "La Reunida existe, pero no tiene cargos cargados para exportar."
        except ReunidaPof.DoesNotExist:
            mensaje_exportacion = "No existe una Reunida POF para el anio y nivel seleccionados."
        except (ProgrammingError, OperationalError):
            mensaje_exportacion = "No se pudieron consultar los datos reales de la Reunida."

    secciones_exportacion = agrupar_filas_por_seccion(
        nivel_codigo=nivel_exportacion,
        columnas=columnas,
        filas=filas_exportacion,
        filas_normalizadas=filas_normalizadas_exportacion,
    )
    secciones_exportacion_globales = agrupar_filas_por_seccion(
        nivel_codigo=nivel_exportacion,
        columnas=columnas_preview,
        filas=filas_exportacion_globales,
        filas_normalizadas=filas_normalizadas_exportacion,
    )
    secciones_preview = _construir_secciones_preview(
        secciones_exportacion_globales,
        columnas_disponibles_base,
        columnas_visibles_keys,
        separadores_filas_exportacion,
        filas_normalizadas_exportacion,
    )
    cabecera_querystring = f"anio={anio}&nivel={nivel_codigo}" if tiene_contexto else ""
    excel_querystring = (
        _armar_excel_querystring_reunida(anio, nivel_codigo, columnas_visibles_keys)
        if tiene_contexto
        else ""
    )
    titulo_excel = f"POF - {nivel_nombre} {anio}".strip()

    return {
        "anio_activo": anio if tiene_contexto else "",
        "nivel_codigo": nivel_codigo if tiene_contexto else "",
        "cabecera_tipo_activa": "REUNIDA",
        "proyecto_especial_id_activo": "",
        "es_proyecto_especial": False,
        "cabecera_titulo": "POF",
        "titulo_exportacion": "EXPORTAR POF",
        "descripcion_exportacion": "Valida los datos cargados y prepara la exportacion final por anio y nivel.",
        "cabecera_querystring": cabecera_querystring,
        "excel_querystring": excel_querystring,
        "reunida": {
            "anio": anio,
            "nivel": nivel_nombre,
            "nivel_codigo": nivel_codigo,
            "existe": bool(reunida_obj),
        },
        "columnas": columnas,
        "columnas_disponibles": columnas_disponibles,
        "columnas_visibles_keys": columnas_visibles_keys,
        "columnas_default_keys": columnas_default_keys,
        "filas_exportacion": filas_exportacion,
        "filas_normalizadas_exportacion": filas_normalizadas_exportacion,
        "separadores_filas_exportacion": separadores_filas_exportacion,
        "secciones_exportacion": secciones_exportacion,
        "secciones_preview": secciones_preview,
        "columnas_preview_cantidad": len(columnas_disponibles),
        "columnas_visuales_extra": columnas_visuales_extra,
        "columnas_preview_colspan": len(columnas_disponibles) + columnas_visuales_extra,
        "mostrar_columna_modificacion_cantidad": mostrar_columna_modificacion_cantidad,
        "mostrar_columna_modificacion_observacion": mostrar_columna_modificacion_observacion,
        "cantidad_secciones": len(secciones_exportacion),
        "mensaje_exportacion": mensaje_exportacion,
        "nombre_archivo": _obtener_nombre_archivo(nivel_nombre, anio),
        "titulo_hoja": nivel_nombre,
        "titulo_excel": titulo_excel,
    }
