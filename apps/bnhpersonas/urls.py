from django.urls import path
from .views import (
    filtrar_ceic, 
    filtrar_grado_anio,
    filtrar_secciones,
    carga_personal, 
    buscar_persona, 
    filtrar_localidades, 
    buscar_codigos_area,
    editar_actividad,
    agregar_horario,
    eliminar_horario,
    guardar_persona_ajax,
    filtrar_datos_actividad,
    horarios_actividad
)

from .views_list import (
    PersonasListView,
    PersonaDetailView,
)

from . import views_ayudas

app_name='bnhpersonas'

urlpatterns = [
    # =========================
    # AJAX / UTILIDADES
    # =========================
    path('filtrar-ceic/', filtrar_ceic, name='filtrar_ceic'),
    path('filtrar-localidades/', filtrar_localidades, name='filtrar_localidades'),
    path('buscar-codigos-area/', buscar_codigos_area, name='buscar_codigos_area'),
    path('filtrar-grado-anio/', filtrar_grado_anio, name='filtrar_grado_anio'),
    path('filtrar-secciones/', filtrar_secciones, name='filtrar_secciones'),
    path("buscar-persona/", buscar_persona, name='buscar_persona'),
    

    # =========================
    # PERSONA CORE
    # =========================
    path('carga-personal/', carga_personal, name='carga_personal'),
    path('personas/<int:pk>/carga-personal/',carga_personal, name='carga_personal_edit'),
    path("guardar-persona-ajax/", guardar_persona_ajax, name="guardar_persona_ajax"),
    
    # =========================
    # LISTADO / DETALLE
    # =========================
    path('personas/',PersonasListView.as_view(),name='personas_list'),
    path('personas/<int:pk>/detalle/',PersonaDetailView.as_view(),name='personas_detail'),
    
    # ========================
    # ACTIVIDADES
    ##########################
    path("filtrar-datos-actividad/",filtrar_datos_actividad,name="filtrar_datos_actividad"),
    
    #############################
    # EDITAR ACTIVIDADES
    #############################
    path('actividad/<int:pk>/editar/',editar_actividad,name='editar_actividad'),
    
    #############################
    # HORARIOS ACTIVIDADES
    #############################
    path('horario/<int:actividad_id>/agregar/', agregar_horario,name='horario_agregar'),
    path('horario/<int:pk>/eliminar/', eliminar_horario,name='eliminar_horario'),
    path('horario/<int:actividad_id>/', horarios_actividad, name='horarios_actividad'),
    
    #############################
    # AYUDAS
    #############################
    path('ayuda-renpe/',views_ayudas.obtener_ayuda_renpe,name='obtener_ayuda_renpe'),
    
    
]