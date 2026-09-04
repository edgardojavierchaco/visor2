from django.urls import path
from . import views, views_ayudas
from .views_list import PersonasListView, PersonaDetailView, exportar_personal
app_name = "bnhpersonas"
urlpatterns = [
    path("", PersonasListView.as_view(), name="inicio"),
    path("personas/", PersonasListView.as_view(), name="personas_list"),
    path("personas/exportar/", exportar_personal, name="exportar_personal"),
    path("personas/vincular/", views.vincular_persona, name="vincular_persona"),
    path("carga-personal/", views.carga_personal, name="carga_personal"),
    path("personas/<int:pk>/carga-personal/", views.carga_personal, name="carga_personal_edit"),
    path("personas/<int:pk>/detalle/", PersonaDetailView.as_view(), name="personas_detail"),
    path("personas/<int:pk>/eliminar/", views.eliminar_persona, name="eliminar_persona"),
    path("personas/<int:persona_id>/actividad/nueva/", views.nueva_actividad, name="nueva_actividad"),
    path("actividad/<int:pk>/editar/", views.editar_actividad, name="editar_actividad"),
    path("actividad/<int:pk>/<str:accion>/", views.accion_actividad, name="accion_actividad"),
    path("horario/<int:actividad_id>/agregar/", views.agregar_horario, name="horario_agregar"),
    path("horario/<int:pk>/eliminar/", views.eliminar_horario, name="eliminar_horario"),
    path("horario/<int:actividad_id>/", views.horarios_actividad, name="horarios_actividad"),
    path("buscar-persona/", views.buscar_persona, name="buscar_persona"),
    path("guardar-persona-ajax/", views.guardar_persona_ajax, name="guardar_persona_ajax"),
    path("filtrar-datos-actividad/", views.filtrar_datos_actividad, name="filtrar_datos_actividad"),
    path("filtrar-ceic/", views.filtrar_ceic, name="filtrar_ceic"),
    path("filtrar-grado-anio/", views.filtrar_grado_anio, name="filtrar_grado_anio"),
    path("filtrar-secciones/", views.filtrar_secciones, name="filtrar_secciones"),
    path("filtrar-localidades/", views.filtrar_localidades, name="filtrar_localidades"),
    path("buscar-codigos-area/", views.buscar_codigos_area, name="buscar_codigos_area"),
    path("ayuda-renpe/", views_ayudas.obtener_ayuda_renpe, name="obtener_ayuda_renpe"),
]
