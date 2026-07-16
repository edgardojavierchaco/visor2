import re

from django.http import QueryDict

from ..models import CargoPof
from .niveles_service import NIVELES_VALIDOS, limpiar_texto, normalizar_nivel


VISTA_RECIENTES = "recientes"
VISTA_7_DIAS = "7_dias"
VISTA_30_DIAS = "30_dias"

VISTAS_RAPIDAS = {
    VISTA_RECIENTES: "Más recientes",
    VISTA_7_DIAS: "Últimos 7 días",
    VISTA_30_DIAS: "Últimos 30 días",
}

TIPOS_MOVIMIENTO_LABELS = {
    "ALTA": "Alta",
    "MODIFICACION": "Modificación",
    "AFECTACION": "Afectación",
    "DESAFECTACION": "Desafectación",
}

NIVEL_TODOS = "__todos__"
TIPO_MOVIMIENTO_TODOS = "__todos__"
CUOF_FILTRO_MAX_LENGTH = 100
TEXTO_FILTRO_SEGURO_RE = re.compile(r"^[^\x00-\x1f\x7f<>]*$")
MENSAJE_FILTROS_INVALIDOS = "Correg\u00ed los filtros marcados para continuar."

MENSAJE_ANIO_INVALIDO = "El filtro Año debe contener 4 dígitos."
MENSAJE_NIVEL_INVALIDO = "El filtro Nivel no es válido."
MENSAJE_CUEANEXO_INVALIDO = "El filtro CUEANEXO debe tener 9 dígitos."
MENSAJE_CUE_INVALIDO = "El filtro CUE debe tener 7 dígitos."
MENSAJE_ANEXO_INVALIDO = "El filtro Anexo debe contener exactamente 2 dígitos."
MENSAJE_CUOF_INVALIDO = "El filtro CUOF contiene un valor inválido."
MENSAJE_CEIC_INVALIDO = "El filtro CEIC debe contener entre 1 y 3 dígitos y ser mayor a 0."
MENSAJE_ESTADO_POF_INVALIDO = "El filtro Estado POF no es válido."
MENSAJE_UNIDAD_INVALIDA = "El filtro Unidad no es válido."
MENSAJE_CUIL_INVALIDO = "El filtro CUIL/DNI debe contener entre 9 y 11 dígitos."


def _limpiar_digitos(valor, max_length=20):
    return "".join(
        caracter for caracter in limpiar_texto(valor, max_length) if caracter.isdigit()
    )


def _validar_filtro_digitos(valor, longitud, mensaje, permitir_vacio=True):
    texto = limpiar_texto(valor, max(longitud, 20))
    if not texto and permitir_vacio:
        return "", ""
    if texto.isdigit() and len(texto) == longitud:
        return texto, ""
    return texto, mensaje


def validar_anio_filtro(valor):
    """
    Valida el año usado por filtros GET del módulo POF.

    - Acepta solo cuatro dígitos.
    - Devuelve el valor limpio para mostrarlo en el formulario si es inválido.
    - Comparte el mismo mensaje entre pantallas.
    """
    return _validar_filtro_digitos(valor, 4, MENSAJE_ANIO_INVALIDO)


def validar_cueanexo_filtro(valor):
    """
    Valida un CUEANEXO completo para filtros administrativos POF.

    - Acepta exactamente nueve dígitos.
    - Mantiene el filtro como coincidencia exacta en backend.
    - Evita que valores parciales disparen consultas amplias.
    """
    return _validar_filtro_digitos(valor, 9, MENSAJE_CUEANEXO_INVALIDO)


def validar_nivel_filtro(valor, permitir_todos=True):
    """
    Valida el nivel usado en filtros GET del módulo POF.

    - Acepta solo niveles definidos en el servicio de niveles.
    - Acepta `__todos__` únicamente cuando la pantalla lo permite.
    - Devuelve error para valores inventados sin aplicarlos al QuerySet.
    """
    nivel = limpiar_texto(valor, 30)
    if not nivel:
        return "", ""
    if permitir_todos and nivel == NIVEL_TODOS:
        return NIVEL_TODOS, ""
    nivel_normalizado = normalizar_nivel(nivel)
    if nivel_normalizado:
        return nivel_normalizado, ""
    return nivel, MENSAJE_NIVEL_INVALIDO


def validar_cue_filtro(valor):
    """
    Valida el CUE base usado en el Detalle de Reunida.

    - Acepta exactamente siete dígitos.
    - No reemplaza al filtro por CUEANEXO completo.
    - Devuelve error de campo sin lanzar excepciones.
    """
    return _validar_filtro_digitos(valor, 7, MENSAJE_CUE_INVALIDO)


def validar_anexo_filtro(valor):
    """
    Valida el anexo usado en el Detalle de Reunida.

    - Acepta exactamente dos dígitos.
    - Conserva ceros a la izquierda.
    - Devuelve error de campo para entradas parciales o no numéricas.
    """
    return _validar_filtro_digitos(valor, 2, MENSAJE_ANEXO_INVALIDO)


def validar_cuof_filtro(valor):
    """
    Valida CUOF como texto seguro para filtros POF.

    - No lo convierte a entero para preservar ceros a la izquierda.
    - Rechaza caracteres de control o marcas HTML.
    - Acota la longitud para mantener consultas razonables.
    """
    cuof = limpiar_texto(valor, 200)
    if not cuof:
        return "", ""
    if (
        len(cuof) > CUOF_FILTRO_MAX_LENGTH
        or not TEXTO_FILTRO_SEGURO_RE.fullmatch(cuof)
    ):
        return cuof, MENSAJE_CUOF_INVALIDO
    return cuof, ""


def validar_ceic_filtro(valor):
    """
    Valida el CEIC usado por consultar, historial y detalle.

    - Acepta de uno a tres dígitos.
    - Exige valor mayor a cero.
    - Devuelve el mismo mensaje funcional para todas las pantallas.
    """
    ceic = limpiar_texto(valor, 20)
    if not ceic:
        return "", ""
    if ceic.isdigit() and 1 <= len(ceic) <= 3 and int(ceic) > 0:
        return ceic, ""
    return ceic, MENSAJE_CEIC_INVALIDO


def validar_estado_pof_filtro(valor):
    """
    Valida Estado POF contra las choices reales de CargoPof.

    - Acepta solo códigos definidos en el modelo.
    - Normaliza a mayúsculas para comparar de forma estable.
    - Devuelve error sin aplicar filtros si llega un valor inventado.
    """
    estado = limpiar_texto(valor, 30).upper()
    if not estado:
        return "", ""
    estados_validos = {codigo for codigo, _ in CargoPof.EstadoPof.choices}
    if estado in estados_validos:
        return estado, ""
    return estado, MENSAJE_ESTADO_POF_INVALIDO


def validar_unidad_cantidad_filtro(valor):
    """
    Valida Unidad de cantidad contra las choices reales de CargoPof.

    - Acepta solo códigos definidos en el modelo.
    - Normaliza a mayúsculas para mantener selects y querystrings estables.
    - Devuelve error de campo si el valor no pertenece al dominio POF.
    """
    unidad = limpiar_texto(valor, 30).upper()
    if not unidad:
        return "", ""
    unidades_validas = {codigo for codigo, _ in CargoPof.UnidadCantidad.choices}
    if unidad in unidades_validas:
        return unidad, ""
    return unidad, MENSAJE_UNIDAD_INVALIDA


def validar_cuil_filtro(valor):
    """
    Valida el CUIL/DNI de usuario para historial de movimientos.

    - Acepta solo dígitos
    - Exige exactamente once dígitos.
    - DNI/CUIL se conserva como texto para filtrar parcialmente sin perder dígitos.
    """
    texto = limpiar_texto(valor, 30)
    if not texto:
        return "", ""
    
    cuil = _limpiar_digitos(texto, 30)
    if 8 <= len(cuil) <= 11:
        return cuil, ""
    return cuil or texto, MENSAJE_CUIL_INVALIDO


def display_estado_pof(valor):
    """
    Devuelve etiqueta legible para chips y listados de Estado POF.

    - Usa "Baja" para DESAFECTADO según la convención visual del módulo.
    - Usa el display del modelo para el resto de estados válidos.
    - Conserva el valor original si no se puede resolver.
    """
    if valor == CargoPof.EstadoPof.DESAFECTADO:
        return "Baja"
    return dict(CargoPof.EstadoPof.choices).get(valor, valor)


def display_unidad_cantidad(valor):
    """
    Devuelve la etiqueta legible de Unidad para filtros POF.

    - Usa las choices reales de CargoPof.
    - Evita mostrar códigos internos en chips cuando existe display.
    - Conserva el valor original si no se puede resolver.
    """
    return dict(CargoPof.UnidadCantidad.choices).get(valor, valor)


def normalizar_anio(valor):
    anio, error = validar_anio_filtro(valor)
    return "" if error else anio


def normalizar_cueanexo(valor):
    cueanexo, error = validar_cueanexo_filtro(valor)
    return "" if error else cueanexo


def normalizar_cuof(valor):
    cuof, error = validar_cuof_filtro(valor)
    return "" if error else cuof


def normalizar_ceic(valor):
    ceic, error = validar_ceic_filtro(valor)
    return "" if error else ceic


def normalizar_cuil(valor):
    """
    Normaliza el CUIL usado para auditar movimientos por usuario.

    - Conserva solo digitos para aceptar entradas con guiones o espacios.
    - Exige 11 digitos para evitar filtros parciales sobre usuarios.
    - Devuelve cadena vacia cuando el valor no es un CUIL valido.
    """
    cuil, error = validar_cuil_filtro(valor)
    return "" if error else cuil


def normalizar_tipo_movimiento(valor):
    tipo = limpiar_texto(valor, 40).upper()
    if tipo == TIPO_MOVIMIENTO_TODOS.upper():
        return TIPO_MOVIMIENTO_TODOS
    return tipo if tipo in TIPOS_MOVIMIENTO_LABELS else ""


def normalizar_nivel_filtro(valor):
    nivel, error = validar_nivel_filtro(valor)
    return "" if error else nivel


def normalizar_vista_rapida(valor):
    vista = limpiar_texto(valor, 20)
    return vista if vista in VISTAS_RAPIDAS else VISTA_RECIENTES


def obtener_filtros_historial_pof(request):
    filtros, _ = obtener_filtros_historial_pof_con_errores(request)
    return filtros


def obtener_filtros_historial_pof_con_errores(request):
    """
    Normaliza filtros de historial y conserva errores de campo.

    - Mantiene la vista rápida propia del historial.
    - Permite mostrar valores inválidos sin aplicarlos al QuerySet.
    - Centraliza las reglas compartidas con consultar y detalle.
    """
    filtros = {
        "anio": "",
        "nivel": "",
        "cueanexo": "",
        "cuof": "",
        "ceic": "",
        "cuil": "",
        "tipo": normalizar_tipo_movimiento(request.GET.get("tipo", "")),
        "vista_rapida": normalizar_vista_rapida(request.GET.get("vista_rapida", "")),
    }
    errores = {}
    validadores = {
        "anio": validar_anio_filtro,
        "cueanexo": validar_cueanexo_filtro,
        "cuof": validar_cuof_filtro,
        "ceic": validar_ceic_filtro,
        "cuil": validar_cuil_filtro,
    }
    for clave, validador in validadores.items():
        valor, error = validador(request.GET.get(clave, ""))
        filtros[clave] = valor
        if error:
            errores[clave] = error
    nivel, error = validar_nivel_filtro(request.GET.get("nivel", ""))
    filtros["nivel"] = nivel
    if error:
        errores["nivel"] = error
    return filtros, errores


def cueanexo_completo(cueanexo):
    return bool(cueanexo and cueanexo.isdigit() and len(cueanexo) == 9)


def cuof_especifico(cuof):
    return bool(cuof and len(cuof) >= 4 and TEXTO_FILTRO_SEGURO_RE.fullmatch(cuof))


def filtros_especificos_activos(filtros):
    return [
        clave
        for clave in (
            "anio",
            "nivel",
            "cueanexo",
            "cuof",
            "ceic",
            "estado_pof",
            "unidad_cantidad",
            "cuil",
            "tipo",
        )
        if filtros.get(clave)
    ]


def filtros_tienen_intencion(filtros):
    return bool(filtros_especificos_activos(filtros) or filtros.get("proyecto_especial_id"))


def _nivel_es_todos(filtros):
    return filtros.get("nivel") == NIVEL_TODOS


def _nivel_especifico(filtros):
    nivel = filtros.get("nivel", "")
    return bool(nivel and nivel != NIVEL_TODOS)


def _filtros_activos_suficiencia(filtros, claves):
    activos = []
    for clave in claves:
        if clave == "cueanexo":
            if cueanexo_completo(filtros.get("cueanexo", "")):
                activos.append(clave)
        elif clave == "cuof":
            if cuof_especifico(filtros.get("cuof", "")):
                activos.append(clave)
        elif clave == "nivel":
            if filtros.get("nivel"):
                activos.append(clave)
        elif filtros.get(clave):
            activos.append(clave)
    return activos


def _filtros_suficientes(filtros, claves, permitir_recientes=False):
    activos = filtros_especificos_activos(filtros)
    if permitir_recientes and not activos and filtros.get("vista_rapida") == VISTA_RECIENTES:
        return True
    if filtros.get("vista_rapida") in {VISTA_7_DIAS, VISTA_30_DIAS}:
        return True
    if cueanexo_completo(filtros.get("cueanexo", "")):
        return True
    if cuof_especifico(filtros.get("cuof", "")):
        return True
    if filtros.get("cuil"):
        return True
    if filtros.get("proyecto_especial_id"):
        return True
    
    activos_suficiencia = _filtros_activos_suficiencia(filtros, claves)
    if activos_suficiencia and set(activos_suficiencia).issubset({"estado_pof", "unidad_cantidad"}):
        return False
    return len(activos_suficiencia) >= 2


def filtros_historial_suficientes(filtros):
    return _filtros_suficientes(
        filtros,
        ("anio", "nivel", "cueanexo", "cuof", "ceic", "cuil", "tipo"),
        permitir_recientes=True,
    )


def filtros_cargos_suficientes(filtros):
    return _filtros_suficientes(
        filtros,
        (
            "anio",
            "nivel",
            "cueanexo",
            "cuof",
            "ceic",
            "estado_pof",
            "unidad_cantidad",
            "proyecto_especial_id",
        ),
    )


def obtener_mensaje_filtros_insuficientes_historial(filtros):
    activos = filtros_especificos_activos(filtros)
    if activos == ["ceic"]:
        return "Para buscar por CEIC, agregá Año, CUEANEXO o CUOF."
    if activos == ["tipo"] and filtros.get("tipo") == TIPO_MOVIMIENTO_TODOS:
        return "Agregá Año, CUEANEXO o CUOF para consultar todos los movimientos."
    if activos == ["tipo"]:
        return "Para buscar por tipo de movimiento, agregá Año, CUEANEXO o CUOF."
    if activos == ["anio"]:
        return "Agregá otro filtro para consultar movimientos del año seleccionado."
    if activos == ["nivel"] and _nivel_es_todos(filtros):
        return "Agregá Año, CUEANEXO o CUOF para consultar todos los niveles."
    if activos == ["nivel"] and _nivel_especifico(filtros):
        return "Agregá Año, CUEANEXO o CUOF para consultar movimientos por nivel."
    return "Agregá al menos otro filtro o ingresá un CUEANEXO/CUOF válido para consultar movimientos."


def obtener_mensaje_filtros_insuficientes_cargos(filtros):
    activos = filtros_especificos_activos(filtros)
    if activos == ["ceic"]:
        return "Para buscar por CEIC, agreg\u00e1 A\u00f1o, CUEANEXO o CUOF."
    if activos and set(activos).issubset({"estado_pof", "unidad_cantidad"}):
        return "Para buscar por Estado y Unidad, agregá Año, CUEANEXO o CUOF."
    if activos == ["estado_pof"]:
        return "Para buscar por Estado POF, agreg\u00e1 A\u00f1o, CUEANEXO o CUOF."
    if activos == ["unidad_cantidad"]:
        return "Para buscar por Unidad, agreg\u00e1 A\u00f1o, CUEANEXO o CUOF."
    if activos == ["anio"]:
        return "Agregá otro filtro para buscar cargos del año seleccionado."
    if activos == ["nivel"] and _nivel_es_todos(filtros):
        return "Agregá Año, CUEANEXO o CUOF para buscar cargos de todos los niveles."
    if activos == ["nivel"] and _nivel_especifico(filtros):
        return "Agregá Año, CUEANEXO o CUOF para buscar cargos por nivel."
    return "Agregá al menos otro filtro o ingresá un CUEANEXO/CUOF válido para buscar cargos."


def _querystring_sin_parametros(request, parametros):
    query = request.GET.copy()
    for parametro in parametros:
        query.pop(parametro, None)
    query.pop("page", None)
    query.pop("texto", None)
    return query.urlencode()


def querystring_limpio_historial(request, page_size):
    query = QueryDict(mutable=True)
    query["vista_rapida"] = VISTA_RECIENTES
    query["page_size"] = page_size
    return query.urlencode()


def querystring_limpio_cargos(request, page_size):
    query = QueryDict(mutable=True)
    query["page_size"] = page_size
    return query.urlencode()


def construir_chips_filtros_historial(request, filtros, errores=None):
    errores = errores or {}
    chips = []
    definiciones = (
        ("anio", "Año", filtros.get("anio")),
        (
            "nivel",
            "Nivel",
            "Todos los niveles"
            if filtros.get("nivel") == NIVEL_TODOS
            else NIVELES_VALIDOS.get(filtros.get("nivel", ""), ""),
        ),
        ("cueanexo", "CUEANEXO", filtros.get("cueanexo")),
        ("cuof", "CUOF", filtros.get("cuof")),
        ("ceic", "CEIC", filtros.get("ceic")),
        ("cuil", "CUIL", filtros.get("cuil")),
        (
            "tipo",
            "Movimiento",
            "Todos los movimientos"
            if filtros.get("tipo") == TIPO_MOVIMIENTO_TODOS
            else TIPOS_MOVIMIENTO_LABELS.get(filtros.get("tipo", ""), ""),
        ),
    )
    for clave, etiqueta, valor in definiciones:
        if valor and clave not in errores:
            chips.append({
                "clave": clave,
                "etiqueta": etiqueta,
                "valor": valor,
                "querystring": _querystring_sin_parametros(request, [clave]),
            })

    vista = filtros.get("vista_rapida")
    if vista and vista != VISTA_RECIENTES:
        chips.append({
            "clave": "vista_rapida",
            "etiqueta": "Vista",
            "valor": VISTAS_RAPIDAS[vista],
            "querystring": _querystring_sin_parametros(request, ["vista_rapida"]),
        })

    return chips


def construir_chips_filtros_cargos(request, filtros, errores=None):
    errores = errores or {}
    chips = []
    definiciones = (
        ("anio", "Año", filtros.get("anio")),
        (
            "nivel",
            "Nivel",
            "Todos los niveles"
            if filtros.get("nivel") == NIVEL_TODOS
            else NIVELES_VALIDOS.get(filtros.get("nivel", ""), ""),
        ),
        ("cueanexo", "CUEANEXO", filtros.get("cueanexo")),
        ("cuof", "CUOF", filtros.get("cuof")),
        ("ceic", "CEIC", filtros.get("ceic")),
        ("estado_pof", "Estado POF", display_estado_pof(filtros.get("estado_pof"))),
        ("unidad_cantidad", "Unidad", display_unidad_cantidad(filtros.get("unidad_cantidad"))),
    )
    for clave, etiqueta, valor in definiciones:
        if valor and clave not in errores:
            chips.append({
                "clave": clave,
                "etiqueta": etiqueta,
                "valor": valor,
                "querystring": _querystring_sin_parametros(request, [clave]),
            })

    return chips
