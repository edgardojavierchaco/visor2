from ..exportacion_rows import construir_filas_exportacion, construir_filas_normalizadas
from ..exportacion_schemas import obtener_schema_exportacion
from ..historial_service import (
    enriquecer_filas_con_historial_cantidad,
    enriquecer_filas_con_historial_estado,
    enriquecer_filas_con_historial_observacion,
)
from .detalle_politicas import obtener_politicas_detalle_reunida
from .detalle_rows import construir_grupos_operativos_detalle


def _obtener_labels_columnas(schema):
    return [columna["label"] for columna in schema["columnas"]]


def _obtener_metadata_contexto(contexto, filas_normalizadas):
    """
    Devuelve metadata opcional por contexto sin afectar el render actual.

    - Expone politicas futuras solo cuando la grilla se usa en Detalle.
    - Mantiene `None` en los demas contextos para no cambiar contratos vigentes.
    - Evita acoplar el builder a templates o servicios de nivel superior.
    """
    if contexto == "DETALLE_REUNIDA":
        detalle_politicas = obtener_politicas_detalle_reunida()
        grupos_operativos_detalle = construir_grupos_operativos_detalle(
            filas_normalizadas=filas_normalizadas,
            detalle_politicas=detalle_politicas,
        )
        return {
            "detalle_politicas": detalle_politicas,
            "grupos_operativos_detalle": grupos_operativos_detalle,
            "cantidad_grupos_operativos_detalle": len(grupos_operativos_detalle),
        }
    return {}


def construir_grilla_pof_desde_cargos(
    *,
    cargos,
    nivel_codigo,
    contexto="REUNIDA",
    espejo=True,
    incluir_historial_cantidad=None,
    incluir_historial_observacion=None,
    incluir_historial_estado=False,
):
    """
    Construye una estructura comun de grilla POF a partir de cargos ya obtenidos.

    - Enriquece historial de cantidad cuando el contexto de Detalle lo requiere.
    - Enriquece historial de observación en el contexto de Detalle.
    - Enriquece historial de Estado POF solo cuando el consumidor lo solicita,
      manteniendo esa consulta limitada al conjunto de cargos recibido.
    - No carga el detalle completo del historial; solo marca filas con cambios
      reales para que el frontend habilite el trigger correspondiente.
    """
    schema = obtener_schema_exportacion(nivel_codigo)
    filas_normalizadas = construir_filas_normalizadas(
        cargos,
        nivel_codigo,
        schema=schema,
    )
    if incluir_historial_cantidad is None:
        incluir_historial_cantidad = contexto == "DETALLE_REUNIDA"
    if incluir_historial_cantidad:
        enriquecer_filas_con_historial_cantidad(filas_normalizadas)
    if incluir_historial_observacion is None:
        incluir_historial_observacion = contexto == "DETALLE_REUNIDA"
    if incluir_historial_observacion:
        enriquecer_filas_con_historial_observacion(filas_normalizadas)
    if incluir_historial_estado:
        enriquecer_filas_con_historial_estado(filas_normalizadas)
    filas_render = construir_filas_exportacion(
        schema,
        filas_normalizadas,
        espejo=espejo,
    )

    return {
        "contexto": contexto,
        "nivel_codigo": nivel_codigo,
        "schema": schema,
        "columnas": _obtener_labels_columnas(schema),
        "filas_normalizadas": filas_normalizadas,
        "filas_exportacion": filas_render,
        "filas_render": filas_render,
        "total_filas": len(filas_render),
        **_obtener_metadata_contexto(contexto, filas_normalizadas),
    }
