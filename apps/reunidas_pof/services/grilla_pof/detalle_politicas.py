def _columna_detalle(campo, *, origen_actual=None):
    """
    Describe una columna funcional del Detalle sin alterar el render actual.

    - Define el nombre estable que usara la futura grilla operativa.
    - Permite anclarlo al campo normalizado disponible hoy cuando difieren.
    - Mantiene la politica desacoplada de templates, Excel y orden visual actual.
    """
    return {
        "campo": campo,
        "origen_actual": origen_actual or campo,
    }


def _dato_derivado_detalle(campo, *, derivado_desde):
    """
    Declara un dato visual derivado sin reemplazar el dato canonico existente.

    - Conserva el campo tecnico real como fuente de verdad para backend.
    - Expone la representacion visual futura que usara el Detalle agrupado.
    - No modifica filas, columnas ni agrupaciones visibles actuales.
    """
    return {
        "campo": campo,
        "derivado_desde": derivado_desde,
    }


def _accion_detalle(accion, *, alcance, habilitada=False):
    """
    Declara una accion futura del Detalle como metadata no ejecutable.

    - Identifica la accion por un nombre estable para backend y UI futura.
    - Marca si aplica a fila o a grupo para evitar ambiguedades posteriores.
    - Conserva `habilitada=False` mientras la politica no se use en pantalla.
    """
    return {
        "accion": accion,
        "alcance": alcance,
        "habilitada": habilitada,
    }


def obtener_politicas_detalle_reunida():
    """
    Devuelve la politica declarativa del futuro Detalle operativo de Reunida comun.

    - No modifica el render actual ni altera la tabla visible de hoy.
    - Declara que el Detalle evolucionara como vista operativa agrupada.
    - Mantiene a Exportacion como salida oficial y no replica su formato.
    - Conserva `cueanexo` como dato canonico y usa `cue`/`anexo` como derivados visuales.
    """
    return {
        "modo_operativo_futuro": "agrupado",
        "dato_canonico": "cueanexo",
        "datos_derivados_visuales": (
            _dato_derivado_detalle("cue", derivado_desde="cueanexo"),
            _dato_derivado_detalle("anexo", derivado_desde="cueanexo"),
        ),
        "agrupacion_operativa": (
            "cue",
            "cueanexo",
            "cuof",
        ),
        "grupo_cue": {
            "encabezado": (
                _columna_detalle("cue", origen_actual="cueanexo"),
                _columna_detalle("establecimiento", origen_actual="nombre"),
                _columna_detalle("total_anexos"),
                _columna_detalle("total_cargos"),
                _columna_detalle("total_puntos", origen_actual="total"),
            ),
        },
        "grupo_anexo_cuof": {
            "resumen": (
                _columna_detalle("anexo", origen_actual="cueanexo"),
                _columna_detalle("cueanexo"),
                _columna_detalle("cuof"),
                _columna_detalle("oferta_tipo", origen_actual="oferta"),
                _columna_detalle("cantidad_cargos", origen_actual="cantidad"),
                _columna_detalle("acciones_grupo"),
            ),
        },
        "cargo_expandible": {
            "columnas": (
                _columna_detalle("ceic"),
                _columna_detalle("cargo"),
                _columna_detalle("cantidad"),
                _columna_detalle("unidad_cantidad"),
                _columna_detalle("puntos_asignados", origen_actual="puntos"),
                _columna_detalle("total"),
                _columna_detalle("observacion", origen_actual="observacion_cargo"),
                _columna_detalle("estado", origen_actual="estado_pof"),
                _columna_detalle("acciones_fila"),
            ),
        },
        "filtros_permitidos_futuros": (
            "cue",
            "anexo",
            "cueanexo",
            "cuof",
            "ceic",
            "cargo",
            "estado",
            "unidad_cantidad",
        ),
        "orden_permitido_futuro": (
            "cueanexo",
            "cuof",
            "ceic",
            "cargo",
            "cantidad",
            "puntos_asignados",
            "total",
            "estado",
        ),
        "agrupacion_visual_por_defecto": (
            "cue",
            "cueanexo",
            "cuof",
        ),
        "campos_totales_operativos": (
            "total_anexos",
            "total_cargos",
            "total_puntos",
            "total",
        ),
        "acciones_futuras_grupo_cue": (
            _accion_detalle("ver_datos_cue", alcance="grupo"),
        ),
        "acciones_futuras_grupo_anexo_cuof": (
            _accion_detalle("administrar_cargos", alcance="grupo"),
        ),
        "acciones_futuras_fila_cargo": (
            _accion_detalle("editar_cargo", alcance="fila"),
            _accion_detalle("ver_historial_cargo", alcance="fila"),
            _accion_detalle("cambiar_estado", alcance="fila"),
        ),
    }
