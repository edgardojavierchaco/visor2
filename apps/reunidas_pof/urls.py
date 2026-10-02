from django.urls import path
from . import views

app_name = "reunidas_pof"

urlpatterns = [
    #Pantalla Principal
    path("", views.inicio, name= "inicio"),


    #Apartados principales
    path("reunida/cargar/", views.cargar_cargos, name="cargar_cargos"),
    path("cargar/", views.cargar_cargos, name="cargar_cargos_legacy"),
    path("reunidas/", views.reunidas_pof, name="reunidas_pof"),
    path("reunidas/crear/", views.crear_reunida, name="crear_reunida"),
    path("reunidas/<int:pk>/eliminar/", views.eliminar_reunida, name="eliminar_reunida"),
    path("proyectos-especiales/", views.proyectos_especiales_pof, name="proyectos_especiales_pof"),
    path("proyectos-especiales/crear/", views.crear_proyecto_especial, name="crear_proyecto_especial"),
    path("proyectos-especiales/cargar/", views.cargar_cargos_proyecto_especial, name="cargar_cargos_proyecto_especial"),
    path("proyectos-especiales/<int:pk>/editar/", views.editar_proyecto_especial, name="editar_proyecto_especial"),
    path("proyectos-especiales/<int:pk>/eliminar/", views.eliminar_proyecto_especial, name="eliminar_proyecto_especial"),
    path("consultar/", views.consultar_cargos, name = "consultar_cargos"),
    path("anexo-pof/", views.administrar_anexo_pof, name="administrar_anexo_pof"),
    path("visualizacion-cargos-localizacion/", views.visualizacion_cargos_localizacion, name="visualizacion_cargos_localizacion"),
    path("visualizacion-cargos-localizacion/datos/", views.visualizacion_cargos_localizacion_datos, name="visualizacion_cargos_localizacion_datos"),
    path("visualizacion-cargos-localizacion/filtros/", views.visualizacion_cargos_localizacion_filtros, name="visualizacion_cargos_localizacion_filtros"),
    path("visualizacion-cargos-localizacion/exportar-filtros/", views.visualizacion_cargos_localizacion_exportar_filtros, name="visualizacion_cargos_localizacion_exportar_filtros"),
    path("visualizacion-cargos-localizacion/exportar-todo/", views.visualizacion_cargos_localizacion_exportar_todo, name="visualizacion_cargos_localizacion_exportar_todo"),
    path("exportar/", views.exportar_reunida, name = "exportar_reunida"),
    path("historial/", views.historial_movimientos, name = "historial_movimientos"),
    path("reunidas/detalle/", views.detalle_reunida, name="detalle_reunida"),
    path("reunidas/detalle/opciones-filtro/", views.detalle_reunida_opciones_filtro, name="detalle_reunida_opciones_filtro"),

    # Acciones internas / futuras consultas dinámicas
    path("validar-reunida/", views.validar_reunida, name="validar_reunida"),
    path("reunidas/previsualizar-base/", views.previsualizar_reunida_base, name="previsualizar_reunida_base"),
    path("buscar-padron/", views.buscar_padron, name="buscar_padron"),
    path("proyectos-especiales/buscar-padron/", views.buscar_padron_proyecto_especial, name="buscar_padron_proyecto_especial"),
    path("proyectos-especiales/catalogos-ingreso-manual/", views.catalogos_ingreso_manual_proyecto_especial, name="catalogos_ingreso_manual_proyecto_especial"),
    path("proyectos-especiales/buscar-cuof-manual/", views.buscar_cuof_manual_proyecto_especial, name="buscar_cuof_manual_proyecto_especial"),
    path("proyectos-especiales/buscar-ceic/", views.buscar_ceic_proyecto_especial, name="buscar_ceic_proyecto_especial"),
    path("proyectos-especiales/catalogo-ceic/", views.catalogo_ceic_proyecto_especial, name="catalogo_ceic_proyecto_especial"),
    path("proyectos-especiales/guardar-carga/", views.guardar_carga_proyecto_especial, name="guardar_carga_proyecto_especial"),
    path("buscar-ceic/", views.buscar_ceic, name="buscar_ceic"),
    path("catalogo-ceic/", views.catalogo_ceic, name="catalogo_ceic"),
    path("guardar-carga-pof/", views.guardar_carga_pof, name="guardar_carga_pof"),
    # Administración Anexo POF
    path("anexo-pof/catalogo/", views.anexo_pof_catalogo, name="anexo_pof_catalogo"),
    path("anexo-pof/catalogo/crear/", views.crear_anexo_pof_catalogo, name="crear_anexo_pof_catalogo"),
    path("anexo-pof/catalogo/<int:catalogo_id>/desactivar/", views.desactivar_anexo_pof_catalogo, name="desactivar_anexo_pof_catalogo"),
    path("anexo-pof/catalogo/<int:catalogo_id>/reactivar/", views.reactivar_anexo_pof_catalogo, name="reactivar_anexo_pof_catalogo"),
    path("anexo-pof/catalogo/<int:catalogo_id>/historial/", views.historial_catalogo_anexo_pof, name="historial_catalogo_anexo_pof"),
    path("anexo-pof/asociaciones/", views.anexo_pof_asociaciones, name="anexo_pof_asociaciones"),
    path("anexo-pof/asociaciones/asociar/", views.asociar_anexo_pof, name="asociar_anexo_pof"),
    path("anexo-pof/asociaciones/desactivar/", views.desactivar_asociacion_anexo_pof_view, name="desactivar_asociacion_anexo_pof"),
    path("anexo-pof/asociaciones/reactivar/", views.reactivar_asociacion_anexo_pof_view, name="reactivar_asociacion_anexo_pof"),
    path("anexo-pof/asociaciones/historial/", views.historial_asociaciones_anexo_pof, name="historial_asociaciones_anexo_pof"),

    path("zona-educativa/catalogo/", views.zona_educativa_catalogo, name="zona_educativa_catalogo"),
    path("zona-educativa/vigente/", views.zona_educativa_vigente, name="zona_educativa_vigente"),
    path("localizaciones/<int:localizacion_id>/zona-educativa/cambiar/", views.cambiar_zona_educativa, name="cambiar_zona_educativa"),
    path("localizaciones/<int:localizacion_id>/zona-educativa/historial/", views.historial_zona_educativa, name="historial_zona_educativa"),
    path("localizaciones/<int:localizacion_id>/historial-cargos/", views.historial_localizacion_cargos_pof, name="historial_localizacion_cargos_pof"),
    path("movimientos/<int:movimiento_id>/detalle/", views.detalle_movimiento_pof, name="detalle_movimiento_pof"),
    path("cargos/<int:cargo_id>/historial/", views.historial_completo_cargo_pof, name="historial_completo_cargo_pof"),
    path("cargos/historial-cantidad/", views.historial_cantidad_cargos_pof, name="historial_cantidad_cargos_pof"),
    path("cargos/historial-observacion/", views.historial_observacion_cargos_pof, name="historial_observacion_cargos_pof"),
    path("cargos/historial-estado/",views.historial_estado_cargos_pof,name="historial_estado_cargos_pof",),
    path("reunidas/<int:reunida_id>/detalle/grupo-cargos/", views.detalle_reunida_grupo_cargos, name="detalle_reunida_grupo_cargos"),
    path("proyectos-especiales/<int:proyecto_especial_id>/detalle/localizaciones/<int:localizacion_id>/cargos/", views.detalle_proyecto_especial_localizacion_cargos, name="detalle_proyecto_especial_localizacion_cargos"),
    path("cargos/<int:cargo_id>/detalle/", views.detalle_cargo_pof, name="detalle_cargo_pof"),
    path("cargos/<int:cargo_id>/ofertas/", views.catalogo_ofertas_cargo_pof, name="catalogo_ofertas_cargo_pof"),
    path("cargos/<int:cargo_id>/modificar/", views.modificar_cargo_pof_view, name="modificar_cargo_pof"),
    path("cargos/<int:cargo_id>/estado/", views.cambiar_estado_cargo_pof_view, name="cambiar_estado_cargo_pof"),
    path("cargos/<int:cargo_id>/eliminar/", views.eliminar_cargo_pof_view, name="eliminar_cargo_pof"),


    #Pantallas que ordenan el flujo de Cargos
    path("cargos/", views.cargos_pof, name="cargos_pof"),
]
