from django.urls import path
from ..views import diagnostico_2026

app_name = 'diagnostico_2026' 

urlpatterns = [
	path('inicio', diagnostico_2026.inicio, name='inicio'),
	path('agregar_alumno/', diagnostico_2026.agregar_alumno, name='agregar_alumno'),
	path('editar_alumno/<uuid:alumno_uuid>/', diagnostico_2026.editar_alumno, name='editar_alumno'),
	path('actualizar_seccion/<uuid:alumno_uuid>/', diagnostico_2026.actualizar_seccion, name='actualizar_seccion'),
	path('realizar_carga/', diagnostico_2026.realizar_carga, name='realizar_carga'),
	path('examenes/<str:materia>/', diagnostico_2026.examenes_lista, name='examenes_lista'),
	path('cargar_examen/<uuid:alumno_uuid>/<str:materia>/', diagnostico_2026.cargar_examen, name='cargar_examen'),
	path('editar_examen/<uuid:alumno_uuid>/<str:materia>/', diagnostico_2026.editar_examen, name='editar_examen'),
	path('eliminar_examen/<uuid:alumno_uuid>/<str:materia>/', diagnostico_2026.eliminar_examen, name='eliminar_examen'),
	path('descargar_examenes/<str:materia>/', diagnostico_2026.descargar_examenes, name='descargar_examenes'),
    #path('monitoreo_diagnostico/', diagnostico_2026.monitoreo_evaluaciones_educativas, name='monitoreo_diagnostico')
  path('analisis_evaluacion/', diagnostico_2026.analisis_evaluacion, name='analisis_evaluacion'),
  path('progreso_alumnos/', diagnostico_2026.progreso_alumnos, name='progreso_alumnos'),
  path('descargar-examen-individual/<str:materia>/', diagnostico_2026.descargar_examen_individual, name='descargar_examen_individual'),
  path('descargar-reporte-listado/<str:materia>/', diagnostico_2026.descargar_reporte_listado, name='descargar_reporte_listado'),
]