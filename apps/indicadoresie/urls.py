from django.urls import path
from .views_dash import (
    DashboardSeguimientoSIE2025View,
    seguimiento_sie_json,
    seguimiento_sie_niveles_json
)
from .views_analisis_sge_ra import (
    ComparativaSgeRaView,
    comparativa_sge_ra_json,
    actualizar_fecha_comparativa_sge_ra,
    progreso_actualizar_fecha_comparativa_sge_ra,
    estado_fecha_comparativa_sge_ra,
)
from .views import (
    InicioSGEView,
    SeguimientoSIE2025ListView, 
    InformeSGEListView, 
    dashboard_prueba, 
    dashboard_prueba_superv, 
    dashboard_prueba_func, 
    dashboard_prueba_regional,
    dashboard_prueba_fluidez,
    dashboard_prueba_fluidez_regional,
    dashboard_prueba_fluidez_func,
    dashboard_prueba_matematica,
    dashboard_prueba_matematica_regional,
    dashboard_prueba_matematica_func,
    actualizar_fecha_sge,
)

# Conectar el archivo de regionales
from .views_regionales import (
    PadronRegionalListView,
    get_jerarquia_oficial_padron  # Importamos la nueva función del mapa oficial
)

# Mantenemos 'indicsie' para evitar el error NoReverseMatch en otros módulos
app_name = 'indicsie'

urlpatterns = [
    # --- VISTAS DE SEGUIMIENTO ---
    path('seguimiento/', InicioSGEView.as_view(), name='seguimiento'),
    path('seguimiento/listado/', InformeSGEListView.as_view(), name='seguimiento_listado'),
    path('seguimiento/comparativa-ra/', ComparativaSgeRaView.as_view(), name='comparativa_sge_ra'),
    path(
        'seguimiento/comparativa-ra/fecha/estado/',
        estado_fecha_comparativa_sge_ra,
        name='estado_fecha_comparativa_sge_ra',
    ),
    path(
        'seguimiento/comparativa-ra/actualizar-fecha/',
        actualizar_fecha_comparativa_sge_ra,
        name='actualizar_fecha_comparativa_sge_ra',
    ),
    path(
        'seguimiento/comparativa-ra/actualizar-fecha/progreso/<uuid:job_id>/',
        progreso_actualizar_fecha_comparativa_sge_ra,
        name='progreso_actualizar_fecha_comparativa_sge_ra',
    ),
    path('seguimiento/alumnos/', SeguimientoSIE2025ListView.as_view(), name='seguimiento_alumnos'),
    
    # --- DASHBOARDS Y API ---
    path('dashboard/', DashboardSeguimientoSIE2025View.as_view(), name='dashboard_seguimiento_sie'),
    path('api/seguimiento-sie/', seguimiento_sie_json, name='seguimiento_sie_json'),
    path('api/seguimiento-sie-niveles/', seguimiento_sie_niveles_json, name='seguimiento_sie_niveles_json'),
    path('api/comparativa-sge-ra/', comparativa_sge_ra_json, name='comparativa_sge_ra_json'),
    
    # --- PRUEBAS Y OTROS DASHBOARDS ---
    path('prueba/', dashboard_prueba, name='prueba'),
    path('prueba_superv/', dashboard_prueba_superv, name='prueba_superv'),
    path('prueba_func/', dashboard_prueba_func, name='prueba_func'),
    path('prueba_reg/', dashboard_prueba_regional, name='prueba_regional'),
    path('prueba_fluidez/', dashboard_prueba_fluidez, name='prueba_fluidez'),
    path('prueba_fluidez_regional/', dashboard_prueba_fluidez_regional, name='prueba_fluidez_reg'),
    path('prueba_fluidez_func/', dashboard_prueba_fluidez_func, name='prueba_fluidez_func'),
    path('prueba_matematica/', dashboard_prueba_matematica, name='prueba_matematica'),
    path('prueba_matematica_regional/', dashboard_prueba_matematica_regional, name='prueba_matematica_regional'),
    path('prueba_matematica_func/', dashboard_prueba_matematica_func, name='prueba_matematica_func'),

    # --- RUTAS DE INSTITUCIONES Y PADRÓN ---
    path('seguimiento/padron-regional/', PadronRegionalListView.as_view(), name='padron_regional_list'),
    
    # RUTA NUEVA: El mapa jerárquico oficial que corrige a Maipú y activa Independencia
    path('api/jerarquia-oficial/', get_jerarquia_oficial_padron, name='get_jerarquia_oficial'),
    
    # --- ACTUALIZACIÓN DE DATOS ---
    path('actualizar-fecha-sge/', actualizar_fecha_sge, name='actualizar_fecha_sge'),
]
