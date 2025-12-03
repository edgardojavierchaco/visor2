from django.urls import path
from . import views
# from django.contrib.auth.views import LogoutView

app_name='evaluaciones_educativas'

urlpatterns = [
	path('carga_alumno/<uuid:grado_public_id>',views.carga_alumno, name= 'carga_alumno'),
    path('editar_alumno/<uuid:alumno_public_id>/',views.editar_alumno, name= 'editar_alumno'),
	path('carga_evaluacion/<uuid:alumno_public_id>/',views.carga_evaluacion, name= 'carga_evaluacion'),
	path('editar_evaluacion/<uuid:alumno_public_id>/',views.editar_evaluacion, name= 'editar_evaluacion'),
    path('',views.grado, name='grados'),
	path('lista/<uuid:grado_public_id>/',views.lista, name='lista'),
    path('lista_grado/<str:grado>',views.lista_grado, name='lista_grado'),
	path('asistencia/<uuid:alumno_public_id>/',views.asistencia, name='asistencia'),
	path('editar_asistencia/<uuid:alumno_public_id>/',views.editar_asistencia, name='editar_asistencia'),
    path('borrar_registro_alumno/<uuid:alumno_public_id>/',views.borrar_registro_alumno, name='borrar_registro_alumno'),
	# path('monitoreo/',views.monitoreo, name='monitoreo'),
    # path('salir/',views.salir, name='salir')
	
]
