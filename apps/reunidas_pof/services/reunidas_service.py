from decimal import Decimal
from urllib.parse import urlencode

from django.core.paginator import Paginator
from django.db import DatabaseError, OperationalError, ProgrammingError
from django.db.models import Prefetch, Q
from django.utils import timezone
from .filtros_pof_service import (
    MENSAJE_FILTROS_INVALIDOS,
    validar_anio_filtro,
    validar_nivel_filtro,
)

from ..models import CargoPof, ProyectosEspecialesPof, ReunidaPof, SnapshotPadronLocalizacionPof
from .exportacion_rows import construir_filas_normalizadas
from .grilla_pof import construir_grilla_pof_desde_cargos, obtener_cargos_grilla_reunida
from .grilla_pof.detalle_politicas import obtener_politicas_detalle_reunida
from .grilla_pof.detalle_rows import (
    construir_grupos_operativos_detalle,
    serializar_grupo_operativo_detalle,
)
from .grilla_pof.proyecto_especial import (
    COLUMNAS_PROYECTO_ESPECIAL,
    armar_fila_proyecto_especial_cargo,
)
from .historial_service import (
    enriquecer_filas_con_historial_cantidad,
    enriquecer_filas_con_historial_estado,
    enriquecer_filas_con_historial_observacion,
)
from .filtros_pof_service import (
    MENSAJE_FILTROS_INVALIDOS,
    display_estado_pof,
    display_unidad_cantidad,
    validar_anexo_filtro,
    validar_ceic_filtro,
    validar_cue_filtro,
    validar_cueanexo_filtro,
    validar_cuof_filtro,
    validar_estado_pof_filtro,
    validar_unidad_cantidad_filtro,
)
from .niveles_service import limpiar_texto, normalizar_nivel, obtener_nombre_nivel
from .padron_materializadas_service import obtener_opciones_filtros_visualizacion_padron


PAGE_SIZE_OPTIONS = (10, 30, 50, 100)
CUES_POR_PAGINA_DETALLE = 25

FILTROS_DETALLE_REUNIDA = (
    "cueanexo",
    "cue_busqueda",
    "anexo",
    "cuof",
    "establecimiento",
    "localidad",
    "departamento",
    "region",
    "jornada",
    "categoria",
    "ambito",
    "ceic",
    "cargo",
    "estado_pof",
    "unidad_cantidad",
)

FILTROS_DETALLE_PROYECTO = (
    "cuof",
    "cueanexo",
    "cue_busqueda",
    "anexo",
    "cui",
    "establecimiento",
    "localidad",
    "departamento",
    "region",
    "jornada",
    "categoria",
    "ambito",
    "ceic",
    "cargo",
    "estado_pof",
    "unidad_cantidad",
)

FILTROS_CARGO_DETALLE_REUNIDA = (
    "ceic",
    "cargo",
    "estado_pof",
    "unidad_cantidad",
)

FILTROS_SNAPSHOT_DETALLE_REUNIDA = {
    "localidad": "localidad",
    "departamento": "departamento",
    "region": "region",
    "jornada": "jornada",
    "categoria": "categoria",
    "ambito": "ambito",
}

SNAPSHOT_COLUMNAS_DETALLE_REUNIDA = {
    "numero_establecimiento": "numero_establecimiento",
    "nombre_establecimiento": "nombre_establecimiento",
    "region": "region",
    "localidad": "localidad",
    "departamento": "departamento",
    "ambito": "ambito",
    "categoria": "categoria",
    "jornada": "jornada",
    "oferta": "oferta",
    "acronimo": "acronimo",
    "estado_localizacion_padron": "estado_localizacion_padron",
    "estado_oferta_padron": "estado_oferta_padron",
    "estado_establecimiento_padron": "estado_establecimiento_padron",
}

OPERADORES_FILTRO_DETALLE = {
    "0": "parecido a",
    "1": "no parecido a",
    "2": "igual a",
    "3": "mayor a",
    "4": "mayor o igual a",
    "5": "menor a",
    "6": "menor o igual a",
    "7": "distinto de",
}
OPERADORES_TEXTO_DETALLE = ("0", "1", "2", "7")
OPERADORES_EXACTOS_DETALLE = ("2", "7")
OPERADORES_NUMERICOS_DETALLE = ("2", "7", "3", "4", "5", "6")

COLUMNAS_BUSQUEDA_DETALLE_REUNIDA = (
    {"id": "cue", "label": "CUE"},
    {"id": "anexo", "label": "Anexo"},
    {"id": "cui", "label": "CUI"},
    {"id": "cuof", "label": "CUOF"},
    {"id": "cargo", "label": "Cargo"},
    {"id": "nombre_establecimiento", "label": "Establecimiento"},
)
COLUMNAS_BUSQUEDA_DETALLE_IDS = tuple(
    columna["id"] for columna in COLUMNAS_BUSQUEDA_DETALLE_REUNIDA
)
COLUMNAS_BUSQUEDA_DETALLE_LABELS = {
    columna["id"]: columna["label"] for columna in COLUMNAS_BUSQUEDA_DETALLE_REUNIDA
}

FILTROS_AVANZADOS_DETALLE_CAMPOS = [
    {"id": "cueanexo", "label": "CUEANEXO", "tipo": "text", "operadores": "text"},
    {"id": "cue", "label": "CUE", "tipo": "text", "operadores": "text"},
    {"id": "anexo", "label": "Anexo", "tipo": "text", "operadores": "text"},
    {"id": "cuof", "label": "CUOF", "tipo": "text", "operadores": "text"},
    {"id": "cui", "label": "CUI", "tipo": "text", "operadores": "text"},
    {"id": "nombre_establecimiento", "label": "Establecimiento", "tipo": "text", "operadores": "text"},
    {"id": "numero_establecimiento", "label": "Número establecimiento", "tipo": "text", "operadores": "text"},
    {"id": "region", "label": "Región", "tipo": "checklist", "operadores": "exact"},
    {"id": "localidad", "label": "Localidad", "tipo": "checklist", "operadores": "exact"},
    {"id": "departamento", "label": "Departamento", "tipo": "checklist", "operadores": "exact"},
    {"id": "ambito", "label": "Ámbito", "tipo": "checklist", "operadores": "exact"},
    {"id": "categoria", "label": "Categoría", "tipo": "checklist", "operadores": "exact"},
    {"id": "jornada", "label": "Jornada", "tipo": "checklist", "operadores": "exact"},
    {"id": "oferta", "label": "Oferta", "tipo": "checklist", "operadores": "exact"},
    {"id": "acronimo", "label": "Acrónimo", "tipo": "checklist", "operadores": "exact"},
    {"id": "estado_localizacion_padron", "label": "Estado localización", "tipo": "checklist", "operadores": "exact"},
    {"id": "estado_oferta_padron", "label": "Estado oferta", "tipo": "checklist", "operadores": "exact"},
    {"id": "estado_establecimiento_padron", "label": "Estado establecimiento", "tipo": "checklist", "operadores": "exact"},
    {"id": "ceic", "label": "CEIC", "tipo": "number", "operadores": "numeric"},
    {"id": "cargo", "label": "Cargo", "tipo": "text", "operadores": "text"},
    {"id": "cantidad", "label": "Cantidad", "tipo": "number", "operadores": "numeric"},
    {"id": "unidad_cantidad", "label": "Unidad", "tipo": "checklist", "operadores": "exact"},
    {"id": "puntos_asignados", "label": "Puntos", "tipo": "number", "operadores": "numeric"},
    {"id": "total", "label": "Total", "tipo": "number", "operadores": "numeric"},
    {"id": "estado_pof", "label": "Estado POF", "tipo": "checklist", "operadores": "exact"},
]
FILTROS_AVANZADOS_DETALLE_POR_ID = {
    filtro["id"]: filtro for filtro in FILTROS_AVANZADOS_DETALLE_CAMPOS
}
FILTROS_AVANZADOS_DETALLE_LABELS = {
    filtro["id"]: filtro["label"] for filtro in FILTROS_AVANZADOS_DETALLE_CAMPOS
}
FILTROS_AVANZADOS_LOCALIZACION_DETALLE = {
    "cueanexo": "localizacion__cueanexo",
    "cuof": "localizacion__cuof",
    "cui": "localizacion__cui",
}
FILTROS_AVANZADOS_CARGO_TEXTO_DETALLE = {
    "cargo": "cargo",
}
FILTROS_AVANZADOS_NUMERICOS_DETALLE = {
    "ceic": "ceic",
    "cantidad": "cantidad",
    "puntos_asignados": "puntos_asignados",
    "total": "total",
}


def serializar_reunida(reunida):
    return {
        "id": reunida.id,
        "anio": reunida.anio,
        "nivel_codigo": reunida.nivel,
        "nivel_nombre": reunida.get_nivel_display(),
        "actualizado_en": reunida.actualizado_en,
    }


def obtener_reunidas_demo(anio_actual):
    return [
        {
            "anio": anio_actual,
            "nivel": "Primaria",
            "nivel_codigo": "PRIMARIA",
            "estado": "Abierta",
            "localizaciones": 0,
            "cargos": 0,
            "total": "0.00",
        },
        {
            "anio": anio_actual,
            "nivel": "Educación Física",
            "nivel_codigo": "FISICA",
            "estado": "Abierta",
            "localizaciones": 0,
            "cargos": 0,
            "total": "0.00",
        },
        {
            "anio": anio_actual - 1,
            "nivel": "Educación Física",
            "nivel_codigo": "FISICA",
            "estado": "Cerrada",
            "localizaciones": 0,
            "cargos": 0,
            "total": "0.00",
        },
    ]

def _obtener_filtros_reunidas_con_errores(request):
    filtros = {
        "anio": "",
        "nivel": "",
    }
    errores = {}

    anio, error = validar_anio_filtro(request.GET.get("anio", ""))
    filtros["anio"] = anio
    if error:
        errores["anio"] = error

    nivel, error = validar_nivel_filtro(request.GET.get("nivel", ""), permitir_todos=False)
    filtros["nivel"] = nivel
    if error:
        errores["nivel"] = error

    return filtros, errores


def construir_contexto_reunidas(request):
    anio_actual = timezone.localdate().year
    filtros, errores_filtros = _obtener_filtros_reunidas_con_errores(request)
    filtro_anio = filtros["anio"]
    filtro_nivel = filtros["nivel"]
    page_size_parametro = request.GET.get("page_size", "")

    try:
        page_size = int(page_size_parametro)
    except (TypeError, ValueError):
        page_size = 10

    if page_size not in PAGE_SIZE_OPTIONS:
        page_size = 10

    reunidas = ReunidaPof.objects.all()

    if errores_filtros:
        reunidas = reunidas.none()
    else:
        if filtro_anio:
            reunidas = reunidas.filter(anio=int(filtro_anio))

        if filtro_nivel:
            reunidas = reunidas.filter(nivel=filtro_nivel)

    reunidas = reunidas.order_by("-anio", "nivel")

    try:
        paginator = Paginator(reunidas, page_size)
        page_obj = paginator.get_page(request.GET.get("page"))
        total_registros = paginator.count
        showing_start = page_obj.start_index() if total_registros else 0
        showing_end = page_obj.end_index() if total_registros else 0
        reunidas_pagina = [serializar_reunida(reunida) for reunida in page_obj.object_list]
        tabla_reunidas_no_migrada = False
    except (ProgrammingError, OperationalError):
        paginator = Paginator([], page_size)
        page_obj = paginator.get_page(1)
        reunidas_pagina = []
        total_registros = 0
        showing_start = 0
        showing_end = 0
        tabla_reunidas_no_migrada = True

    query_params = request.GET.copy()
    query_params.pop("page", None)
    query_params["page_size"] = str(page_size)

    if filtro_anio:
        query_params["anio"] = filtro_anio
    else:
        query_params.pop("anio", None)

    if filtro_nivel:
        query_params["nivel"] = filtro_nivel
    else:
        query_params.pop("nivel", None)

    return {
        "anio_actual": anio_actual,
        "page_obj": page_obj,
        "paginator": paginator,
        "reunidas": reunidas_pagina,
        "total_registros": total_registros,
        "showing_start": showing_start,
        "showing_end": showing_end,
        "page_size": page_size,
        "page_size_options": PAGE_SIZE_OPTIONS,
        "filtro_anio": filtro_anio,
        "filtro_nivel": filtro_nivel,
        "niveles": ReunidaPof.Nivel.choices,
        "query_params_base": query_params.urlencode(),
        "page_range": list(paginator.get_elided_page_range(number=page_obj.number)),
        "tabla_reunidas_no_migrada": tabla_reunidas_no_migrada,
        "filtros": filtros,
        "errores_filtros": errores_filtros,
        "mensaje_filtros": MENSAJE_FILTROS_INVALIDOS if errores_filtros else ""
    }


def obtener_grupos_cue_demo():
    return [
        {
            "cuof": "1269",
            "cue_base": "2200242",
            "cui": "992201476",
            "establecimiento_base": "E.E.P. N° 123",
            "total": "8.936,00",
            "anexos": [
                {
                    "sub_cue": "220024200",
                    "cueanexo": "220024200",
                    "anexo": "00",
                    "cui": "992201476",
                    "establecimiento": "E.E.P. N° 123",
                    "oferta": "Primaria común",
                    "localidad": "Resistencia",
                    "total": "6.186,00",
                    "cargos": [
                        {
                            "ceic": "206",
                            "cargo": "Director de 1ra. categoría",
                            "cantidad": "1",
                            "unidad": "Cargo",
                            "puntos": "3.436,00",
                            "total": "3.436,00",
                            "estado": "Afectado",
                        },
                        {
                            "ceic": "111",
                            "cargo": "Horas Cátedra",
                            "cantidad": "25",
                            "unidad": "Hora cátedra",
                            "puntos": "110,00",
                            "total": "2.750,00",
                            "estado": "Afectado",
                        },
                    ],
                },
                {
                    "sub_cue": "220024201",
                    "cueanexo": "220024201",
                    "anexo": "01",
                    "cui": "992201476",
                    "establecimiento": "E.E.P. N° 123 - Anexo",
                    "oferta": "Primaria común",
                    "localidad": "Barranqueras",
                    "total": "2.750,00",
                    "cargos": [
                        {
                            "ceic": "111",
                            "cargo": "Horas Cátedra",
                            "cantidad": "25",
                            "unidad": "Hora cátedra",
                            "puntos": "110,00",
                            "total": "2.750,00",
                            "estado": "Afectado",
                        },
                    ],
                },
            ],
        },
        {
            "cuof": "1270",
            "cue_base": "2200100",
            "cui": "992201368",
            "establecimiento_base": "E.E.P. N° 456",
            "total": "1.880,00",
            "anexos": [
                {
                    "sub_cue": "220010000",
                    "cueanexo": "220010000",
                    "anexo": "00",
                    "cui": "992201368",
                    "establecimiento": "E.E.P. N° 456",
                    "oferta": "Primaria común",
                    "localidad": "Fontana",
                    "total": "1.880,00",
                    "cargos": [
                        {
                            "ceic": "115",
                            "cargo": "Maestro de grado",
                            "cantidad": "1",
                            "unidad": "Cargo",
                            "puntos": "1.880,00",
                            "total": "1.880,00",
                            "estado": "Afectado",
                        },
                    ],
                },
            ],
        },
    ]


def _valor_o_guion(valor):
    return valor if valor not in (None, "") else "—"


def _formatear_decimal(valor, decimales=2):
    if valor is None:
        valor = 0

    formato = f"{{:,.{decimales}f}}"
    return formato.format(valor).replace(",", "X").replace(".", ",").replace("X", ".")


def _formatear_cantidad(valor):
    if valor is None:
        return "0"

    if valor == valor.to_integral_value():
        return str(int(valor))

    return _formatear_decimal(valor)


def _obtener_snapshot_vigente(localizacion):
    snapshots = getattr(localizacion, "snapshots_vigentes", [])
    return snapshots[0] if snapshots else None


def _obtener_establecimiento(snapshot):
    if not snapshot:
        return "—"

    return _valor_o_guion(snapshot.nombre_establecimiento or snapshot.numero_establecimiento)


def _serializar_cargo_detalle(cargo):
    return {
        "ceic": cargo.ceic,
        "cargo": _valor_o_guion(cargo.cargo),
        "cantidad": _formatear_cantidad(cargo.cantidad),
        "unidad": cargo.get_unidad_cantidad_display(),
        "puntos": _formatear_decimal(cargo.puntos_asignados),
        "total": _formatear_decimal(cargo.total),
        "estado": cargo.get_estado_pof_display(),
        "estado_clase": cargo.estado_pof.lower(),
    }


def _crear_anexo_desde_localizacion(localizacion, snapshot):
    cueanexo = localizacion.cueanexo or ""

    return {
        "cueanexo": cueanexo,
        "sub_cue": cueanexo or "—",
        "anexo": localizacion.anexo_localizacion or "—",
        "cui": _valor_o_guion(localizacion.cui),
        "establecimiento": _obtener_establecimiento(snapshot),
        "oferta": _valor_o_guion(snapshot.oferta if snapshot else ""),
        "localidad": _valor_o_guion(snapshot.localidad if snapshot else ""),
        "departamento": _valor_o_guion(snapshot.departamento if snapshot else ""),
        "region": _valor_o_guion(snapshot.region if snapshot else ""),
        "ubicacion": _valor_o_guion(snapshot.ubicacion if snapshot else ""),
        "total_valor": 0,
        "total": _formatear_decimal(0),
        "cargos": [],
    }


def _obtener_cargos_detalle_queryset():
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


def _obtener_cargos_detalle_reunida(reunida):
    return obtener_cargos_grilla_reunida(reunida=reunida)


def _normalizar_texto_filtro_detalle(valor, max_length=50):
    """
    Normaliza texto libre recibido por GET para filtros del Detalle.

    - Aplica strip y colapsa espacios internos repetidos.
    - Acota la longitud antes de devolver el valor al template.
    - No altera reglas especificas como CUOF, CUE, Anexo o CEIC.
    """
    texto = limpiar_texto(valor, max_length)
    return " ".join(texto.split())


def _obtener_filtros_detalle_reunida(request):
    """
    Normaliza los filtros GET propios del Detalle operativo de Reunida.

    - Mantiene separados filtros de localizacion y filtros internos de cargo.
    - Acota cadenas antes de aplicarlas sobre QuerySets.
    - Devuelve cadenas acotadas para reutilizarlas en QuerySets y en el template.
    """
    return {
        "cueanexo": _normalizar_texto_filtro_detalle(request.GET.get("cueanexo", ""), 20),
        "cue_busqueda": _normalizar_texto_filtro_detalle(request.GET.get("cue_busqueda", ""), 20),
        "anexo": _normalizar_texto_filtro_detalle(request.GET.get("anexo", ""), 10),
        "cuof": _normalizar_texto_filtro_detalle(request.GET.get("cuof", ""), 80),
        "cui": _normalizar_texto_filtro_detalle(request.GET.get("cui", ""), 100),
        "establecimiento": _normalizar_texto_filtro_detalle(request.GET.get("establecimiento", ""), 100),
        "localidad": _normalizar_texto_filtro_detalle(request.GET.get("localidad", ""), 100),
        "departamento": _normalizar_texto_filtro_detalle(request.GET.get("departamento", ""), 100),
        "region": _normalizar_texto_filtro_detalle(request.GET.get("region", ""), 50),
        "jornada": _normalizar_texto_filtro_detalle(request.GET.get("jornada", ""), 100),
        "categoria": _normalizar_texto_filtro_detalle(request.GET.get("categoria", ""), 100),
        "ambito": _normalizar_texto_filtro_detalle(request.GET.get("ambito", ""), 50),
        "ceic": _normalizar_texto_filtro_detalle(request.GET.get("ceic", ""), 20),
        "cargo": _normalizar_texto_filtro_detalle(request.GET.get("cargo", ""), 100),
        "estado_pof": _normalizar_texto_filtro_detalle(request.GET.get("estado_pof", ""), 20).upper(),
        "unidad_cantidad": _normalizar_texto_filtro_detalle(request.GET.get("unidad_cantidad", ""), 20).upper(),
    }


def _choices_options_detalle(choices):
    return [
        {"value": str(codigo), "label": str(etiqueta)}
        for codigo, etiqueta in choices
        if str(codigo)
    ]


def _construir_opciones_filtros_detalle_reunida():
    opciones = {campo["id"]: [] for campo in FILTROS_AVANZADOS_DETALLE_CAMPOS}
    opciones.update({
        "unidad_cantidad": _choices_options_detalle(CargoPof.UnidadCantidad.choices),
        "estado_pof": _choices_options_detalle(CargoPof.EstadoPof.choices),
    })

    try:
        opciones_padron = obtener_opciones_filtros_visualizacion_padron()
    except (DatabaseError, ProgrammingError, OperationalError):
        opciones_padron = {}

    for campo_id in opciones:
        if campo_id in opciones_padron:
            opciones[campo_id] = opciones_padron[campo_id]

    return opciones


def _obtener_busquedas_columna_detalle_reunida(request):
    busquedas = {}
    for columna_id in COLUMNAS_BUSQUEDA_DETALLE_IDS:
        valor = _normalizar_texto_filtro_detalle(
            request.GET.get(f"col_{columna_id}", ""),
            180,
        )
        if valor:
            busquedas[columna_id] = valor
    return busquedas


def _obtener_busqueda_columna_activa_detalle_reunida(busquedas_columna):
    for columna_id in COLUMNAS_BUSQUEDA_DETALLE_IDS:
        valor = busquedas_columna.get(columna_id, "")
        if valor:
            return columna_id, valor
    return "cue", ""


def _operadores_validos_para_campo_detalle(campo_id):
    definicion = FILTROS_AVANZADOS_DETALLE_POR_ID.get(campo_id)
    if not definicion:
        return ()
    if definicion["operadores"] == "exact":
        return OPERADORES_EXACTOS_DETALLE
    if definicion["operadores"] == "numeric":
        return OPERADORES_NUMERICOS_DETALLE
    return OPERADORES_TEXTO_DETALLE


def _obtener_filtros_avanzados_detalle_reunida(request):
    filtros = []
    campos = request.GET.getlist("campo_filtro")
    operadores = request.GET.getlist("operador_filtro")
    valores = request.GET.getlist("valor_filtro")

    for indice, campo_id in enumerate(campos):
        campo_id = _normalizar_texto_filtro_detalle(campo_id, 80)
        valor = _normalizar_texto_filtro_detalle(
            valores[indice] if indice < len(valores) else "",
            240,
        )
        operador = _normalizar_texto_filtro_detalle(
            operadores[indice] if indice < len(operadores) else "0",
            4,
        )

        if not campo_id or not valor or campo_id not in FILTROS_AVANZADOS_DETALLE_POR_ID:
            continue
        if operador not in _operadores_validos_para_campo_detalle(campo_id):
            continue

        filtros.append({
            "indice": indice,
            "campo": campo_id,
            "operador": operador,
            "valor": valor,
        })

    return filtros


def _hay_filtros_detalle_reunida(filtros, nombres_filtros=FILTROS_DETALLE_REUNIDA):
    """
    Indica si el Detalle común recibió al menos un filtro operativo.

    - Se usa solo para mostrar estado visual y mensajes suaves.
    - No altera la carga normal sin filtros.
    - Ignora parámetros base de cabecera como año y nivel.
    """
    return any(filtros.get(nombre) for nombre in nombres_filtros)


def _hay_filtros_cargo_detalle_reunida(filtros):
    """
    Detecta si el Detalle debe entrar en modo de cargos coincidentes.

    - Considera solo filtros internos de CargoPof.
    - Permite mantener el modo normal con AJAX cuando no hay filtros de cargo.
    - No depende de filtros de localizacion ya aplicados al alcance base.
    """
    return any(filtros.get(nombre) for nombre in FILTROS_CARGO_DETALLE_REUNIDA)


def _construir_querystrings_quitar_filtros_detalle_base(
    filtros,
    base_params,
    nombres_filtros=FILTROS_DETALLE_REUNIDA,
):
    querystrings = {}
    for filtro_a_quitar in nombres_filtros:
        if not filtros.get(filtro_a_quitar):
            continue

        params = dict(base_params)
        for nombre_filtro in nombres_filtros:
            if nombre_filtro == filtro_a_quitar:
                continue
            valor = filtros.get(nombre_filtro)
            if valor:
                params[nombre_filtro] = valor

        querystrings[filtro_a_quitar] = urlencode(params)

    return querystrings


def _construir_querystring_detalle_con_filtros(
    filtros,
    base_params,
    nombres_filtros=FILTROS_DETALLE_REUNIDA,
):
    params = dict(base_params)
    for nombre_filtro in nombres_filtros:
        valor = filtros.get(nombre_filtro)
        if valor:
            params[nombre_filtro] = valor
    return urlencode(params)


def _construir_querystrings_quitar_filtros_detalle(filtros, anio, nivel_codigo):
    """
    Construye URLs parciales para quitar un unico filtro activo del Detalle comun.

    - Conserva cabecera_tipo, anio y nivel de la Reunida actual.
    - Mantiene los demas filtros activos sin recalcular resultados.
    - Omite claves vacias para no marcar selects por sus opciones por defecto.
    """
    return _construir_querystrings_quitar_filtros_detalle_base(
        filtros,
        {
            "cabecera_tipo": "REUNIDA",
            "anio": anio,
            "nivel": nivel_codigo,
        },
    )


def _construir_chips_filtros_detalle(
    filtros,
    querystrings,
    errores=None,
    nombres_filtros=FILTROS_DETALLE_REUNIDA,
):
    """
    Construye chips removibles para filtros activos del Detalle.

    - Usa etiquetas legibles y displays reales para choices de CargoPof.
    - Omite filtros inválidos porque no fueron aplicados al resultado.
    - Reutiliza los querystrings que conservan cabecera_tipo, año y nivel.
    """
    errores = errores or {}
    definiciones = (
        ("cueanexo", "CUEANEXO", filtros.get("cueanexo")),
        ("cue_busqueda", "CUE", filtros.get("cue_busqueda")),
        ("anexo", "Anexo", filtros.get("anexo")),
        ("cuof", "CUOF", filtros.get("cuof")),
        ("cui", "CUI", filtros.get("cui")),
        ("establecimiento", "Establecimiento", filtros.get("establecimiento")),
        ("localidad", "Localidad", filtros.get("localidad")),
        ("departamento", "Departamento", filtros.get("departamento")),
        ("region", "Región", filtros.get("region")),
        ("jornada", "Jornada", filtros.get("jornada")),
        ("categoria", "Categoría", filtros.get("categoria")),
        ("ambito", "Ámbito", filtros.get("ambito")),
        ("ceic", "CEIC", filtros.get("ceic")),
        ("cargo", "Cargo", filtros.get("cargo")),
        ("estado_pof", "Estado POF", display_estado_pof(filtros.get("estado_pof"))),
        ("unidad_cantidad", "Unidad", display_unidad_cantidad(filtros.get("unidad_cantidad"))),
    )
    chips = []
    nombres_filtros = set(nombres_filtros)
    for clave, etiqueta, valor in definiciones:
        if clave in nombres_filtros and valor and clave not in errores:
            chips.append({
                "clave": clave,
                "etiqueta": etiqueta,
                "valor": valor,
                "querystring": querystrings.get(clave, ""),
            })
    return chips


def _valor_filtro_avanzado_detalle_label(campo_id, valor):
    choices = ()
    if campo_id == "estado_pof":
        choices = CargoPof.EstadoPof.choices
    elif campo_id == "unidad_cantidad":
        choices = CargoPof.UnidadCantidad.choices

    for codigo, etiqueta in choices:
        if str(codigo) == str(valor):
            return str(etiqueta)
    return valor


def _construir_chips_detalle_dinamicos(
    filtros_simples_chips,
    filtros_avanzados,
    busquedas_columna,
):
    chips = []

    for chip in filtros_simples_chips:
        texto = f"{chip['etiqueta']}: {chip['valor']}"
        chips.append({
            "tipo": "simple",
            "campo": chip["clave"],
            "indice": "",
            "texto": texto,
        })

    for filtro in filtros_avanzados:
        campo_id = filtro["campo"]
        etiqueta = FILTROS_AVANZADOS_DETALLE_LABELS.get(campo_id, campo_id)
        operador = OPERADORES_FILTRO_DETALLE.get(filtro["operador"], OPERADORES_FILTRO_DETALLE["0"])
        valor = _valor_filtro_avanzado_detalle_label(campo_id, filtro["valor"])
        chips.append({
            "tipo": "avanzado",
            "campo": campo_id,
            "indice": filtro["indice"],
            "texto": f"{etiqueta} {operador}: {valor}",
        })

    for columna_id, valor in busquedas_columna.items():
        etiqueta = COLUMNAS_BUSQUEDA_DETALLE_LABELS.get(columna_id, columna_id)
        chips.append({
            "tipo": "columna",
            "campo": columna_id,
            "indice": "",
            "texto": f"Columna {etiqueta} {OPERADORES_FILTRO_DETALLE['0']}: {valor}",
        })

    return chips


def _normalizar_pagina_detalle(valor_pagina):
    """
    Normaliza el parametro `page` para la paginacion de CUEs del Detalle.

    - Los valores vacios, no numericos o menores a 1 vuelven a la pagina 1.
    - Las paginas mayores al total se resuelven luego con `Paginator.get_page`.
    - No modifica filtros ni otros parametros del request.
    """
    try:
        pagina = int(valor_pagina)
    except (TypeError, ValueError):
        return 1

    if pagina < 1:
        return 1
    return pagina


def _construir_query_params_paginacion_detalle(request):
    """
    Construye la base de querystring para paginar CUEs del Detalle comun.

    - Conserva filtros y parametros de contexto vigentes.
    - Quita solo `page` para que cada link reemplace la pagina actual.
    - Mantiene deep-links por cueanexo/cuof cuando ya vienen en la URL.
    """
    query_params = request.GET.copy()
    query_params.pop("page", None)
    return query_params.urlencode()


def _obtener_page_range_detalle(paginator, page_obj):
    """
    Devuelve un rango compacto de paginas para grupos CUE del Detalle.

    - Usa rangos elididos para evitar cientos de links.
    - Mantiene paginas cercanas a la actual y extremos.
    - Devuelve una lista segura para iterar desde el template.
    """
    return list(
        paginator.get_elided_page_range(
            number=page_obj.number,
            on_each_side=2,
            on_ends=1,
        )
    )


def _paginar_grupos_cue_detalle(grupos_cue, valor_pagina):
    """
    Pagina grupos CUE ya armados para el Detalle de Reunida comun.

    - Pagina CUEs completos, no cargos ni grupos Anexo/CUOF internos.
    - Mantiene intactos totales, filas y estructuras publicas de cada grupo.
    - Devuelve contadores para mostrar el rango visible sin recalcular datos.
    """
    paginator = Paginator(grupos_cue, CUES_POR_PAGINA_DETALLE)
    page_obj = paginator.get_page(_normalizar_pagina_detalle(valor_pagina))
    total = paginator.count

    return {
        "page_obj": page_obj,
        "paginator": paginator,
        "grupos": list(page_obj.object_list),
        "total": total,
        "showing_start": page_obj.start_index() if total else 0,
        "showing_end": page_obj.end_index() if total else 0,
        "page_size": CUES_POR_PAGINA_DETALLE,
        "page_range": _obtener_page_range_detalle(paginator, page_obj),
    }


def _aplicar_filtros_detalle_reunida(queryset, filtros, incluir_cui=False):
    """
    Aplica filtros de grupo/localización antes de construir la grilla del Detalle.

    - Filtra CUE de 7 digitos y CUOF directamente sobre LocalizacionPof.
    - Filtra datos descriptivos sobre el snapshot vigente asociado.
    - Usa `distinct()` cuando entra por snapshots para evitar duplicados.
    """
    mensajes = []
    errores = {}
    cueanexo = filtros.get("cueanexo", "")
    cue_busqueda = filtros.get("cue_busqueda", "")
    anexo = filtros.get("anexo", "")
    cuof = filtros.get("cuof", "")
    cui = filtros.get("cui", "")

    if cueanexo:
        cueanexo, error = validar_cueanexo_filtro(cueanexo)
        if error:
            mensajes.append(error)
            errores["cueanexo"] = error
            queryset = queryset.none()
        else:
            queryset = queryset.filter(localizacion__cueanexo=cueanexo)

    if cue_busqueda:
        cue_busqueda, error = validar_cue_filtro(cue_busqueda)
        if error:
            mensajes.append(error)
            errores["cue_busqueda"] = error
            queryset = queryset.none()
        else:
            queryset = queryset.filter(localizacion__cueanexo__startswith=cue_busqueda)

    if anexo:
        anexo, error = validar_anexo_filtro(anexo)
        if error:
            mensajes.append(error)
            errores["anexo"] = error
            queryset = queryset.none()
        else:
            queryset = queryset.filter(localizacion__cueanexo__endswith=anexo)

    if cuof:
        cuof, error = validar_cuof_filtro(cuof)
        if error:
            mensajes.append(error)
            errores["cuof"] = error
            queryset = queryset.none()
        else:
            queryset = queryset.filter(localizacion__cuof__iexact=cuof)

    if incluir_cui and cui:
        queryset = queryset.filter(localizacion__cui__icontains=cui)

    snapshot_q = Q()
    if filtros.get("establecimiento"):
        establecimiento = filtros["establecimiento"]
        snapshot_q &= (
            Q(localizacion__snapshots_padron__nombre_establecimiento__icontains=establecimiento)
            | Q(localizacion__snapshots_padron__numero_establecimiento__icontains=establecimiento)
        )

    for nombre_filtro, campo_snapshot in FILTROS_SNAPSHOT_DETALLE_REUNIDA.items():
        valor = filtros.get(nombre_filtro)
        if valor:
            snapshot_q &= Q(**{f"localizacion__snapshots_padron__{campo_snapshot}__icontains": valor})

    if snapshot_q:
        queryset = queryset.filter(
            snapshot_q,
            localizacion__snapshots_padron__vigente=True,
        ).distinct()

    return queryset, " ".join(mensajes), errores


def _snapshot_filter_q_detalle(campo, valor, exacto=False):
    lookup = "iexact" if exacto else "icontains"
    return Q(
        localizacion__snapshots_padron__vigente=True,
        **{f"localizacion__snapshots_padron__{campo}__{lookup}": valor},
    )


def _texto_lookup_q_detalle(campo, operador, valor):
    lookup = "icontains" if operador in {"0", "1"} else "iexact"
    return Q(**{f"{campo}__{lookup}": valor})


def _snapshot_lookup_q_detalle(campo, operador, valor):
    lookup = "icontains" if operador in {"0", "1"} else "iexact"
    return Q(
        localizacion__snapshots_padron__vigente=True,
        **{f"localizacion__snapshots_padron__{campo}__{lookup}": valor},
    )


def _cue_lookup_q_detalle(operador, valor):
    if operador in {"2", "7"}:
        return Q(localizacion__cueanexo__startswith=valor)
    return Q(localizacion__cueanexo__icontains=valor)


def _anexo_lookup_q_detalle(operador, valor):
    if operador in {"2", "7"}:
        return Q(localizacion__cueanexo__endswith=valor)
    return Q(localizacion__cueanexo__icontains=valor)


def _decimal_valor_detalle(valor):
    try:
        return Decimal(str(valor).replace(",", "."))
    except Exception:
        return None


def _numero_lookup_q_detalle(campo, operador, valor):
    numero = _decimal_valor_detalle(valor)
    if numero is None:
        return None

    if campo == "ceic":
        if numero != numero.to_integral_value():
            return None
        numero = int(numero)

    lookup_por_operador = {
        "2": "exact",
        "7": "exact",
        "3": "gt",
        "4": "gte",
        "5": "lt",
        "6": "lte",
    }
    lookup = lookup_por_operador.get(operador)
    if not lookup:
        return None
    return Q(**{f"{campo}__{lookup}": numero})


def _filtro_avanzado_detalle_q(campo_id, operador, valor):
    if campo_id == "cue":
        return _cue_lookup_q_detalle(operador, valor)
    if campo_id == "anexo":
        return _anexo_lookup_q_detalle(operador, valor)
    if campo_id in FILTROS_AVANZADOS_LOCALIZACION_DETALLE:
        return _texto_lookup_q_detalle(
            FILTROS_AVANZADOS_LOCALIZACION_DETALLE[campo_id],
            operador,
            valor,
        )
    if campo_id in SNAPSHOT_COLUMNAS_DETALLE_REUNIDA:
        return _snapshot_lookup_q_detalle(
            SNAPSHOT_COLUMNAS_DETALLE_REUNIDA[campo_id],
            operador,
            valor,
        )
    if campo_id in FILTROS_AVANZADOS_CARGO_TEXTO_DETALLE:
        return _texto_lookup_q_detalle(
            FILTROS_AVANZADOS_CARGO_TEXTO_DETALLE[campo_id],
            operador,
            valor,
        )
    if campo_id in FILTROS_AVANZADOS_NUMERICOS_DETALLE:
        return _numero_lookup_q_detalle(
            FILTROS_AVANZADOS_NUMERICOS_DETALLE[campo_id],
            operador,
            valor,
        )
    if campo_id == "estado_pof":
        return Q(estado_pof=valor)
    if campo_id == "unidad_cantidad":
        return Q(unidad_cantidad=valor)
    return None


def _aplicar_filtro_detalle_q(queryset, filtro_q, operador):
    if filtro_q is None:
        return queryset
    if operador in {"1", "7"}:
        return queryset.exclude(filtro_q)
    return queryset.filter(filtro_q)


def _aplicar_filtros_avanzados_detalle_reunida(queryset, filtros_avanzados):
    grupos = {}
    filtros_sueltos = []

    for filtro in filtros_avanzados:
        if filtro["operador"] in {"0", "2"}:
            grupos.setdefault((filtro["campo"], filtro["operador"]), []).append(filtro["valor"])
        else:
            filtros_sueltos.append(filtro)

    for (campo_id, operador), valores in grupos.items():
        filtro_grupo = Q()
        for valor in valores:
            filtro_q = _filtro_avanzado_detalle_q(campo_id, operador, valor)
            if filtro_q is not None:
                filtro_grupo |= filtro_q
        if filtro_grupo:
            queryset = queryset.filter(filtro_grupo)

    for filtro in filtros_sueltos:
        filtro_q = _filtro_avanzado_detalle_q(
            filtro["campo"],
            filtro["operador"],
            filtro["valor"],
        )
        queryset = _aplicar_filtro_detalle_q(queryset, filtro_q, filtro["operador"])

    return queryset.distinct() if filtros_avanzados else queryset


def _aplicar_busqueda_columna_detalle_reunida(queryset, columna_id, valor):
    if columna_id == "cue":
        return queryset.filter(localizacion__cueanexo__startswith=valor)
    if columna_id == "anexo":
        return queryset.filter(localizacion__cueanexo__endswith=valor)
    if columna_id == "cui":
        return queryset.filter(localizacion__cui__icontains=valor)
    if columna_id == "cuof":
        return queryset.filter(localizacion__cuof__icontains=valor)
    if columna_id == "cargo":
        return queryset.filter(cargo__icontains=valor)
    if columna_id == "nombre_establecimiento":
        return queryset.filter(_snapshot_filter_q_detalle("nombre_establecimiento", valor)).distinct()
    return queryset


def _aplicar_busquedas_columna_detalle_reunida(queryset, busquedas_columna):
    for columna_id, valor in busquedas_columna.items():
        queryset = _aplicar_busqueda_columna_detalle_reunida(queryset, columna_id, valor)
    return queryset.distinct() if busquedas_columna else queryset


def _aplicar_filtros_cargo_detalle_reunida(queryset, filtros):
    """
    Aplica filtros internos de cargo sobre el alcance base del Detalle.

    - Filtra CEIC exacto, cargo parcial, estado POF y unidad por QuerySet.
    - Valida contra choices reales del modelo para evitar valores inventados.
    - Devuelve mensajes suaves sin lanzar excepciones por GET invalido.
    """
    mensajes = []
    errores = {}
    ceic = filtros.get("ceic", "")
    cargo = filtros.get("cargo", "")
    estado_pof = filtros.get("estado_pof", "")
    unidad_cantidad = filtros.get("unidad_cantidad", "")

    if ceic:
        ceic, error = validar_ceic_filtro(ceic)
        if not error:
            queryset = queryset.filter(ceic=int(ceic))
        else:
            mensajes.append(error)
            errores["ceic"] = error
            queryset = queryset.none()

    if cargo:
        queryset = queryset.filter(cargo__icontains=cargo)

    if estado_pof:
        estado_pof, error = validar_estado_pof_filtro(estado_pof)
        if not error:
            queryset = queryset.filter(estado_pof=estado_pof)
        else:
            mensajes.append(error)
            errores["estado_pof"] = error
            queryset = queryset.none()

    if unidad_cantidad:
        unidad_cantidad, error = validar_unidad_cantidad_filtro(unidad_cantidad)
        if not error:
            queryset = queryset.filter(unidad_cantidad=unidad_cantidad)
        else:
            mensajes.append(error)
            errores["unidad_cantidad"] = error
            queryset = queryset.none()

    return queryset, " ".join(mensajes), errores


def _calcular_resumen_resultado_detalle(grupos):
    """
    Calcula los contadores globales del resultado visible del Detalle común.

    - Usa la misma estructura que se renderiza en pantalla para evitar divergencias.
    - Cuenta cargos, CUE con resultados y anexos reales por CUE.
    - No recalcula puntos ni modifica los totales completos de cada CUE.
    """
    cantidad_cargos = 0
    anexos_por_cue = set()

    for grupo_cue in grupos:
        cue = str(grupo_cue.get("cue", "") or "")
        for grupo_anexo in grupo_cue.get("anexos", []):
            cueanexo = str(grupo_anexo.get("cueanexo", "") or "")
            if cueanexo:
                anexos_por_cue.add((cue, cueanexo))
            cantidad_cargos += len(grupo_anexo.get("cargos", []))

    return {
        "cargos": cantidad_cargos,
        "cues": len(grupos),
        "anexos": len(anexos_por_cue),
    }


def _hay_errores_filtros_detalle(*grupos_errores):
    """
    Indica si la validacion de filtros del Detalle comun produjo errores de campo.

    - Consolida errores de filtros de localizacion y de cargo.
    - Permite evitar resumenes o estados vacios que parezcan resultados validos.
    - No altera la forma en que se aplican los QuerySets existentes.
    """
    return any(bool(errores) for errores in grupos_errores)


def _fusionar_grupos_detalle_con_coincidencias(grupos_base, grupos_coincidentes):
    """
    Combina totales base de CUE con cargos coincidentes por Anexo/CUOF.

    - Conserva encabezados y totales CUE calculados desde el alcance base.
    - Mantiene solo Anexo/CUOF que contienen cargos coincidentes.
    - Reemplaza la lista de cargos por las coincidencias sin recalcular totales.
    """
    anexos_coincidentes_por_clave = {}

    for grupo in grupos_coincidentes:
        cue = str(grupo.get("cue", "") or "")
        for anexo in grupo.get("anexos", []):
            clave = (
                cue,
                str(anexo.get("cueanexo", "") or ""),
                str(anexo.get("cuof", "") or ""),
            )
            anexos_coincidentes_por_clave[clave] = anexo

    grupos_resultado = []
    for grupo_base in grupos_base:
        cue = str(grupo_base.get("cue", "") or "")
        anexos = []
        for anexo_base in grupo_base.get("anexos", []):
            clave = (
                cue,
                str(anexo_base.get("cueanexo", "") or ""),
                str(anexo_base.get("cuof", "") or ""),
            )
            anexo_coincidente = anexos_coincidentes_por_clave.get(clave)
            if not anexo_coincidente:
                continue

            anexo = dict(anexo_base)
            anexo["cargos"] = anexo_coincidente.get("cargos", [])
            anexo["cantidad_cargos_coincidentes"] = len(anexo["cargos"])
            anexos.append(anexo)

        if anexos:
            grupo = dict(grupo_base)
            grupo["anexos"] = anexos
            grupos_resultado.append(grupo)

    return grupos_resultado


def _obtener_cargos_detalle_proyecto(proyecto_especial_id):
    return _obtener_cargos_detalle_queryset().filter(
        localizacion__proyecto_especial_id=proyecto_especial_id,
    )


def _construir_grupos_cue_reales(cargos):
    grupos_por_clave = {}

    for cargo in cargos:
        localizacion = cargo.localizacion
        snapshot = _obtener_snapshot_vigente(localizacion)
        cue_base = localizacion.cue_base or "—"
        cuof = localizacion.cuof or "—"
        clave_grupo = (cuof, cue_base)
        establecimiento = _obtener_establecimiento(snapshot)

        if clave_grupo not in grupos_por_clave:
            grupos_por_clave[clave_grupo] = {
                "cuof": cuof,
                "cue_base": cue_base,
                "cui": _valor_o_guion(localizacion.cui),
                "establecimiento_base": establecimiento,
                "total_valor": 0,
                "total": _formatear_decimal(0),
                "anexos": [],
                "_anexos_por_clave": {},
            }

        grupo = grupos_por_clave[clave_grupo]
        if localizacion.anexo_localizacion == "00" and establecimiento != "—":
            grupo["establecimiento_base"] = establecimiento
            grupo["cui"] = _valor_o_guion(localizacion.cui)

        clave_anexo = localizacion.id
        if clave_anexo not in grupo["_anexos_por_clave"]:
            anexo = _crear_anexo_desde_localizacion(localizacion, snapshot)
            grupo["_anexos_por_clave"][clave_anexo] = anexo
            grupo["anexos"].append(anexo)

        anexo = grupo["_anexos_por_clave"][clave_anexo]
        anexo["cargos"].append(_serializar_cargo_detalle(cargo))

        if cargo.esta_afectado:
            anexo["total_valor"] += cargo.total
            grupo["total_valor"] += cargo.total

    grupos = []
    for grupo in grupos_por_clave.values():
        for anexo in grupo["anexos"]:
            anexo["total"] = _formatear_decimal(anexo["total_valor"])
            anexo.pop("total_valor", None)

        grupo["total"] = _formatear_decimal(grupo["total_valor"])
        grupo.pop("total_valor", None)
        grupo.pop("_anexos_por_clave", None)
        grupos.append(grupo)

    return grupos


def _calcular_totales_por_localizacion(cargos):
    totales = {}

    for cargo in cargos:
        if cargo.esta_afectado:
            totales[cargo.localizacion_id] = (
                totales.get(cargo.localizacion_id, Decimal("0")) + cargo.total
            )

    return totales


def _construir_querystring_administrar(localizacion):
    params = {}

    if localizacion.proyecto_especial_id:
        params["cabecera_tipo"] = "PROYECTO_ESPECIAL"
        params["proyecto_especial_id"] = localizacion.proyecto_especial_id
    elif localizacion.reunida:
        params["anio"] = localizacion.reunida.anio
        params["nivel"] = localizacion.reunida.nivel

    if localizacion.cueanexo:
        params["cueanexo"] = localizacion.cueanexo

    return urlencode(params)


def _construir_querystring_administrar_proyecto(proyecto_especial_id, cuof="", cueanexo=""):
    if not cueanexo and not cuof:
        return ""

    params = {
        "cabecera_tipo": "PROYECTO_ESPECIAL",
        "proyecto_especial_id": proyecto_especial_id,
    }

    if cueanexo:
        params["cueanexo"] = cueanexo
    if cuof:
        params["cuof"] = cuof

    return urlencode(params)


def _es_cueanexo_oficial_detalle(cueanexo):
    cueanexo = str(cueanexo or "").strip()
    return len(cueanexo) == 9 and cueanexo.isdigit()


def _obtener_info_cue_proyecto(cargos):
    filas_normalizadas = construir_filas_normalizadas(cargos)
    grupos_operativos = construir_grupos_operativos_detalle(
        filas_normalizadas=filas_normalizadas,
        detalle_politicas=obtener_politicas_detalle_reunida(),
    )
    return {
        grupo.get("cue", ""): grupo.get("info_cue", [])
        for grupo in grupos_operativos
        if grupo.get("cue")
    }


def _construir_grupos_detalle_proyecto(cargos, proyecto_especial_id):
    cargos = list(cargos)
    grupos_por_clave = {}
    info_cue_por_cue = _obtener_info_cue_proyecto(cargos)

    for cargo in cargos:
        localizacion = cargo.localizacion
        snapshot = _obtener_snapshot_vigente(localizacion)
        cueanexo = str(localizacion.cueanexo or "").strip()
        cuof = str(localizacion.cuof or "").strip()
        es_oficial = _es_cueanexo_oficial_detalle(cueanexo)
        cueanexo_operativo = cueanexo if es_oficial else ""
        cue = cueanexo[:7] if es_oficial else ""
        anexo = cueanexo[7:9] if es_oficial else ""
        tipo_identidad = "CUE" if es_oficial else "CUOF"
        identificador = cue if es_oficial else (cuof or f"LOCALIZACION:{localizacion.id}")
        clave_grupo = f"{tipo_identidad}:{identificador}"

        if clave_grupo not in grupos_por_clave:
            grupos_por_clave[clave_grupo] = {
                "tipo_identidad": tipo_identidad,
                "clave": clave_grupo,
                "cue": cue,
                "cuof": cuof,
                "establecimiento": "",
                "info_cue": info_cue_por_cue.get(cue, []) if es_oficial else [],
                "total_anexos": 0,
                "cueanexos_set": set(),
                "total_valor": Decimal("0"),
                "total_puntos": _formatear_decimal(0),
                "total_cargos": 0,
                "total_localizaciones": 0,
                "localizaciones": [],
                "_localizaciones_por_id": {},
            }

        grupo = grupos_por_clave[clave_grupo]
        if es_oficial:
            grupo["cueanexos_set"].add(cueanexo)

        if localizacion.id not in grupo["_localizaciones_por_id"]:
            establecimiento = _obtener_establecimiento(snapshot)
            if establecimiento == "—":
                establecimiento = ""
            localizacion_detalle = {
                "localizacion_id": localizacion.id,
                "cueanexo": cueanexo_operativo,
                "cue": cue,
                "anexo": anexo,
                "cuof": cuof,
                "cui": str(localizacion.cui or "").strip(),
                "establecimiento": establecimiento,
                "cantidad_cargos": 0,
                "admin_querystring": _construir_querystring_administrar_proyecto(
                    proyecto_especial_id,
                    cuof,
                    cueanexo if es_oficial else "",
                ),
            }
            grupo["_localizaciones_por_id"][localizacion.id] = localizacion_detalle
            grupo["localizaciones"].append(localizacion_detalle)
            if establecimiento and (
                not grupo["establecimiento"] or (es_oficial and anexo == "00")
            ):
                grupo["establecimiento"] = establecimiento

        localizacion_grupo = grupo["_localizaciones_por_id"][localizacion.id]
        localizacion_grupo["cantidad_cargos"] += 1
        grupo["total_cargos"] += 1

        if cargo.esta_afectado:
            grupo["total_valor"] += cargo.total

    grupos = []
    for grupo in grupos_por_clave.values():
        grupo["total_puntos"] = _formatear_decimal(grupo["total_valor"])
        grupo["total_localizaciones"] = len(grupo["localizaciones"])
        grupo["total_anexos"] = len(grupo["cueanexos_set"])
        grupo.pop("total_valor", None)
        grupo.pop("cueanexos_set", None)
        grupo.pop("_localizaciones_por_id", None)
        grupos.append(grupo)

    return grupos


def construir_payload_cargos_detalle_proyecto_localizacion(
    proyecto_especial_id,
    localizacion_id,
):
    cargos = list(
        _obtener_cargos_detalle_queryset().filter(
            localizacion_id=localizacion_id,
            localizacion__proyecto_especial_id=proyecto_especial_id,
        )
    )
    if not cargos:
        return {}

    filas_normalizadas = construir_filas_normalizadas(cargos)
    if not _es_cueanexo_oficial_detalle(
        cargos[0].localizacion.cueanexo
    ):
        for fila in filas_normalizadas:
            fila["cueanexo"] = ""
    enriquecer_filas_con_historial_cantidad(filas_normalizadas)
    enriquecer_filas_con_historial_observacion(filas_normalizadas)
    enriquecer_filas_con_historial_estado(filas_normalizadas)
    grupos_operativos = construir_grupos_operativos_detalle(
        filas_normalizadas=filas_normalizadas,
        detalle_politicas=obtener_politicas_detalle_reunida(),
    )
    if not grupos_operativos or not grupos_operativos[0].get("anexos"):
        return {}

    payload = serializar_grupo_operativo_detalle(
        grupos_operativos[0]["anexos"][0]
    )
    payload["localizacion_id"] = localizacion_id
    return payload


def _construir_grupos_cueanexo_reales(cargos, columnas):
    cargos = list(cargos)
    totales_por_localizacion = _calcular_totales_por_localizacion(cargos)
    grupos_por_cueanexo = {}

    for cargo in cargos:
        localizacion = cargo.localizacion
        cueanexo_valor = localizacion.cueanexo or ""
        cueanexo = cueanexo_valor or "—"
        clave_grupo = cueanexo_valor or f"localizacion-{localizacion.id}"

        if clave_grupo not in grupos_por_cueanexo:
            grupos_por_cueanexo[clave_grupo] = {
                "cueanexo": cueanexo,
                "filas": [],
                "total_valor": Decimal("0"),
                "total": _formatear_decimal(0),
                "admin_querystring": _construir_querystring_administrar(localizacion),
            }

        grupo = grupos_por_cueanexo[clave_grupo]
        grupo["filas"].append(
            armar_fila_proyecto_especial_cargo(
                columnas,
                cargo,
                totales_por_localizacion.get(cargo.localizacion_id, Decimal("0")),
            )
        )

        if cargo.esta_afectado:
            grupo["total_valor"] += cargo.total

    grupos = []
    for grupo in grupos_por_cueanexo.values():
        grupo["total"] = _formatear_decimal(grupo["total_valor"])
        grupo.pop("total_valor", None)
        grupos.append(grupo)

    return grupos


def _construir_querystring_administrar_reunida(anio, nivel_codigo, cueanexo):
    params = {
        "anio": anio,
        "nivel": nivel_codigo,
    }

    if cueanexo:
        params["cueanexo"] = cueanexo

    return urlencode(params)


def _construir_grupos_cueanexo_desde_grilla(grilla, anio, nivel_codigo):
    filas_normalizadas = grilla["filas_normalizadas"]
    filas_render = grilla["filas_render"]
    grupos_por_cueanexo = {}

    for indice, fila_normalizada in enumerate(filas_normalizadas):
        cueanexo_valor = fila_normalizada.get("cueanexo")
        cueanexo = _valor_o_guion(cueanexo_valor)
        localizacion_id = fila_normalizada.get("localizacion_id") or indice
        clave_grupo = cueanexo or f"localizacion-{localizacion_id}"

        if clave_grupo not in grupos_por_cueanexo:
            grupos_por_cueanexo[clave_grupo] = {
                "cueanexo": cueanexo,
                "filas": [],
                "total_valor": Decimal("0"),
                "total": _formatear_decimal(0),
                "admin_querystring": _construir_querystring_administrar_reunida(
                    anio,
                    nivel_codigo,
                    cueanexo_valor,
                ),
            }

        grupo = grupos_por_cueanexo[clave_grupo]
        grupo["filas"].append(filas_render[indice])

        if fila_normalizada.get("estado_pof_codigo") == CargoPof.EstadoPof.AFECTADO:
            grupo["total_valor"] += fila_normalizada.get("total") or Decimal("0")

    grupos = []
    for grupo in grupos_por_cueanexo.values():
        grupo["total"] = _formatear_decimal(grupo["total_valor"])
        grupo.pop("total_valor", None)
        grupos.append(grupo)

    return grupos


def construir_contexto_detalle_reunida(request):
    cabecera_tipo = str(request.GET.get("cabecera_tipo", "") or "").strip().upper()
    proyecto_especial_id = limpiar_texto(request.GET.get("proyecto_especial_id", ""), 20)
    es_proyecto_especial = cabecera_tipo == "PROYECTO_ESPECIAL" or bool(proyecto_especial_id)

    if es_proyecto_especial:
        mensaje_detalle = ""
        mensaje_filtros_detalle = ""
        mensaje_filtros_cargo_detalle = ""
        errores_filtros_detalle = {}
        errores_filtros_cargo_detalle = {}
        proyecto_obj = None
        columnas_detalle = list(COLUMNAS_PROYECTO_ESPECIAL)
        grupos_cueanexo = []
        grupos_detalle_proyecto = []
        filtros_detalle = _obtener_filtros_detalle_reunida(request)
        filtros_avanzados_detalle = _obtener_filtros_avanzados_detalle_reunida(request)
        busquedas_columna_detalle = _obtener_busquedas_columna_detalle_reunida(request)
        detalle_busqueda_columna_id, detalle_busqueda_columna_valor = (
            _obtener_busqueda_columna_activa_detalle_reunida(busquedas_columna_detalle)
        )
        filtros_detalle_activos = (
            _hay_filtros_detalle_reunida(
                filtros_detalle,
                FILTROS_DETALLE_PROYECTO,
            )
            or bool(filtros_avanzados_detalle)
            or bool(busquedas_columna_detalle)
        )
        filtros_cargo_detalle_activos = _hay_filtros_cargo_detalle_reunida(filtros_detalle)

        if not proyecto_especial_id.isdigit():
            mensaje_detalle = "Debe seleccionar un Proyecto Especial POF valido."
        else:
            try:
                proyecto_obj = ProyectosEspecialesPof.objects.get(pk=proyecto_especial_id)
                cargos_detalle = _obtener_cargos_detalle_proyecto(proyecto_especial_id)
                (
                    cargos_detalle,
                    mensaje_filtros_detalle,
                    errores_filtros_detalle,
                ) = _aplicar_filtros_detalle_reunida(
                    cargos_detalle,
                    filtros_detalle,
                    incluir_cui=True,
                )
                cargos_detalle = _aplicar_filtros_avanzados_detalle_reunida(
                    cargos_detalle,
                    filtros_avanzados_detalle,
                )
                cargos_detalle = _aplicar_busquedas_columna_detalle_reunida(
                    cargos_detalle,
                    busquedas_columna_detalle,
                )
                (
                    cargos_detalle,
                    mensaje_filtros_cargo_detalle,
                    errores_filtros_cargo_detalle,
                ) = _aplicar_filtros_cargo_detalle_reunida(
                    cargos_detalle,
                    filtros_detalle,
                )
                grupos_detalle_proyecto = _construir_grupos_detalle_proyecto(
                    cargos_detalle,
                    proyecto_obj.id,
                )
            except ProyectosEspecialesPof.DoesNotExist:
                mensaje_detalle = "No existe el Proyecto Especial POF seleccionado."
            except (ProgrammingError, OperationalError):
                mensaje_detalle = "No se pudieron consultar los datos reales del Proyecto Especial POF."

        anio = str(proyecto_obj.anio) if proyecto_obj else ""
        nombre = proyecto_obj.nombre if proyecto_obj else "-"
        resolucion = proyecto_obj.resolucion if proyecto_obj and proyecto_obj.resolucion else "Sin resolucion"
        cabecera_querystring = (
            f"cabecera_tipo=PROYECTO_ESPECIAL&proyecto_especial_id={proyecto_obj.id}"
            if proyecto_obj
            else ""
        )
        base_params_detalle = (
            {
                "cabecera_tipo": "PROYECTO_ESPECIAL",
                "proyecto_especial_id": proyecto_obj.id,
            }
            if proyecto_obj
            else {}
        )
        detalle_limpiar_filtros_querystring = urlencode(base_params_detalle) if base_params_detalle else ""
        detalle_quitar_filtro_querystrings = _construir_querystrings_quitar_filtros_detalle_base(
            filtros_detalle,
            base_params_detalle,
            FILTROS_DETALLE_PROYECTO,
        ) if base_params_detalle else {}
        errores_filtros_detalle_todos = {
            **errores_filtros_detalle,
            **errores_filtros_cargo_detalle,
        }
        filtros_detalle_chips = _construir_chips_filtros_detalle(
            filtros_detalle,
            detalle_quitar_filtro_querystrings,
            errores_filtros_detalle_todos,
            FILTROS_DETALLE_PROYECTO,
        ) if base_params_detalle else []
        filtros_detalle_chips = _construir_chips_detalle_dinamicos(
            filtros_detalle_chips,
            filtros_avanzados_detalle,
            busquedas_columna_detalle,
        ) if base_params_detalle else []
        filtros_detalle_invalidos = _hay_errores_filtros_detalle(
            errores_filtros_detalle,
            errores_filtros_cargo_detalle,
        )
        paginacion_grupos_detalle = _paginar_grupos_cue_detalle([], 1)
        if not filtros_detalle_invalidos:
            paginacion_grupos_detalle = _paginar_grupos_cue_detalle(
                grupos_detalle_proyecto,
                request.GET.get("page", 1),
            )
            grupos_detalle_proyecto = paginacion_grupos_detalle["grupos"]
        paginacion_grupos_detalle["query_params_base"] = (
            _construir_query_params_paginacion_detalle(request)
        )
        detalle_exportar_querystring = _construir_querystring_detalle_con_filtros(
            filtros_detalle,
            base_params_detalle,
            FILTROS_DETALLE_PROYECTO,
        ) if base_params_detalle else ""

        return {
            "anio_activo": anio,
            "nivel_codigo": "",
            "cabecera_tipo_activa": "PROYECTO_ESPECIAL",
            "proyecto_especial_id_activo": str(proyecto_obj.id) if proyecto_obj else "",
            "es_proyecto_especial": True,
            "seccion_activa": "proyectos_especiales",
            "titulo_detalle": "DETALLE DE PROYECTO ESPECIAL",
            "descripcion_detalle": "Detalle operativo de cargos del Proyecto Especial por CUE/Anexo o CUOF, según la identidad disponible.",
            "cabecera_detalle_nombre": "Proyecto Especial",
            "cabecera_querystring": cabecera_querystring,
            "detalle_exportar_querystring": detalle_exportar_querystring,
            "detalle_limpiar_filtros_querystring": detalle_limpiar_filtros_querystring,
            "detalle_quitar_filtro_querystrings": detalle_quitar_filtro_querystrings,
            "filtros_detalle": filtros_detalle,
            "filtros_detalle_chips": filtros_detalle_chips,
            "filtros_detalle_activos": filtros_detalle_activos,
            "filtros_avanzados_detalle": filtros_avanzados_detalle,
            "busquedas_columna_detalle": busquedas_columna_detalle,
            "detalle_busqueda_columnas": COLUMNAS_BUSQUEDA_DETALLE_REUNIDA,
            "detalle_busqueda_columna_id": detalle_busqueda_columna_id,
            "detalle_busqueda_columna_valor": detalle_busqueda_columna_valor,
            "filtros_detalle_campos": FILTROS_AVANZADOS_DETALLE_CAMPOS,
            "filtros_detalle_opciones": _construir_opciones_filtros_detalle_reunida(),
            "filtros_cargo_detalle_activos": filtros_cargo_detalle_activos,
            "mensaje_filtros_detalle": mensaje_filtros_detalle,
            "mensaje_filtros_cargo_detalle": mensaje_filtros_cargo_detalle,
            "mensaje_filtros_detalle_general": MENSAJE_FILTROS_INVALIDOS if filtros_detalle_invalidos else "",
            "errores_filtros_detalle": errores_filtros_detalle,
            "errores_filtros_cargo_detalle": errores_filtros_cargo_detalle,
            "filtros_detalle_invalidos": filtros_detalle_invalidos,
            "mensaje_detalle": mensaje_detalle,
            "reunida": {
                "anio": anio,
                "nivel": nombre,
                "nivel_codigo": "",
                "estado": "Abierta",
                "existe": bool(proyecto_obj),
            },
            "proyecto_especial": {
                "id": proyecto_obj.id if proyecto_obj else "",
                "anio": anio,
                "nombre": nombre,
                "resolucion": resolucion,
            },
            "columnas_detalle": columnas_detalle,
            "opciones_estado_pof_detalle": CargoPof.EstadoPof.choices,
            "opciones_unidad_cantidad_detalle": CargoPof.UnidadCantidad.choices,
            "detalle_total_label_colspan": max(len(columnas_detalle) - 1, 1),
            "grupos_detalle_proyecto": grupos_detalle_proyecto,
            "paginacion_grupos_detalle": paginacion_grupos_detalle,
            "grupos_cueanexo": grupos_cueanexo,
        }

    anio_parametro = limpiar_texto(request.GET.get("anio", ""), 4)
    nivel_parametro = request.GET.get("nivel", "")
    nivel_codigo = normalizar_nivel(nivel_parametro)
    nivel = obtener_nombre_nivel(nivel_codigo, nivel_parametro)
    tiene_contexto = bool(anio_parametro.isdigit() and len(anio_parametro) == 4 and nivel_codigo)
    filtros_detalle = _obtener_filtros_detalle_reunida(request)
    filtros_avanzados_detalle = _obtener_filtros_avanzados_detalle_reunida(request)
    busquedas_columna_detalle = _obtener_busquedas_columna_detalle_reunida(request)
    detalle_busqueda_columna_id, detalle_busqueda_columna_valor = (
        _obtener_busqueda_columna_activa_detalle_reunida(busquedas_columna_detalle)
    )
    filtros_detalle_activos = (
        _hay_filtros_detalle_reunida(filtros_detalle)
        or bool(filtros_avanzados_detalle)
        or bool(busquedas_columna_detalle)
    )
    filtros_cargo_detalle_activos = _hay_filtros_cargo_detalle_reunida(filtros_detalle)
    mensaje_filtros_detalle = ""
    mensaje_filtros_cargo_detalle = ""
    errores_filtros_detalle = {}
    errores_filtros_cargo_detalle = {}
    mensaje_detalle = ""
    reunida_obj = None
    columnas_detalle = []
    detalle_politicas = {}
    grupos_operativos_detalle = []
    cantidad_grupos_operativos_detalle = 0
    grupos_coincidentes_detalle = []
    resumen_coincidencias_detalle = {
        "cargos": 0,
        "cues": 0,
        "anexos": 0,
    }
    grupos_cueanexo = []

    if not anio_parametro or not anio_parametro.isdigit() or len(anio_parametro) != 4 or not nivel_codigo:
        mensaje_detalle = "Debe seleccionar una Reunida válida por año y nivel."
    else:
        try:
            reunida_obj = ReunidaPof.objects.get(anio=int(anio_parametro), nivel=nivel_codigo)
            cargos_alcance_detalle = _obtener_cargos_detalle_reunida(reunida_obj)
            (
                cargos_alcance_detalle,
                mensaje_filtros_detalle,
                errores_filtros_detalle,
            ) = _aplicar_filtros_detalle_reunida(
                cargos_alcance_detalle,
                filtros_detalle,
            )
            cargos_alcance_detalle = _aplicar_filtros_avanzados_detalle_reunida(
                cargos_alcance_detalle,
                filtros_avanzados_detalle,
            )
            cargos_alcance_detalle = _aplicar_busquedas_columna_detalle_reunida(
                cargos_alcance_detalle,
                busquedas_columna_detalle,
            )
            grilla_detalle = construir_grilla_pof_desde_cargos(
                cargos=cargos_alcance_detalle,
                nivel_codigo=nivel_codigo,
                contexto="DETALLE_REUNIDA",
                espejo=False,
            )
            columnas_detalle = list(grilla_detalle["columnas"])
            detalle_politicas = grilla_detalle.get("detalle_politicas", {})
            grupos_operativos_detalle = grilla_detalle.get("grupos_operativos_detalle", [])
            cantidad_grupos_operativos_detalle = grilla_detalle.get("cantidad_grupos_operativos_detalle", 0)
            grupos_cueanexo = _construir_grupos_cueanexo_desde_grilla(
                grilla_detalle,
                anio_parametro,
                nivel_codigo,
            )
            if filtros_detalle_activos:
                resumen_coincidencias_detalle = _calcular_resumen_resultado_detalle(
                    grupos_operativos_detalle,
                )
            if filtros_cargo_detalle_activos:
                cargos_coincidentes = cargos_alcance_detalle
                (
                    cargos_coincidentes,
                    mensaje_filtros_cargo_detalle,
                    errores_filtros_cargo_detalle,
                ) = _aplicar_filtros_cargo_detalle_reunida(
                    cargos_coincidentes,
                    filtros_detalle,
                )
                grilla_coincidencias = construir_grilla_pof_desde_cargos(
                    cargos=cargos_coincidentes,
                    nivel_codigo=nivel_codigo,
                    contexto="DETALLE_REUNIDA",
                    espejo=False,
                )
                grupos_coincidentes_detalle = _fusionar_grupos_detalle_con_coincidencias(
                    grupos_operativos_detalle,
                    grilla_coincidencias.get("grupos_operativos_detalle", []),
                )
                resumen_coincidencias_detalle = _calcular_resumen_resultado_detalle(
                    grupos_coincidentes_detalle,
                )
        except ReunidaPof.DoesNotExist:
            mensaje_detalle = "No existe una Reunida POF para el año y nivel seleccionados."
        except (ProgrammingError, OperationalError):
            mensaje_detalle = "No se pudieron consultar los datos reales de la Reunida."

    if not columnas_detalle:
        grilla_detalle_vacia = construir_grilla_pof_desde_cargos(
            cargos=[],
            nivel_codigo=nivel_codigo or "PRIMARIA",
            contexto="DETALLE_REUNIDA",
            espejo=False,
        )
        columnas_detalle = list(grilla_detalle_vacia["columnas"])
        detalle_politicas = grilla_detalle_vacia.get("detalle_politicas", detalle_politicas)
        grupos_operativos_detalle = grilla_detalle_vacia.get("grupos_operativos_detalle", grupos_operativos_detalle)
        cantidad_grupos_operativos_detalle = grilla_detalle_vacia.get(
            "cantidad_grupos_operativos_detalle",
            cantidad_grupos_operativos_detalle,
        )

    anio = anio_parametro if anio_parametro else ""
    cabecera_querystring = f"anio={anio}&nivel={nivel_codigo}" if tiene_contexto else ""
    detalle_limpiar_filtros_querystring = urlencode(
        {
            "cabecera_tipo": "REUNIDA",
            "anio": anio,
            "nivel": nivel_codigo,
        }
    ) if tiene_contexto else ""
    detalle_quitar_filtro_querystrings = _construir_querystrings_quitar_filtros_detalle(
        filtros_detalle,
        anio,
        nivel_codigo,
    ) if tiene_contexto else {}
    errores_filtros_detalle_todos = {
        **errores_filtros_detalle,
        **errores_filtros_cargo_detalle,
    }
    filtros_detalle_chips = _construir_chips_filtros_detalle(
        filtros_detalle,
        detalle_quitar_filtro_querystrings,
        errores_filtros_detalle_todos,
    ) if tiene_contexto else []
    filtros_detalle_chips = _construir_chips_detalle_dinamicos(
        filtros_detalle_chips,
        filtros_avanzados_detalle,
        busquedas_columna_detalle,
    ) if tiene_contexto else []
    nivel_nombre = reunida_obj.get_nivel_display() if reunida_obj else (nivel or "—")
    filtros_detalle_invalidos = _hay_errores_filtros_detalle(
        errores_filtros_detalle,
        errores_filtros_cargo_detalle,
    )
    mostrar_resumen_detalle = filtros_detalle_activos and not filtros_detalle_invalidos
    paginacion_grupos_detalle = _paginar_grupos_cue_detalle([], 1)

    if not filtros_detalle_invalidos:
        if filtros_cargo_detalle_activos:
            paginacion_grupos_detalle = _paginar_grupos_cue_detalle(
                grupos_coincidentes_detalle,
                request.GET.get("page", 1),
            )
            grupos_coincidentes_detalle = paginacion_grupos_detalle["grupos"]
        else:
            paginacion_grupos_detalle = _paginar_grupos_cue_detalle(
                grupos_operativos_detalle,
                request.GET.get("page", 1),
            )
            grupos_operativos_detalle = paginacion_grupos_detalle["grupos"]
    paginacion_grupos_detalle["query_params_base"] = _construir_query_params_paginacion_detalle(request)

    return {
        "anio_activo": anio if tiene_contexto else "",
        "nivel_codigo": nivel_codigo if tiene_contexto else "",
        "cabecera_tipo_activa": "REUNIDA",
        "proyecto_especial_id_activo": "",
        "es_proyecto_especial": False,
        "seccion_activa": "reunidas",
        "titulo_detalle": "DETALLE DE POF",
        "descripcion_detalle": "Visualiza el resumen de localizaciones, cargos, puntos y estado de la POF.",
        "cabecera_detalle_nombre": "POF",
        "cabecera_querystring": cabecera_querystring,
        "detalle_limpiar_filtros_querystring": detalle_limpiar_filtros_querystring,
        "detalle_quitar_filtro_querystrings": detalle_quitar_filtro_querystrings,
        "filtros_detalle": filtros_detalle,
        "filtros_detalle_chips": filtros_detalle_chips,
        "filtros_detalle_activos": filtros_detalle_activos,
        "filtros_avanzados_detalle": filtros_avanzados_detalle,
        "busquedas_columna_detalle": busquedas_columna_detalle,
        "detalle_busqueda_columnas": COLUMNAS_BUSQUEDA_DETALLE_REUNIDA,
        "detalle_busqueda_columna_id": detalle_busqueda_columna_id,
        "detalle_busqueda_columna_valor": detalle_busqueda_columna_valor,
        "filtros_detalle_campos": FILTROS_AVANZADOS_DETALLE_CAMPOS,
        "filtros_detalle_opciones": _construir_opciones_filtros_detalle_reunida(),
        "filtros_cargo_detalle_activos": filtros_cargo_detalle_activos,
        "mensaje_filtros_detalle": mensaje_filtros_detalle,
        "mensaje_filtros_cargo_detalle": mensaje_filtros_cargo_detalle,
        "mensaje_filtros_detalle_general": MENSAJE_FILTROS_INVALIDOS if filtros_detalle_invalidos else "",
        "errores_filtros_detalle": errores_filtros_detalle,
        "errores_filtros_cargo_detalle": errores_filtros_cargo_detalle,
        "filtros_detalle_invalidos": filtros_detalle_invalidos,
        "mostrar_resumen_detalle": mostrar_resumen_detalle,
        "resumen_coincidencias_detalle": resumen_coincidencias_detalle,
        "mensaje_detalle": mensaje_detalle,
        "reunida": {
            "id": reunida_obj.id if reunida_obj else "",
            "anio": anio,
            "nivel": nivel_nombre,
            "nivel_codigo": nivel_codigo,
            "estado": "Abierta",
            "existe": bool(reunida_obj),
        },
        "columnas_detalle": columnas_detalle,
        "detalle_politicas": detalle_politicas,
        "grupos_operativos_detalle": grupos_operativos_detalle,
        "cantidad_grupos_operativos_detalle": cantidad_grupos_operativos_detalle,
        "grupos_coincidentes_detalle": grupos_coincidentes_detalle,
        "paginacion_grupos_detalle": paginacion_grupos_detalle,
        "opciones_estado_pof_detalle": CargoPof.EstadoPof.choices,
        "opciones_unidad_cantidad_detalle": CargoPof.UnidadCantidad.choices,
        "detalle_total_label_colspan": max(len(columnas_detalle) - 1, 1),
        "grupos_cueanexo": grupos_cueanexo,
    }
