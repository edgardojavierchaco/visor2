from django.urls import path
from apps.evaluaciones_educativas.views import fluidez_octubre_2026

app_name = "fluidez_octubre_2026"

urlpatterns = [
    # path('carga_alumno/<str:fid_actual>/<uuid:grado_public_id>', fluidez_octubre_2026.carga_alumno, name='carga_alumno'),
    # path('editar_alumno/<uuid:alumno_public_id>/<str:fid_actual>/', fluidez_octubre_2026.editar_alumno, name='editar_alumno'),
    # path('carga_evaluacion/<uuid:alumno_public_id>/<str:fid_actual>/', fluidez_octubre_2026.carga_evaluacion, name='carga_evaluacion'),
    # path('editar_evaluacion/<uuid:alumno_public_id>/<str:fid_actual>/', fluidez_octubre_2026.editar_evaluacion, name='editar_evaluacion'),
    # path('actualizar_seccion/<uuid:alumno_public_id>/', fluidez_octubre_2026.actualizar_seccion, name='actualizar_seccion'),
    # path(
    #     "borrar_registro_alumno/<uuid:alumno_public_id>/<str:fid_actual>/",
    #     fluidez_octubre_2026.borrar_registro_alumno,
    #     name="borrar_registro_alumno",
    # ),
    # path('lista_examen', fluidez_octubre_2026.lista_examen, name='lista_examen'),
    # path('lista_examen/<str:fid_actual>/', fluidez_octubre_2026.lista_examen, name='lista_examen_fid'),
    # path("monitoreo/", fluidez_octubre_2026.monitoreo, name="monitoreo"),
    # path("monitoreo_alumno/", fluidez_octubre_2026.monitoreo_alumno, name="monitoreo_alumno"),
    # # Los paths con <str> genérico van al final para no interceptar paths específicos
    # path('', fluidez_octubre_2026.lista, name='lista'),
    # path('<str:fid_actual>/', fluidez_octubre_2026.lista, name='lista_fid'),
    path('tabuladores/',        fluidez_octubre_2026.gestion_tabuladores, name='gestion_tabuladores'),
    path('tabuladores/cargar/', fluidez_octubre_2026.carga_tabulador,     name='carga_tabulador'),
    path('tabuladores/<str:cuil_tabulador>/asignar/', fluidez_octubre_2026.asignacion_tabulador, name='asignacion_tabulador'),
    path('tabuladores/<str:cuil_tabulador>/eliminar/', fluidez_octubre_2026.eliminar_tabulador, name='eliminar_tabulador'),
]
