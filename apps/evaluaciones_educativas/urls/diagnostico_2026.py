from django.urls import path
from ..views import diagnostico_2026

app_name = 'diagnostico_2026' 

urlpatterns = [
	path('inicio', diagnostico_2026.inicio, name='inicio'),
	path('agregar_alumno/', diagnostico_2026.agregar_alumno, name='agregar_alumno'),
	path('editar_alumno/<uuid:alumno_uuid>/', diagnostico_2026.editar_alumno, name='editar_alumno'),
	path('actualizar_seccion/<uuid:alumno_uuid>/', diagnostico_2026.actualizar_seccion, name='actualizar_seccion'),
	path('cargar_examen/<uuid:alumno_uuid>/<str:materia>/', diagnostico_2026.cargar_examen, name='cargar_examen'),
	path('editar_examen/<uuid:alumno_uuid>/<str:materia>/', diagnostico_2026.editar_examen, name='editar_examen'),
	path('descargar_examen/<uuid:alumno_uuid>/<str:materia>/', diagnostico_2026.descargar_examen_pdf, name='descargar_examen'),
]