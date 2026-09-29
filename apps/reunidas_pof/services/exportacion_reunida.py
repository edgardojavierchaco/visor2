import re
import unicodedata
from decimal import Decimal, InvalidOperation
from urllib.parse import urlencode

from django.core.paginator import Paginator
from django.db import DatabaseError, OperationalError, ProgrammingError
from django.db.models import Case, CharField, Min, Prefetch, Q, Sum, Value, When
from django.db.models.functions import Cast, Concat, Trim

from ..models import CargoPof, ProyectosEspecialesPof, ReunidaPof, SnapshotPadronLocalizacionPof
from .anexo_pof_service import (
    TIPO_PROPIETARIO_CUE,
    TIPO_PROPIETARIO_CUOF,
    obtener_codigos_activos_propietarios,
)
from .exportacion_politicas import (
    obtener_clave_seccion_exportacion,
    obtener_clave_seccion_normalizada_exportacion,
    obtener_titulo_seccion_exportacion,
    ordenar_cargos_exportacion,
)
from .exportacion_rows import (
    aplicar_vaciado_repetidos,
    construir_filas_exportacion,
    construir_filas_normalizadas,
    obtener_clave_total_general,
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
from .grilla_pof.proyecto_especial import (
    COLUMNAS_PROYECTO_ESPECIAL,
    armar_fila_proyecto_especial,
)
from .historial_service import (
    enriquecer_filas_con_historial_cantidad,
    enriquecer_filas_con_historial_observacion,
)
from .niveles_service import (
    NIVELES_VALIDOS as NOMBRES_NIVEL,
    limpiar_texto,
    normalizar_nivel,
    obtener_nombre_nivel,
)
from .reunidas_service import (
    FILTROS_AVANZADOS_DETALLE_CAMPOS,
    FILTROS_AVANZADOS_DETALLE_LABELS,
    FILTROS_DETALLE_PROYECTO,
    OPERADORES_FILTRO_DETALLE,
    _aplicar_filtros_avanzados_detalle_reunida,
    _aplicar_filtros_cargo_detalle_reunida,
    _aplicar_filtros_detalle_reunida,
    _construir_chips_filtros_detalle,
    _construir_opciones_filtros_detalle_reunida,
    _construir_querystring_detalle_con_filtros,
    _hay_filtros_detalle_reunida,
    _obtener_filtros_avanzados_detalle_reunida,
    _obtener_filtros_detalle_reunida,
    _valor_filtro_avanzado_detalle_label,
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

COLUMNAS_EXPORTACION_PROYECTO_ESPECIAL = (
    {
        "key": "proyecto_especial_cueanexo",
        "titulo": "CUEANEXO",
        "source": "cueanexo",
        "required": True,
        "visible_default": True,
    },
    {"key": "proyecto_especial_anexo_pof", "titulo": "Código(s) Anexo POF", "source": "anexo_pof", "visible_default": True},
    {"key": "proyecto_especial_cue", "titulo": "CUE", "source": "cue", "visible_default": True},
    {"key": "proyecto_especial_anexo", "titulo": "Anexo", "source": "anexo", "visible_default": True},
    {"key": "proyecto_especial_cuof", "titulo": "CUOF", "source": "cuof", "visible_default": True},
    {"key": "proyecto_especial_cui", "titulo": "CUI", "source": "cui", "visible_default": True},
    {"key": "proyecto_especial_establecimiento", "titulo": "Establecimiento", "source": "establecimiento", "visible_default": True},
    {"key": "proyecto_especial_oferta", "titulo": "Oferta", "source": "oferta", "visible_default": True},
    {"key": "proyecto_especial_zona_educativa", "titulo": "Zona Educativa", "source": "zona_educativa", "visible_default": True},
    {"key": "proyecto_especial_puntos_zona_educativa", "titulo": "Puntos Zona Educativa", "source": "puntos_zona_educativa", "visible_default": True},
    {"key": "proyecto_especial_ceic", "titulo": "CEIC", "source": "ceic", "visible_default": True},
    {"key": "proyecto_especial_cargo", "titulo": "Cargo", "source": "cargo", "visible_default": True},
    {"key": "proyecto_especial_cantidad", "titulo": "Cantidad", "source": "cantidad", "visible_default": True},
    {"key": "proyecto_especial_unidad", "titulo": "Unidad", "source": "unidad", "visible_default": True},
    {"key": "proyecto_especial_puntos", "titulo": "Puntos", "source": "puntos", "visible_default": True},
    {"key": "proyecto_especial_total", "titulo": "Total", "source": "total", "visible_default": True},
    {"key": "proyecto_especial_total_general", "titulo": "Total General", "source": "total_general", "visible_default": True},
    {"key": "proyecto_especial_estado_pof", "titulo": "Estado POF", "source": "estado_pof", "visible_default": True},
)

FUENTES_NO_REPETIR_PROYECTO_ESPECIAL = {
    "cueanexo",
    "cue",
    "anexo",
    "cuof",
    "cui",
    "establecimiento",
    "zona_educativa",
    "puntos_zona_educativa",
    "total_general",
}

CUEANEXOS_POR_PAGINA_EXPORTACION = 5

COLUMNAS_BUSQUEDA_EXPORTACION = (
    {"id": "cueanexo", "label": "CUE-Anexo"},
    {"id": "cuof", "label": "CUOF"},
    {"id": "ceic", "label": "CEIC"},
    {"id": "cargo", "label": "Cargo"},
    {"id": "puntos", "label": "Puntos"},
    {"id": "oferta", "label": "Oferta"},
    {"id": "estado_pof", "label": "Estado POF"},
    {"id": "observacion", "label": "Observación"},
)

FILTROS_AVANZADOS_QUERY_PARAMS = {
    "campo_filtro",
    "operador_filtro",
    "valor_filtro",
}

BUSQUEDA_EXPORTACION_A_FILTRO_AVANZADO = {
    "cueanexo": "cueanexo",
    "cuof": "cuof",
    "ceic": "ceic",
    "cargo": "cargo",
    "puntos": "puntos_asignados",
    "oferta": "oferta",
    "estado_pof": "estado_pof",
}

FILTRO_SIMPLE_PROYECTO_A_AVANZADO = {
    "cueanexo": "cueanexo",
    "cue_busqueda": "cue",
    "anexo": "anexo",
    "cuof": "cuof",
    "cui": "cui",
    "establecimiento": "nombre_establecimiento",
    "localidad": "localidad",
    "departamento": "departamento",
    "region": "region",
    "jornada": "jornada",
    "categoria": "categoria",
    "ambito": "ambito",
    "ceic": "ceic",
    "cargo": "cargo",
    "estado_pof": "estado_pof",
    "unidad_cantidad": "unidad_cantidad",
}

FILTRO_ZONA_EDUCATIVA_EXPORTACION = {
    "id": "zona_educativa",
    "label": "Zona Educativa",
    "tipo": "checklist",
    "operadores": "exact",
}

FILTROS_AVANZADOS_EXPORTACION_CAMPOS = []
for _filtro_exportacion in FILTROS_AVANZADOS_DETALLE_CAMPOS:
    FILTROS_AVANZADOS_EXPORTACION_CAMPOS.append(_filtro_exportacion)
    if _filtro_exportacion["id"] == "departamento":
        FILTROS_AVANZADOS_EXPORTACION_CAMPOS.append(
            FILTRO_ZONA_EDUCATIVA_EXPORTACION
        )

FILTROS_AVANZADOS_EXPORTACION_LABELS = {
    **FILTROS_AVANZADOS_DETALLE_LABELS,
    "zona_educativa": "Zona Educativa",
}


def _obtener_filtros_simples_proyecto_efectivos(
    filtros_simples,
    filtros_avanzados,
):
    """Da precedencia al criterio avanzado equivalente sobre filtros legacy."""
    campos_avanzados = {
        filtro.get("campo")
        for filtro in (filtros_avanzados or [])
        if filtro.get("campo")
    }
    return {
        clave: (
            ""
            if FILTRO_SIMPLE_PROYECTO_A_AVANZADO.get(clave) in campos_avanzados
            else valor
        )
        for clave, valor in (filtros_simples or {}).items()
    }


def _obtener_busquedas_columnas_exportacion_efectivas(
    busquedas,
    filtros_avanzados,
):
    """
    Evita aplicar dos criterios simultaneos sobre el mismo campo funcional.

    El filtro avanzado tiene precedencia sobre la busqueda rapida, igual que en
    Visualizacion. La URL puede conservar un col_* legacy, pero el queryset no
    queda accidentalmente restringido por ambos criterios.
    """
    campos_avanzados = {
        filtro.get("campo")
        for filtro in (filtros_avanzados or [])
        if filtro.get("campo")
    }
    return {
        columna_id: valor
        for columna_id, valor in (busquedas or {}).items()
        if BUSQUEDA_EXPORTACION_A_FILTRO_AVANZADO.get(columna_id)
        not in campos_avanzados
    }


def _obtener_filtros_avanzados_exportacion(request):
    """
    Reutiliza los filtros avanzados de Detalle y agrega Zona Educativa solo
    para Exportar, sin ampliar la UI de Detalle ni duplicar el resto del motor.
    """
    filtros = list(_obtener_filtros_avanzados_detalle_reunida(request))
    indices_existentes = {
        filtro.get("indice")
        for filtro in filtros
        if filtro.get("indice") is not None
    }
    campos = request.GET.getlist("campo_filtro")
    operadores = request.GET.getlist("operador_filtro")
    valores = request.GET.getlist("valor_filtro")

    for indice, campo_id in enumerate(campos):
        if indice in indices_existentes:
            continue
        if str(campo_id or "").strip() != "zona_educativa":
            continue

        operador = str(
            operadores[indice] if indice < len(operadores) else "2"
        ).strip()
        valor = str(
            valores[indice] if indice < len(valores) else ""
        ).strip()[:240]

        if not valor or operador not in {"2", "7"}:
            continue

        filtros.append({
            "indice": indice,
            "campo": "zona_educativa",
            "operador": operador,
            "valor": valor,
        })

    return sorted(
        filtros,
        key=lambda filtro: (
            filtro.get("indice") is None,
            filtro.get("indice") if filtro.get("indice") is not None else 0,
        ),
    )


def _aplicar_filtros_avanzados_exportacion(queryset, filtros_avanzados):
    """
    Aplica el motor compartido de Detalle y resuelve Zona Educativa sobre el
    snapshot vigente de la localizacion.
    """
    filtros_zona = [
        filtro
        for filtro in (filtros_avanzados or [])
        if filtro.get("campo") == "zona_educativa"
    ]
    filtros_compartidos = [
        filtro
        for filtro in (filtros_avanzados or [])
        if filtro.get("campo") != "zona_educativa"
    ]

    queryset = _aplicar_filtros_avanzados_detalle_reunida(
        queryset,
        filtros_compartidos,
    )

    valores_iguales = [
        filtro["valor"]
        for filtro in filtros_zona
        if filtro.get("operador") == "2"
    ]
    if valores_iguales:
        consulta_zona = Q()
        for valor in valores_iguales:
            consulta_zona |= Q(
                localizacion__snapshots_padron__vigente=True,
                localizacion__snapshots_padron__zona_educativa__iexact=valor,
            )
        queryset = queryset.filter(consulta_zona)

    for filtro in filtros_zona:
        if filtro.get("operador") != "7":
            continue
        queryset = queryset.exclude(
            Q(
                localizacion__snapshots_padron__vigente=True,
                localizacion__snapshots_padron__zona_educativa__iexact=filtro["valor"],
            )
        )

    return queryset.distinct() if filtros_zona else queryset


def _construir_opciones_filtros_exportacion():
    """
    Conserva las opciones lazy de Padrón y precarga únicamente Zona Educativa.

    Zona Educativa vive en snapshots POF, no en Padrón, y su catálogo es pequeño;
    una consulta DISTINCT evita agregar otro endpoint o tocar el de Detalle.
    """
    opciones = _construir_opciones_filtros_detalle_reunida(
        incluir_opciones_padron=False,
    )
    try:
        valores = (
            SnapshotPadronLocalizacionPof.objects
            .filter(vigente=True)
            .exclude(zona_educativa="")
            .exclude(zona_educativa__isnull=True)
            .order_by("zona_educativa")
            .values_list("zona_educativa", flat=True)
            .distinct()[:500]
        )
        opciones["zona_educativa"] = sorted(
            {
                str(valor).strip()
                for valor in valores
                if str(valor or "").strip()
            },
            key=str.casefold,
        )
    except (DatabaseError, ProgrammingError, OperationalError):
        opciones["zona_educativa"] = []

    return opciones


def _iterar_parametros_filtros_exportacion(request, incluir_simples=False):
    """
    Extrae solamente parametros funcionales de filtros para el Excel de vista.

    Conserva el orden y multiplicidad de las tripletas avanzadas, las busquedas
    col_* y, para Proyecto Especial, los filtros simples heredados de Detalle.
    """
    if request is None:
        return []

    filtros_simples = set(FILTROS_DETALLE_PROYECTO) if incluir_simples else set()
    parametros = []
    for clave, valores in request.GET.lists():
        if (
            clave.startswith("col_")
            or clave in FILTROS_AVANZADOS_QUERY_PARAMS
            or clave in filtros_simples
        ):
            parametros.extend((clave, valor) for valor in valores)
    return parametros


def _descripcion_filtros_exportacion(
    busquedas=None,
    filtros_avanzados=None,
    filtros_simples=None,
    nombres_filtros_simples=(),
):
    """Construye una descripcion legible y fiel del alcance filtrado."""
    partes = []

    etiquetas_busqueda = {
        columna["id"]: columna["label"]
        for columna in COLUMNAS_BUSQUEDA_EXPORTACION
    }
    for columna_id, valor in (busquedas or {}).items():
        partes.append(f"{etiquetas_busqueda.get(columna_id, columna_id)}: {valor}")

    if filtros_simples:
        chips_simples = _construir_chips_filtros_detalle(
            filtros_simples,
            {},
            {},
            nombres_filtros_simples,
        )
        partes.extend(
            f"{chip['etiqueta']}: {chip['valor']}"
            for chip in chips_simples
        )

    for filtro in filtros_avanzados or []:
        campo_id = filtro.get("campo", "")
        operador = filtro.get("operador", "0")
        valor = filtro.get("valor", "")
        etiqueta = FILTROS_AVANZADOS_EXPORTACION_LABELS.get(campo_id, campo_id)
        operador_label = OPERADORES_FILTRO_DETALLE.get(
            operador,
            OPERADORES_FILTRO_DETALLE["0"],
        )
        valor_label = _valor_filtro_avanzado_detalle_label(campo_id, valor)
        partes.append(f"{etiqueta} {operador_label}: {valor_label}")

    return " · ".join(partes) if partes else "Sin filtros"


def _obtener_busquedas_columnas_exportacion(request):
    """
    Lee todas las búsquedas por columna permitidas para Reunidas comunes.

    - Recorre una whitelist fija de las ocho columnas comunes.
    - Ignora nombres de parámetros que no pertenezcan a esa whitelist.
    - Limita la longitud del texto antes de construir el filtro ORM.
    - Conserva el orden funcional de la whitelist y solo devuelve valores no vacíos.
    """
    busquedas = {}
    for columna in COLUMNAS_BUSQUEDA_EXPORTACION:
        columna_id = columna["id"]
        valor = limpiar_texto(request.GET.get(f"col_{columna_id}", ""), 120)
        if valor:
            busquedas[columna_id] = valor
    return busquedas


def _consulta_estado_pof_exportacion(valor):
    """
    Construye la consulta segura para Estado POF.

    - Prioriza coincidencias exactas contra código o etiqueta visible.
    - Si no hay coincidencia exacta, permite coincidencias parciales entre las choices.
    - Mantiene la lista de estados derivada de las choices del modelo.
    - No acepta nombres de campo ni expresiones ORM desde el navegador.
    """
    valor_normalizado = valor.casefold()
    choices = tuple(CargoPof.EstadoPof.choices)
    coincidencias_exactas = [
        codigo
        for codigo, etiqueta in choices
        if valor_normalizado in {
            str(codigo).casefold(),
            str(etiqueta).casefold(),
        }
    ]
    if coincidencias_exactas:
        return Q(estado_pof__in=coincidencias_exactas)

    coincidencias_parciales = [
        codigo
        for codigo, etiqueta in choices
        if (
            valor_normalizado in str(codigo).casefold()
            or valor_normalizado in str(etiqueta).casefold()
        )
    ]
    if coincidencias_parciales:
        return Q(estado_pof__in=coincidencias_parciales)

    return Q(pk__in=[])


def _aplicar_busqueda_columna_exportacion(cargos_queryset, columna_id, valor):
    """
    Aplica la búsqueda común al queryset ya limitado a una Reunida.

    - Resuelve cada columna mediante ramas explícitas y parametrizadas.
    - Busca Oferta en el cargo o, cuando está vacía, en el snapshot vigente.
    - Mantiene el filtrado en base de datos antes de paginar el preview.
    - Devuelve el queryset sin modificar cargos ni materializar filas.
    """
    if not valor:
        return cargos_queryset

    if columna_id == "cueanexo":
        return cargos_queryset.filter(localizacion__cueanexo__icontains=valor)
    if columna_id == "cuof":
        return cargos_queryset.filter(localizacion__cuof__icontains=valor)
    if columna_id == "ceic":
        return cargos_queryset.annotate(
            ceic_busqueda_exportacion=Cast("ceic", CharField()),
        ).filter(ceic_busqueda_exportacion__icontains=valor)
    if columna_id == "cargo":
        return cargos_queryset.filter(cargo__icontains=valor)
    if columna_id == "puntos":
        queryset = cargos_queryset.annotate(
            puntos_busqueda_exportacion=Cast("puntos_asignados", CharField()),
        )
        consulta = Q(puntos_busqueda_exportacion__icontains=valor)
        try:
            numero = Decimal(valor.replace(",", "."))
        except (InvalidOperation, TypeError, ValueError):
            numero = None
        if numero is not None:
            consulta |= Q(puntos_asignados=numero)
        return queryset.filter(consulta)
    if columna_id == "oferta":
        return cargos_queryset.filter(
            Q(oferta__icontains=valor)
            | (
                Q(oferta="")
                & Q(
                    localizacion__snapshots_padron__vigente=True,
                    localizacion__snapshots_padron__oferta__icontains=valor,
                )
            )
        ).distinct()
    if columna_id == "estado_pof":
        return cargos_queryset.filter(_consulta_estado_pof_exportacion(valor))
    if columna_id == "observacion":
        return cargos_queryset.filter(observacion__icontains=valor)

    return cargos_queryset


def _aplicar_busquedas_columnas_exportacion(cargos_queryset, busquedas):
    """Aplica todas las búsquedas de columnas en cadena, con semántica AND."""
    for columna_id, valor in busquedas.items():
        cargos_queryset = _aplicar_busqueda_columna_exportacion(
            cargos_queryset,
            columna_id,
            valor,
        )
    return cargos_queryset


def _obtener_columna_oferta_exportacion():
    """
    Define Oferta como columna obligatoria de Exportar Reunida.

    - Se muestra en todos los niveles de Reunidas comunes.
    - Repite el valor en cada fila de cargo.
    - Se ubica después del bloque CUEANEXO + Código(s) Anexo POF.
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
    """
    Inserta Oferta después de Anexo POF cuando está visible.

    Si Anexo POF no forma parte del conjunto visible, conserva el fallback
    histórico inmediatamente después de CUEANEXO.
    """
    columna_oferta = _obtener_columna_oferta_exportacion()
    columna_key = columna_oferta["key"]

    columnas_disponibles_resultado = [
        columna
        for columna in columnas_disponibles
        if columna.get("key") != columna_key
    ]
    columna_anexo_pof = next(
        (
            columna
            for columna in columnas_disponibles_resultado
            if columna.get("source") == "anexo_pof"
        ),
        None,
    )
    anexo_pof_key = (
        columna_anexo_pof.get("key")
        if columna_anexo_pof
        else None
    )
    indice_disponible = (
        columnas_disponibles_resultado.index(columna_anexo_pof) + 1
        if columna_anexo_pof
        else 1
    )
    columnas_disponibles_resultado.insert(indice_disponible, columna_oferta)

    columnas_default_resultado = [
        key for key in columnas_default_keys if key != columna_key
    ]
    indice_default = (
        columnas_default_resultado.index(anexo_pof_key) + 1
        if anexo_pof_key in columnas_default_resultado
        else 1
    )
    columnas_default_resultado.insert(indice_default, columna_key)

    columnas_visibles_resultado = [
        key for key in columnas_visibles_keys if key != columna_key
    ]
    indice_visible = (
        columnas_visibles_resultado.index(anexo_pof_key) + 1
        if anexo_pof_key in columnas_visibles_resultado
        else 1
    )
    columnas_visibles_resultado.insert(indice_visible, columna_key)

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


def _resolver_propietario_anexo_pof_fila_exportacion(
    fila,
    *,
    es_proyecto_especial,
):
    cue = str(fila.get("cue") or "").strip()
    if len(cue) == 7 and cue.isdigit():
        return {
            "tipo": TIPO_PROPIETARIO_CUE,
            "valor": cue,
        }

    if es_proyecto_especial:
        cuof = str(fila.get("cuof") or "").strip()
        if cuof:
            return {
                "tipo": TIPO_PROPIETARIO_CUOF,
                "valor": cuof,
            }

    return None


def _enriquecer_filas_exportacion_con_anexo_pof(
    filas_normalizadas,
    *,
    es_proyecto_especial,
):
    """
    Agrega el texto de Código(s) Anexo POF a filas normalizadas en una sola consulta.

    Reunida usa exclusivamente CUE. Proyecto Especial usa CUE con precedencia
    estricta y CUOF sólo cuando la fila no dispone de un CUE válido.
    """
    filas = list(filas_normalizadas or [])
    propietarios = []
    claves_por_indice = {}

    for indice, fila in enumerate(filas):
        fila["anexo_pof"] = ""
        propietario = _resolver_propietario_anexo_pof_fila_exportacion(
            fila,
            es_proyecto_especial=es_proyecto_especial,
        )
        if propietario is None:
            continue

        clave = (propietario["tipo"], propietario["valor"])
        claves_por_indice[indice] = clave
        propietarios.append(propietario)

    mapa_codigos = obtener_codigos_activos_propietarios(
        propietarios=propietarios,
    )

    for indice, clave in claves_por_indice.items():
        filas[indice]["anexo_pof"] = ", ".join(
            mapa_codigos.get(clave, [])
        )

    return filas


def _obtener_clave_propietario_anexo_pof_proyecto(fila, indice=None):
    propietario = _resolver_propietario_anexo_pof_fila_exportacion(
        fila,
        es_proyecto_especial=True,
    )
    if propietario is not None:
        return (propietario["tipo"], propietario["valor"])

    identificador = fila.get("localizacion_id") or fila.get("cargo_id") or indice
    return ("LOCALIZACION", identificador)


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


def obtener_clave_total_general_cueanexo_reunida(fila_dict, indice=None):
    """Resuelve el grupo de Total General estándar de Exportar POF.

    Replica la jerarquía del Visualizador: CUEANEXO, CUOF y localización. El
    cargo o índice se usa únicamente como aislamiento defensivo final.
    """
    cueanexo = str(fila_dict.get("cueanexo", "") or "").strip()
    if cueanexo:
        return f"CUEANEXO:{cueanexo}"

    cuof = str(fila_dict.get("cuof", "") or "").strip()
    if cuof:
        return f"CUOF:{cuof}"

    localizacion_id = fila_dict.get("localizacion_id")
    if localizacion_id not in (None, ""):
        return f"LOCALIZACION:{localizacion_id}"

    identificador = fila_dict.get("cargo_id") or indice
    return f"FILA:{identificador}"


def obtener_clave_total_general_visual_reunida(fila_dict, indice=None):
    """
    Resuelve la clave por CUE usada por políticas `REPETIR_POR_CUE` legacy.

    - Usa el CUE normalizado o derivado desde `cueanexo`.
    - Si no existe CUE confiable, aísla la fila por localizacion/cargo para no mezclarla.
    - No define la semántica del Total General estándar de Exportar POF.
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
    clave_cue_anterior = None
    clave_total_general_anterior = None
    filas_con_metadata = _agregar_metadata_grupo_visual_reunida(filas_normalizadas)

    for indice, fila in enumerate(filas_con_metadata):
        clave_actual = obtener_clave_grupo_visual_reunida(fila, indice=indice)
        clave_cue_actual = obtener_clave_total_general_visual_reunida(
            fila,
            indice=indice,
        )
        clave_total_general_actual = (
            obtener_clave_total_general_cueanexo_reunida(fila, indice=indice)
        )
        misma_localizacion = clave_actual == clave_anterior
        mismo_cue = clave_cue_actual == clave_cue_anterior
        mismo_grupo_total_general = (
            clave_total_general_actual == clave_total_general_anterior
        )
        fila_render = []

        for columna in columnas:
            source = columna["source"]
            valor = fila.get(source, "")
            if source in {"total_general", "total_general_exportacion"}:
                if mismo_grupo_total_general:
                    valor = ""
            elif (
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
        clave_cue_anterior = clave_cue_actual
        clave_total_general_anterior = clave_total_general_actual

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
        if valor is None:
            valor = ""
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
        "cueanexo": str(fila_normalizada.get("cueanexo", "") or "").strip(),
        "cuof": str(fila_normalizada.get("cuof", "") or "").strip(),
        "mostrar_afectar": False,
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
    identidad_afectar="CUEANEXO",
):
    separadores_filas = separadores_filas or []
    filas_normalizadas = filas_normalizadas or []
    secciones_preview = []
    claves_afectar_vistas = set()

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
            fila_preview = _construir_fila_preview(
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

            if identidad_afectar == "CUOF":
                clave_afectar = fila_preview["cuof"]
            else:
                clave_afectar = normalizar_cueanexo_exportacion(
                    fila_preview["cueanexo"]
                )

            fila_preview["mostrar_afectar"] = bool(
                clave_afectar
                and clave_afectar not in claves_afectar_vistas
            )
            if clave_afectar:
                claves_afectar_vistas.add(clave_afectar)

            filas_preview.append(fila_preview)

        seccion_preview["filas"] = filas_preview
        secciones_preview.append(seccion_preview)

    return secciones_preview


def _anotar_claves_preview_reunida(cargos_queryset):
    """
    Anota la unidad DB-first usada para paginar el preview de Reunida.

    - Usa CUEANEXO completo como unidad funcional de establecimiento/localizacion.
    - Aisla por localizacion cualquier fila legacy sin CUEANEXO utilizable.
    - Mantiene la consulta perezosa para no materializar cargos fuera de pagina.
    """
    cueanexo_disponible = (
        ~Q(localizacion__cueanexo="")
        & Q(localizacion__cueanexo__isnull=False)
    )
    return cargos_queryset.annotate(
        _unidad_paginacion_exportacion=Case(
            When(
                cueanexo_disponible,
                then=Concat(
                    Value("CUEANEXO:"),
                    "localizacion__cueanexo",
                    output_field=CharField(),
                ),
            ),
            default=Concat(
                Value("_sin_cueanexo:"),
                Cast("localizacion_id", CharField()),
                output_field=CharField(),
            ),
            output_field=CharField(),
        ),
    )


def _paginar_unidades_preview_reunida(cargos_queryset, request):
    """
    Selecciona primero los cinco CUEANEXO del preview mediante una consulta agrupada.

    - Respeta el orden funcional actual usando la primera aparicion de cada
      unidad y sus desempates de localizacion, CEIC e identificador.
    - Devuelve solo las claves de las unidades de la pagina y el objeto Page
      para construir los metadatos de navegacion.
    - No consulta ni normaliza cargos fuera de las unidades seleccionadas.
    """
    unidades_queryset = (
        _anotar_claves_preview_reunida(cargos_queryset)
        .values("_unidad_paginacion_exportacion")
        .annotate(
            _primer_cueanexo=Min("localizacion__cueanexo"),
            _primer_cuof=Min("localizacion__cuof"),
            _primer_ceic=Min("ceic"),
            _primer_id=Min("id"),
        )
        .order_by(
            "_primer_cueanexo",
            "_primer_cuof",
            "_primer_ceic",
            "_primer_id",
            "_unidad_paginacion_exportacion",
        )
        .values_list("_unidad_paginacion_exportacion", flat=True)
    )
    paginator = Paginator(
        unidades_queryset,
        CUEANEXOS_POR_PAGINA_EXPORTACION,
    )
    page_obj = paginator.get_page(request.GET.get("page", 1))
    return list(page_obj.object_list), page_obj


def _restringir_queryset_preview_reunida(cargos_queryset, unidades_pagina):
    """
    Restringe el queryset de cargos a los CUEANEXO de la pagina actual.

    - Mantiene todos los cargos pertenecientes a cada CUEANEXO seleccionado.
    - Conserva el orden de consulta base antes de aplicar la politica exacta
      de orden de cada nivel en `ordenar_cargos_exportacion`.
    - Devuelve un queryset vacio cuando la pagina no tiene unidades.
    """
    if not unidades_pagina:
        return cargos_queryset.none()

    return (
        _anotar_claves_preview_reunida(cargos_queryset)
        .filter(_unidad_paginacion_exportacion__in=unidades_pagina)
        .order_by(
            "localizacion__cueanexo",
            "localizacion__cuof",
            "ceic",
            "id",
        )
    )


def _anotar_clave_total_general_cueanexo_reunida(queryset):
    """Anota en SQL la clave canónica del Total General estándar."""
    queryset = queryset.annotate(
        _cueanexo_total_general_exportacion=Trim("localizacion__cueanexo"),
        _cuof_total_general_exportacion=Trim("localizacion__cuof"),
    )
    return queryset.annotate(
        _clave_total_general_exportacion=Case(
            When(
                Q(_cueanexo_total_general_exportacion__isnull=False)
                & ~Q(_cueanexo_total_general_exportacion=""),
                then=Concat(
                    Value("CUEANEXO:"),
                    "_cueanexo_total_general_exportacion",
                ),
            ),
            When(
                Q(_cuof_total_general_exportacion__isnull=False)
                & ~Q(_cuof_total_general_exportacion=""),
                then=Concat(
                    Value("CUOF:"),
                    "_cuof_total_general_exportacion",
                ),
            ),
            default=Concat(
                Value("LOCALIZACION:"),
                Cast("localizacion_id", CharField()),
            ),
            output_field=CharField(),
        )
    )


def _obtener_totales_generales_preview_reunida(
    cargos_queryset,
    nivel_codigo,
    unidades_pagina=None,
):
    """
    Obtiene los totales generales completos de los grupos de la pagina.

    - Suma exclusivamente cargos AFECTADOS de los CUEANEXO seleccionados.
    - Agrupa cada CUEANEXO de manera independiente, con fallback a CUOF y
      localización, igual que el Visualizador.
    - Con `unidades_pagina` limita la lectura al preview; sin ese argumento
      calcula el conjunto completo requerido por Excel.
    - Devuelve un mapping vacio cuando el filtro no produjo unidades para la
      pagina, sin intentar anotar un queryset `.none()`.
    - No modifica cargos ni consulta grupos fuera del alcance solicitado.
    """
    if unidades_pagina is not None and not unidades_pagina:
        return {}

    cargos_pagina = (
        _restringir_queryset_preview_reunida(
            cargos_queryset,
            unidades_pagina,
        )
        if unidades_pagina is not None
        else _anotar_claves_preview_reunida(cargos_queryset)
    )
    cargos_pagina = _anotar_clave_total_general_cueanexo_reunida(
        cargos_pagina.filter(estado_pof=CargoPof.EstadoPof.AFECTADO)
    )

    return {
        agregado["_clave_total_general_exportacion"]: (
            agregado.get("_total_general") or Decimal("0")
        )
        for agregado in (
            cargos_pagina
            .order_by()
            .values("_clave_total_general_exportacion")
            .annotate(_total_general=Sum("total"))
        )
    }


def _aplicar_totales_generales_preview_reunida(
    filas_normalizadas,
    nivel_codigo,
    totales_generales,
):
    """
    Sustituye en memoria el total parcial por el agregado completo de la pagina.

    - Usa la clave canónica por CUEANEXO del preview y del Excel común.
    - Mantiene cero cuando un grupo no tiene cargos AFECTADOS.
    - Solo ajusta el diccionario renderizado; nunca escribe en persistencia.
    """
    if totales_generales is None:
        return

    for indice, fila in enumerate(filas_normalizadas):
        clave_total = obtener_clave_total_general_cueanexo_reunida(
            fila,
            indice=indice,
        )
        total_general = totales_generales.get(clave_total, Decimal("0"))
        fila["total_general"] = total_general
        fila["total_general_exportacion"] = total_general


def _construir_paginacion_preview_reunida(page_obj, request):
    """
    Serializa los metadatos del paginador DB-first del preview común.

    - Mantiene el rango de CUEANEXO, anterior/siguiente y el rango elidido de
      paginas sin recorrer filas normalizadas.
    - Excluye `page` y `accion` de los enlaces de preview para no limitar ni
      contaminar Excel.
    - Conserva alias legacy de CUE para compatibilidad interna transitoria.
    """
    paginator = page_obj.paginator

    parametros_preview = []
    for clave, valores in request.GET.lists():
        if clave in {"page", "accion"}:
            continue
        parametros_preview.extend((clave, valor) for valor in valores)

    total_cueanexo = paginator.count
    total_paginas = (
        (total_cueanexo + CUEANEXOS_POR_PAGINA_EXPORTACION - 1)
        // CUEANEXOS_POR_PAGINA_EXPORTACION
        if total_cueanexo
        else 0
    )
    primer_cueanexo = (
        ((page_obj.number - 1) * CUEANEXOS_POR_PAGINA_EXPORTACION) + 1
        if total_cueanexo
        else 0
    )
    ultimo_cueanexo = (
        min(
            page_obj.number * CUEANEXOS_POR_PAGINA_EXPORTACION,
            total_cueanexo,
        )
        if total_cueanexo
        else 0
    )

    return {
        "mostrar": bool(total_cueanexo),
        "pagina_actual": page_obj.number,
        "total_paginas": total_paginas,
        "cueanexos_por_pagina": CUEANEXOS_POR_PAGINA_EXPORTACION,
        "total_cueanexo": total_cueanexo,
        "primer_cueanexo": primer_cueanexo,
        "ultimo_cueanexo": ultimo_cueanexo,
        "cues_por_pagina": CUEANEXOS_POR_PAGINA_EXPORTACION,
        "total_cue": total_cueanexo,
        "primer_cue": primer_cueanexo,
        "ultimo_cue": ultimo_cueanexo,
        "tiene_anterior": page_obj.has_previous(),
        "pagina_anterior": (
            page_obj.previous_page_number() if page_obj.has_previous() else None
        ),
        "tiene_siguiente": page_obj.has_next(),
        "pagina_siguiente": (
            page_obj.next_page_number() if page_obj.has_next() else None
        ),
        "page_range": (
            list(paginator.get_elided_page_range(number=page_obj.number))
            if total_cueanexo
            else []
        ),
        "querystring_base": urlencode(parametros_preview),
    }


def _armar_excel_querystring_base(
    base_params,
    columnas_visibles_keys,
    request=None,
    alcance="vista",
    incluir_filtros_simples=False,
):
    """
    Construye un enlace Excel coherente con Vista actual / Todos los datos.

    Vista actual conserva únicamente filtros funcionales; Todos los datos ignora
    cualquier filtro aunque la URL origen todavía los contenga.
    """
    if not columnas_visibles_keys:
        return ""

    params = [
        *base_params.items(),
        ("accion", "excel"),
        ("alcance", alcance),
    ]
    if request is not None and alcance == "vista":
        params.extend(
            _iterar_parametros_filtros_exportacion(
                request,
                incluir_simples=incluir_filtros_simples,
            )
        )
    params.extend(
        ("visible_col", key)
        for key in columnas_visibles_keys
    )
    return urlencode(params)


def _armar_excel_querystring_reunida(
    anio,
    nivel_codigo,
    columnas_visibles_keys,
    request=None,
    alcance="vista",
):
    return _armar_excel_querystring_base(
        {
            "anio": anio,
            "nivel": nivel_codigo,
        },
        columnas_visibles_keys,
        request=request,
        alcance=alcance,
    )


def _armar_excel_querystring_proyecto(
    proyecto_especial_id,
    columnas_visibles_keys,
    request=None,
    alcance="vista",
):
    return _armar_excel_querystring_base(
        {
            "cabecera_tipo": "PROYECTO_ESPECIAL",
            "proyecto_especial_id": proyecto_especial_id,
        },
        columnas_visibles_keys,
        request=request,
        alcance=alcance,
        incluir_filtros_simples=True,
    )



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


def _clave_orden_cargo_proyecto_especial(cargo):
    localizacion = cargo.localizacion
    cueanexo = normalizar_cueanexo_exportacion(localizacion.cueanexo)
    cuof = str(localizacion.cuof or "").strip()
    ceic = str(cargo.ceic or "").strip()
    orden_ceic = (0, int(ceic)) if ceic.isdigit() else (1, ceic)

    return (
        0 if cueanexo else 1,
        cueanexo[:7] if cueanexo else "",
        cueanexo[7:] if cueanexo else "",
        cuof,
        orden_ceic,
        cargo.id or 0,
    )


def _obtener_filas_normalizadas_exportacion_proyecto(
    cargos_queryset,
    incluir_historial_cantidad=False,
    incluir_historial_observacion=False,
):
    cargos_ordenados = sorted(
        list(cargos_queryset),
        key=_clave_orden_cargo_proyecto_especial,
    )
    filas_normalizadas = construir_filas_normalizadas(cargos_ordenados)
    filas_normalizadas = _enriquecer_filas_exportacion_con_anexo_pof(
        filas_normalizadas,
        es_proyecto_especial=True,
    )
    if incluir_historial_cantidad:
        enriquecer_filas_con_historial_cantidad(filas_normalizadas)
    if incluir_historial_observacion:
        enriquecer_filas_con_historial_observacion(filas_normalizadas)
    return filas_normalizadas


def _obtener_clave_grupo_proyecto_especial(fila, indice=None):
    cueanexo = normalizar_cueanexo_exportacion(fila.get("cueanexo", ""))
    if cueanexo:
        return f"CUEANEXO:{cueanexo}"

    cuof = str(fila.get("cuof", "") or "").strip()
    if cuof:
        return f"CUOF:{cuof}"

    identificador = fila.get("localizacion_id") or fila.get("cargo_id") or indice
    return f"LOCALIZACION:{identificador}"


def _proyectar_filas_exportacion_proyecto(filas_normalizadas, columnas):
    filas = []
    clave_anterior = None
    clave_propietario_anexo_pof_anterior = None

    for indice, fila in enumerate(filas_normalizadas):
        clave_actual = _obtener_clave_grupo_proyecto_especial(fila, indice)
        clave_propietario_anexo_pof_actual = (
            _obtener_clave_propietario_anexo_pof_proyecto(fila, indice)
        )
        misma_localizacion = clave_actual == clave_anterior
        mismo_propietario_anexo_pof = (
            clave_propietario_anexo_pof_actual
            == clave_propietario_anexo_pof_anterior
        )
        fila_render = []

        for columna in columnas:
            source = columna["source"]
            valor = fila.get(source, "")
            if source == "anexo_pof" and mismo_propietario_anexo_pof:
                valor = ""
            elif (
                misma_localizacion
                and source in FUENTES_NO_REPETIR_PROYECTO_ESPECIAL
            ):
                valor = ""
            fila_render.append(valor)

        filas.append(fila_render)
        clave_anterior = clave_actual
        clave_propietario_anexo_pof_anterior = (
            clave_propietario_anexo_pof_actual
        )

    return filas


def _obtener_separadores_grupo_visual_proyecto(filas_normalizadas):
    separadores = []
    clave_anterior = None
    cue_anterior = None
    cueanexo_anterior = None

    for indice, fila in enumerate(filas_normalizadas):
        clave_actual = _obtener_clave_grupo_proyecto_especial(fila, indice)
        cueanexo_actual = normalizar_cueanexo_exportacion(
            fila.get("cueanexo", "")
        )
        cue_actual = cueanexo_actual[:7] if cueanexo_actual else ""
        cambio_grupo = bool(separadores and clave_actual != clave_anterior)
        es_inicio_cue = bool(
            cambio_grupo
            and (
                not cueanexo_actual
                or not cue_anterior
                or cue_actual != cue_anterior
            )
        )
        es_inicio_anexo = bool(
            cambio_grupo
            and cueanexo_actual
            and cue_actual == cue_anterior
            and cueanexo_actual != cueanexo_anterior
        )

        separadores.append({
            "es_inicio_cue": es_inicio_cue,
            "es_inicio_anexo": es_inicio_anexo,
        })
        clave_anterior = clave_actual
        cue_anterior = cue_actual or None
        cueanexo_anterior = cueanexo_actual or None

    return separadores


def _construir_seccion_unica_exportacion(filas):
    if not filas:
        return []
    return [{
        "clave": "PROYECTO_ESPECIAL",
        "titulo": "",
        "filas": filas,
        "indices_filas": list(range(len(filas))),
        "cantidad_filas": len(filas),
    }]


def _resolver_columnas_exportacion_proyecto(request, columna_observacion):
    columnas_base = [
        {**columna, "required": columna.get("required", False)}
        for columna in COLUMNAS_EXPORTACION_PROYECTO_ESPECIAL
    ]
    columnas_base.append({
        **columna_observacion,
        "required": False,
    })
    columnas_base = _agregar_metadata_cantidad_preview(columnas_base)
    columnas_default_keys = [
        columna["key"]
        for columna in columnas_base
        if columna.get("visible_default", False)
    ]
    visibles_solicitadas = [
        limpiar_texto(valor, 120)
        for valor in request.GET.getlist("visible_col")
        if limpiar_texto(valor, 120)
    ] if request else []

    if visibles_solicitadas:
        visibles_set = set(visibles_solicitadas)
        columnas_visibles_keys = [
            columna["key"]
            for columna in columnas_base
            if (
                columna["key"] in visibles_set
                or columna.get("source") in visibles_set
            )
        ]
    else:
        columnas_visibles_keys = list(columnas_default_keys)

    for columna in columnas_base:
        if (
            columna.get("required")
            and columna["key"] not in columnas_visibles_keys
        ):
            columnas_visibles_keys.insert(0, columna["key"])

    columnas_disponibles = _marcar_columnas_disponibles(
        columnas_base,
        columnas_default_keys,
        columnas_visibles_keys,
    )
    return (
        columnas_disponibles,
        columnas_default_keys,
        columnas_visibles_keys,
    )


def _obtener_filas_reales_exportacion(
    columnas,
    cargos_queryset,
    nivel_codigo=None,
    incluir_historial_cantidad=False,
    incluir_historial_observacion=False,
    incluir_historial_estado=False,
    totales_generales=None,
):
    """
    Construye filas normalizadas para el conjunto de cargos recibido.

    - Mantiene las politicas de orden y render existentes.
    - Permite que el preview comun limite antes el queryset y sus historiales.
    - Corrige en memoria los totales generales cuando fueron agregados sobre
      todos los cargos de los CUE seleccionados.
    """
    cargos_ordenados = ordenar_cargos_exportacion(cargos_queryset, nivel_codigo)

    if nivel_codigo:
        grilla = construir_grilla_pof_desde_cargos(
            cargos=cargos_ordenados,
            nivel_codigo=nivel_codigo,
            contexto="REUNIDA",
            incluir_historial_cantidad=incluir_historial_cantidad,
            incluir_historial_estado=incluir_historial_estado,
        )
        filas_normalizadas = grilla["filas_normalizadas"]
        filas_normalizadas = _enriquecer_filas_exportacion_con_anexo_pof(
            filas_normalizadas,
            es_proyecto_especial=False,
        )
        if incluir_historial_observacion:
            enriquecer_filas_con_historial_observacion(filas_normalizadas)
        _aplicar_totales_generales_preview_reunida(
            filas_normalizadas,
            nivel_codigo,
            totales_generales,
        )
        filas_exportacion = construir_filas_exportacion(
            grilla["schema"],
            filas_normalizadas,
        )
        return filas_exportacion, filas_normalizadas

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
    columna_observacion = _obtener_columna_observacion_exportacion()
    (
        columnas_disponibles,
        columnas_default_keys,
        columnas_visibles_keys,
    ) = _resolver_columnas_exportacion_proyecto(
        request,
        columna_observacion,
    )
    columnas_exportacion_config = [
        columna
        for columna in columnas_disponibles
        if columna["key"] in columnas_visibles_keys
    ]
    columnas = [
        columna["titulo"]
        for columna in columnas_exportacion_config
    ]
    mostrar_columna_modificacion_cantidad = any(
        columna.get("es_columna_cantidad")
        and columna["key"] in columnas_visibles_keys
        for columna in columnas_disponibles
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
    proyecto_obj = None
    es_excel = bool(request and request.GET.get("accion") == "excel")
    alcance_solicitado = request.GET.get("alcance") if request else ""
    alcance_excel = (
        alcance_solicitado
        if alcance_solicitado in {"vista", "todos"}
        else "todos"
    )
    filtros_detalle = _obtener_filtros_detalle_reunida(request) if request else {}
    filtros_avanzados_exportacion = (
        _obtener_filtros_avanzados_exportacion(request)
        if request
        else []
    )
    filtros_detalle_efectivos = _obtener_filtros_simples_proyecto_efectivos(
        filtros_detalle,
        filtros_avanzados_exportacion,
    )
    filtros_detalle_activos = (
        (
            _hay_filtros_detalle_reunida(
                filtros_detalle_efectivos,
                FILTROS_DETALLE_PROYECTO,
            )
            or bool(filtros_avanzados_exportacion)
        )
        if request
        else False
    )

    if not proyecto_especial_id.isdigit():
        mensaje_exportacion = "Debe seleccionar un Proyecto Especial POF valido."
    else:
        try:
            proyecto_obj = ProyectosEspecialesPof.objects.get(pk=proyecto_especial_id)
            cargos_exportacion = _obtener_cargos_exportacion_proyecto(proyecto_especial_id)
            aplicar_filtros = request is not None and (
                not es_excel or alcance_excel == "vista"
            )
            if aplicar_filtros:
                cargos_exportacion, _mensaje_filtros, _errores_filtros = _aplicar_filtros_detalle_reunida(
                    cargos_exportacion,
                    filtros_detalle_efectivos,
                    incluir_cui=True,
                )
                cargos_exportacion = _aplicar_filtros_avanzados_exportacion(
                    cargos_exportacion,
                    filtros_avanzados_exportacion,
                )
                cargos_exportacion, _mensaje_cargo, _errores_cargo = _aplicar_filtros_cargo_detalle_reunida(
                    cargos_exportacion,
                    filtros_detalle_efectivos,
                )
            filas_normalizadas_exportacion = _obtener_filas_normalizadas_exportacion_proyecto(
                cargos_exportacion,
                incluir_historial_cantidad=(
                    request is not None
                    and request.GET.get("accion") != "excel"
                ),
                incluir_historial_observacion=(
                    request is not None
                    and request.GET.get("accion") != "excel"
                ),
            )
            filas_exportacion = _proyectar_filas_exportacion_proyecto(
                filas_normalizadas_exportacion,
                columnas_exportacion_config,
            )
            filas_exportacion_globales = _proyectar_filas_exportacion_proyecto(
                filas_normalizadas_exportacion,
                columnas_disponibles,
            )
            separadores_filas_exportacion = (
                _obtener_separadores_grupo_visual_proyecto(
                    filas_normalizadas_exportacion
                )
            )
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

    secciones_exportacion = _construir_seccion_unica_exportacion(
        filas_exportacion
    )
    secciones_exportacion_globales = _construir_seccion_unica_exportacion(
        filas_exportacion_globales
    )
    secciones_preview = _construir_secciones_preview(
        secciones_exportacion_globales,
        columnas_disponibles,
        columnas_visibles_keys,
        separadores_filas_exportacion,
        filas_normalizadas=filas_normalizadas_exportacion,
        identidad_afectar="CUOF",
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
    excel_querystring = (
        _armar_excel_querystring_proyecto(
            proyecto_obj.id,
            columnas_visibles_keys,
            request=request,
            alcance="vista",
        )
        if proyecto_obj
        else ""
    )
    titulo_excel = (
        f"Proyecto Especial POF - {nombre} {anio} - Resolución: {resolucion}"
    ).strip()

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
        "alcance_excel": alcance_excel,
        "filtros_excel": _descripcion_filtros_exportacion(
            filtros_avanzados=filtros_avanzados_exportacion,
            filtros_simples=filtros_detalle_efectivos,
            nombres_filtros_simples=FILTROS_DETALLE_PROYECTO,
        ),
        "filtros_exportacion_activos": filtros_detalle_activos,
        "filtros_avanzados_exportacion": filtros_avanzados_exportacion,
        "filtros_exportacion_campos": FILTROS_AVANZADOS_EXPORTACION_CAMPOS,
        "filtros_exportacion_opciones": _construir_opciones_filtros_exportacion(),
        "filtros_simple_exportacion_nombres": FILTROS_DETALLE_PROYECTO,
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
        "columnas_preview_config": columnas_disponibles,
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
        "nombre_archivo": _obtener_nombre_archivo_proyecto(proyecto_obj) if proyecto_obj else "Proyecto_Especial_POF.xlsx",
        "titulo_hoja": nombre,
        "titulo_excel": titulo_excel,
    }


def construir_contexto_exportacion(request):
    """
    Construye el contexto de exportación manteniendo separado el preview del Excel.

    - Usa solo los cinco CUEANEXO de la pagina para el preview web de Reunidas comunes.
    - Conserva todas las filas normalizadas y proyectadas del alcance Excel solicitado.
    - Mantiene sin cambios Proyecto Especial, calculos, agrupaciones y orden de exportacion.
    """
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
    cargos_queryset_reunida = None
    es_excel = request.GET.get("accion") == "excel"
    alcance_solicitado = request.GET.get("alcance")
    alcance_excel = (
        alcance_solicitado
        if alcance_solicitado in {"vista", "todos"}
        else "todos"
    )
    paginacion_preview = {}
    busqueda_sin_resultados = False
    filtros_avanzados_exportacion = _obtener_filtros_avanzados_exportacion(
        request
    )
    busquedas_columnas = _obtener_busquedas_columnas_exportacion(request)
    busquedas_columnas_efectivas = (
        _obtener_busquedas_columnas_exportacion_efectivas(
            busquedas_columnas,
            filtros_avanzados_exportacion,
        )
    )
    filtros_exportacion_activos = bool(
        busquedas_columnas_efectivas or filtros_avanzados_exportacion
    )
    busqueda_columna_id = next(
        iter(busquedas_columnas),
        COLUMNAS_BUSQUEDA_EXPORTACION[0]["id"],
    )
    busqueda_columna_valor = busquedas_columnas.get(busqueda_columna_id, "")

    if not tiene_contexto:
        mensaje_exportacion = "Debe seleccionar una Reunida valida por anio y nivel."
    else:
        try:
            reunida_obj = ReunidaPof.objects.get(anio=int(anio), nivel=nivel_codigo)
            nivel_nombre = NOMBRES_NIVEL.get(nivel_codigo, reunida_obj.get_nivel_display())
            cargos_queryset_reunida = _obtener_cargos_exportacion(reunida_obj)
            if es_excel:
                cargos_queryset_excel = cargos_queryset_reunida
                if alcance_excel == "vista":
                    cargos_queryset_excel = _aplicar_filtros_avanzados_exportacion(
                        cargos_queryset_excel,
                        filtros_avanzados_exportacion,
                    )
                    cargos_queryset_excel = _aplicar_busquedas_columnas_exportacion(
                        cargos_queryset_excel,
                        busquedas_columnas_efectivas,
                    )
                _filas_schema, filas_normalizadas_exportacion = _obtener_filas_reales_exportacion(
                    obtener_columnas_por_nivel(nivel_exportacion),
                    cargos_queryset_excel,
                    nivel_codigo=nivel_codigo,
                )
            else:
                cargos_queryset = _aplicar_filtros_avanzados_exportacion(
                    cargos_queryset_reunida,
                    filtros_avanzados_exportacion,
                )
                cargos_queryset = _aplicar_busquedas_columnas_exportacion(
                    cargos_queryset,
                    busquedas_columnas_efectivas,
                )
                unidades_pagina, page_obj = _paginar_unidades_preview_reunida(
                    cargos_queryset,
                    request,
                )
                cargos_pagina = _restringir_queryset_preview_reunida(
                    cargos_queryset,
                    unidades_pagina,
                )
                totales_generales = _obtener_totales_generales_preview_reunida(
                    cargos_queryset,
                    nivel_codigo,
                    unidades_pagina=unidades_pagina,
                )
                _filas_schema, filas_normalizadas_exportacion = _obtener_filas_reales_exportacion(
                    obtener_columnas_por_nivel(nivel_exportacion),
                    cargos_pagina,
                    nivel_codigo=nivel_codigo,
                    incluir_historial_cantidad=(
                        tiene_columna_modificacion_cantidad
                    ),
                    incluir_historial_observacion=True,
                    incluir_historial_estado=True,
                    totales_generales=totales_generales,
                )
                paginacion_preview = _construir_paginacion_preview_reunida(
                    page_obj,
                    request,
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
                if (
                    not es_excel
                    and filtros_exportacion_activos
                    and cargos_queryset_reunida is not None
                    and cargos_queryset_reunida.exists()
                ):
                    busqueda_sin_resultados = True
                    mensaje_exportacion = (
                        "No se encontraron resultados para los filtros aplicados."
                    )
                else:
                    mensaje_exportacion = (
                        "La Reunida existe, pero no tiene cargos cargados para exportar."
                    )
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
    secciones_exportacion_globales_preview = agrupar_filas_por_seccion(
        nivel_codigo=nivel_exportacion,
        columnas=columnas_preview,
        filas=filas_exportacion_globales,
        filas_normalizadas=filas_normalizadas_exportacion,
    )
    secciones_preview = _construir_secciones_preview(
        secciones_exportacion_globales_preview,
        columnas_disponibles_base,
        columnas_visibles_keys,
        separadores_filas_exportacion,
        filas_normalizadas_exportacion,
    )
    cabecera_querystring = f"anio={anio}&nivel={nivel_codigo}" if tiene_contexto else ""
    excel_querystring = (
        _armar_excel_querystring_reunida(
            anio,
            nivel_codigo,
            columnas_visibles_keys,
            request=request,
        )
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
        "columnas_exportacion_config": columnas_visibles,
        "schema_exportacion": obtener_schema_exportacion(nivel_exportacion),
        "columnas_disponibles": columnas_disponibles,
        "columnas_visibles_keys": columnas_visibles_keys,
        "columnas_default_keys": columnas_default_keys,
        "filas_exportacion": filas_exportacion,
        "filas_normalizadas_exportacion": filas_normalizadas_exportacion,
        "separadores_filas_exportacion": separadores_filas_exportacion,
        "secciones_exportacion": secciones_exportacion,
        "secciones_preview": secciones_preview,
        "columnas_busqueda": COLUMNAS_BUSQUEDA_EXPORTACION,
        "busquedas_columnas": busquedas_columnas,
        "busquedas_columnas_efectivas": busquedas_columnas_efectivas,
        "busqueda_columna_id": busqueda_columna_id,
        "busqueda_columna_valor": busqueda_columna_valor,
        "alcance_excel": alcance_excel,
        "filtros_excel": _descripcion_filtros_exportacion(
            busquedas=busquedas_columnas_efectivas,
            filtros_avanzados=filtros_avanzados_exportacion,
        ),
        "filtros_exportacion_activos": filtros_exportacion_activos,
        "filtros_avanzados_exportacion": filtros_avanzados_exportacion,
        "filtros_exportacion_campos": FILTROS_AVANZADOS_EXPORTACION_CAMPOS,
        "filtros_exportacion_opciones": _construir_opciones_filtros_exportacion(),
        "filtros_simple_exportacion_nombres": (),
        "busqueda_sin_resultados": busqueda_sin_resultados,
        "filas_preview_count": len(filas_exportacion_globales),
        "paginacion_preview": paginacion_preview,
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
