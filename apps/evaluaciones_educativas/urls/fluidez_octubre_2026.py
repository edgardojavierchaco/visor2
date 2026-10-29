from django.urls import path
from apps.evaluaciones_educativas.views import fluidez_octubre_2026

app_name = "fluidez_octubre_2026"

urlpatterns = [
    # Carga de exámenes (tabuladores). <grado> es la clave de GRADOS_URL ('2' / '3').
    path('examenes/',                                 fluidez_octubre_2026.lista,        name='lista'),
    path('examenes/lista_examen/',                    fluidez_octubre_2026.lista_examen, name='lista_examen'),
    path('examenes/lista_examen/<str:fid_actual>/',   fluidez_octubre_2026.lista_examen, name='lista_examen_fid'),
    path('examenes/evaluacion/<str:fid_actual>/<str:cueanexo>/<str:grado>/<int:id_persona>/',
         fluidez_octubre_2026.evaluacion, name='evaluacion'),
    path('examenes/completar_carga/<str:cueanexo>/<str:grado>/', fluidez_octubre_2026.completar_carga, name='completar_carga'),
    path('examenes/excel/<str:cueanexo>/<str:grado>/',           fluidez_octubre_2026.descargar_excel, name='excel'),
    # Va último dentro de examenes/ para no tapar los paths anteriores.
    path('examenes/<str:fid_actual>/',                fluidez_octubre_2026.lista,        name='lista_fid'),

    path('tabuladores/',        fluidez_octubre_2026.gestion_tabuladores, name='gestion_tabuladores'),
    path('tabuladores/cargar/', fluidez_octubre_2026.carga_tabulador,     name='carga_tabulador'),
    path('tabuladores/<str:cuil_tabulador>/asignar/', fluidez_octubre_2026.asignacion_tabulador, name='asignacion_tabulador'),
    path('tabuladores/<str:cuil_tabulador>/eliminar/', fluidez_octubre_2026.eliminar_tabulador, name='eliminar_tabulador'),

    # Aplicadores
    path('aplicadores/',                     fluidez_octubre_2026.gestion_aplicadores, name='gestion_aplicadores'),
    path('aplicadores/cargar/',              fluidez_octubre_2026.carga_aplicador,     name='carga_aplicador'),
    path('aplicadores/buscar_cuil/',         fluidez_octubre_2026.buscar_persona_cuil, name='buscar_persona_cuil'),
    path('aplicadores/<str:cuil_aplicador>/editar/',   fluidez_octubre_2026.carga_aplicador,      name='editar_aplicador'),
    path('aplicadores/<str:cuil_aplicador>/asignar/',  fluidez_octubre_2026.asignacion_aplicador, name='asignacion_aplicador'),
    path('aplicadores/<str:cuil_aplicador>/eliminar/', fluidez_octubre_2026.eliminar_aplicador,   name='eliminar_aplicador'),

    # Excel con tabuladores y aplicadores por sección
    path('personal/excel/', fluidez_octubre_2026.descargar_excel_personal_fluidez_octubre, name='descargar_excel_personal'),
]
