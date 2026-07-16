from ..exportacion_rows import construir_datos_normalizados_cargo
from .columnas import obtener_clave_columna


COLUMNAS_PROYECTO_ESPECIAL = [
    "Anio",
    "Proyecto Especial",
    "Resolucion",
    "CUOF",
    "CUE",
    "SUBCUE",
    "CUI",
    "Establecimiento",
    "Oferta",
    "CEIC",
    "Cargo",
    "Cantidad",
    "Unidad",
    "Puntos Asignados",
    "Total",
    "Total General",
    "Estado POF",
]


def armar_fila_proyecto_especial(columnas, datos):
    """
    Arma una fila visible de Proyecto Especial desde datos ya normalizados.

    - Respeta exactamente las columnas historicas del preview y del Excel.
    - Resuelve cada celda por label visible o por clave logica normalizada.
    - No aplica reglas nuevas ni altera el contenido recibido.
    """
    return [
        datos.get(columna, datos.get(obtener_clave_columna(columna), ""))
        for columna in columnas
    ]


def armar_fila_proyecto_especial_cargo(columnas, cargo, total_general):
    """
    Construye la fila de Proyecto Especial a partir de un cargo real.

    - Reutiliza la misma normalizacion historica usada por Exportacion.
    - Conserva el total general recibido para Detalle y preview.
    - Devuelve la fila con el mismo orden y las mismas celdas visibles actuales.
    """
    return armar_fila_proyecto_especial(
        columnas,
        construir_datos_normalizados_cargo(cargo, total_general),
    )
