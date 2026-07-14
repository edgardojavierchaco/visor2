from django.urls import path
from apps.evaluaciones_educativas.views import fluidez_2026

app_name = 'fluidez_2026' 

urlpatterns = [
	#path('',fluidez_2026.inicio, name= 'inicio'),
    path('carga_alumno/<str:fid_actual>/<uuid:grado_public_id>',fluidez_2026.carga_alumno, name= 'carga_alumno'),
    path('editar_alumno/<uuid:alumno_public_id>/<str:fid_actual>/',fluidez_2026.editar_alumno, name= 'editar_alumno'),
	path('carga_evaluacion/<uuid:alumno_public_id>/<str:fid_actual>/',fluidez_2026.carga_evaluacion, name= 'carga_evaluacion'),
	path('editar_evaluacion/<uuid:alumno_public_id>/<str:fid_actual>/',fluidez_2026.editar_evaluacion, name= 'editar_evaluacion'),
    # path('',fluidez_2026.grado, name='grados'),
	#path('<str:fid_actual>/',fluidez_2026.lista, name='lista'),
    #path('',fluidez_2026.lista, name='lista'),
    #path('lista_examen',fluidez_2026.lista_examen, name='lista_examen'),
    #path('lista_examen/<str:fid_actual>/',fluidez_2026.lista_examen, name='lista_examen'),
    path('actualizar_seccion/<uuid:alumno_public_id>/', fluidez_2026.actualizar_seccion, name='actualizar_seccion'),
    path('analisis_evaluacion/',fluidez_2026.analisis_evaluaciones_junio_2026, name='analisis_evaluacion'),
    path('analisis_evaluacion_junio_2026/',fluidez_2026.analisis_evaluaciones_regional_junio_2026, name='analisis_evaluacion_junio_2026'),
    path('analisis_completo_evaluacion_junio_2026/',fluidez_2026.analisis_evaluaciones_ministros_junio_2026, name='analisis_completo_evaluacion_junio_2026'),
	
]