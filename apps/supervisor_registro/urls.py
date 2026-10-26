from django.urls import path

from .api import (
    catalogos, 
    expediente, 
    ofertas, 
    regiones, 
    regionales, 
    supervisor,
    mapa,
    sin_supervisor,
    observatorio as api_observatorio,
)

from .views import (
    SupervisoresList,
    SupervisorEditar,
    dashboard,
    detalle_supervisor,
    exportar_excel,
)
from .views_ajax import supervisores_datatable
from .views_observatorio import observatorio, mapa_territorial, nomina_supervisores
from . import views_central

app_name = "supervisor_registro"

urlpatterns = [
    path("central/", views_central.inicio, name="central_inicio"),
    path("central/supervisores/", views_central.listado, name="central_listado"),
    path("central/supervisores/nuevo/", views_central.alta_supervisor, name="central_alta"),
    path("central/api/usuario-cuil/", views_central.buscar_usuario_alta, name="central_usuario_cuil"),
    path("central/supervisores/<int:pk>/asignaciones/", views_central.gestor, name="central_gestor"),
    path("central/api/asignacion/<int:sr_id>/", views_central.detalle_asignacion, name="central_asignacion"),
    path("central/api/asignacion/<int:sr_id>/disponibles/", views_central.buscar_disponibles, name="central_disponibles"),
    path("central/api/asignacion/<int:sr_id>/cambios/", views_central.cambios_masivos, name="central_cambios"),
    path("central/supervisores/<int:pk>/regionales/agregar/", views_central.agregar_regional, name="central_agregar_regional"),
    path("central/supervisores/<int:pk>/competencias/agregar/", views_central.agregar_competencia, name="central_agregar_competencia"),
    path("central/supervisores/<int:pk>/competencias/<int:nivel_id>/finalizar/", views_central.finalizar_competencia, name="central_finalizar_competencia"),
    path("central/supervisores/<int:pk>/regionales/<int:sr_id>/finalizar/", views_central.finalizar_regional, name="central_finalizar_regional"),
    path("central/supervisores/<int:pk>/situaciones/agregar/", views_central.crear_situacion, name="central_crear_situacion"),
    path("central/supervisores/<int:pk>/situaciones/<int:situacion_id>/editar/", views_central.editar_situacion, name="central_editar_situacion"),
    path("central/supervisores/<int:pk>/situaciones/<int:situacion_id>/finalizar/", views_central.finalizar_situacion, name="central_finalizar_situacion"),
    path("central/supervisores/<int:pk>/contacto/", views_central.actualizar_contacto, name="central_actualizar_contacto"),
    path("central/calidad/", views_central.calidad, name="central_calidad"),
    path("central/auditoria/", views_central.auditoria, name="central_auditoria"),
    path("central/exportar/", views_central.exportar_asignaciones, name="central_exportar"),
    path("observatorio/", observatorio, name="observatorio"),
    path("observatorio/mapa/", mapa_territorial, name="mapa_territorial"),
    path("observatorio/nomina/", nomina_supervisores, name="nomina_ministerial"),
    path("api/observatorio/sin-supervisor/", sin_supervisor.consultar, name="sin_supervisor"),
    path("api/observatorio/indicadores/", api_observatorio.indicadores, name="observatorio_indicadores"),
    path("", dashboard, name="dashboard"),

    # -----------------------------------------------------
    # Supervisores
    # -----------------------------------------------------
    path("api/supervisores/", supervisor.buscar_supervisor, name="buscar_supervisor"),
    path("api/supervisor/create/", supervisor.crear_supervisor, name="crear_supervisor"),
    path("api/supervisor/update/", supervisor.actualizar_supervisor, name="actualizar_supervisor"),
    path("api/supervisor/delete/", supervisor.eliminar_supervisor, name="eliminar_supervisor"),
    path("api/supervisor/toggle/", supervisor.toggle_supervisor, name="toggle_supervisor"),

    # Compatibilidad con el endpoint anterior.
    path("api/supervisores/listado/", supervisor.listado_supervisores, name="api_listado_supervisores"),

    # -----------------------------------------------------
    # Catálogos
    # -----------------------------------------------------
    path("api/catalogos/situaciones/", catalogos.situaciones, name="catalogo_situaciones"),
    path("api/catalogos/niveles/", catalogos.niveles, name="catalogo_niveles"),
    path("api/regiones-permitidas/", regiones.regiones_permitidas, name="regiones_permitidas"),

    # -----------------------------------------------------
    # Expediente
    # -----------------------------------------------------
    path("api/expediente/<int:supervisor_id>/", expediente.get_expediente, name="get_expediente"),

    path("api/expediente/situacion/add/", expediente.add_situacion, name="add_situacion"),
    path("api/expediente/situacion/delete/<int:pk>/", expediente.delete_situacion, name="delete_situacion"),
    path("api/expediente/situacion/<int:pk>/update/", expediente.update_situacion, name="update_situacion"),

    path("api/expediente/regional/add/", expediente.add_regional, name="add_regional"),
    path("api/expediente/regional/delete/<int:pk>/", expediente.delete_regional, name="delete_regional"),

    path("api/expediente/nivel/add/", expediente.add_nivel, name="add_nivel"),
    path("api/expediente/nivel/delete/", expediente.delete_nivel, name="delete_nivel"),
    path("api/expediente/nivel/<int:pk>/update/", expediente.update_nivel, name="update_nivel"),

    path("api/expediente/oferta/add/", expediente.add_oferta, name="add_oferta"),
    path("api/expediente/oferta/delete/<int:pk>/", expediente.delete_oferta, name="delete_oferta"),
    path("api/expediente/oferta/<int:pk>/update/", expediente.update_oferta, name="update_oferta"),

    # -----------------------------------------------------
    # Ofertas
    # -----------------------------------------------------
    path("api/ofertas/buscar/", ofertas.api_buscar, name="ofertas_buscar"),
    path("api/buscar-cue/", ofertas.buscar_cue, name="buscar_cue"),

    # -----------------------------------------------------
    # Listado HTML + DataTables
    # -----------------------------------------------------
    path("supervisores/", SupervisoresList, name="listado_supervisores"),
    path("api/listado/", supervisores_datatable, name="supervisores_datatable"),

    # -----------------------------------------------------
    # Detalle / edición / exportación
    # -----------------------------------------------------
    path("supervisores/<int:pk>/detalle/", detalle_supervisor, name="detalle"),
    path("supervisores/<int:pk>/editar/", SupervisorEditar, name="editar"),
    path("supervisores/exportar-excel/", exportar_excel, name="exportar_excel"),
    
    # Mapa Escuelas asignadas
    path("api/mapa/supervisores/",mapa.mapa_supervisores,name="mapa_supervisores"),
]