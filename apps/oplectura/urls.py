from config.urls import path, include
from .views import CreateRegDocporSeccionView, ListadoDocentesView, EditarDocentesView, EliminarDocentesView, RegistrarEvaluacionLectora, ListadoEvaluacionLectora, EditarEvaluacionAlumnosView
from .views import EliminarEvaluacionAlumnoView, RegAlumnosFluidezLectoraCreateView, ListadoAlumnosDirectoresView, EditarAlumnosDirectoresView, EliminarEvaluacionAlumnoDirectoresView
from .views import RegAlumnosFluidezLectoraDirectorCreateView, ListadoEvaluacionLectoraDirectoresView, DepEvaluacionPortada
from .views_resultados import tu_vista, cargar_grafico_reg, mostrar_grafico_reg

app_name='oplectura'

urlpatterns = [
    path('cargar/',CreateRegDocporSeccionView.as_view(), name='cargar'),
    path('listados/',ListadoDocentesView.as_view(), name='listados'),  
    path('list_alumnos/',ListadoAlumnosDirectoresView.as_view(), name='listado_alumnos'),
    path('editar/',EditarDocentesView.as_view(), name='editar'), 
    path('eliminar/',EliminarDocentesView.as_view(), name='eliminar'),
    path('registrar/',RegistrarEvaluacionLectora, name='registrar'),
    path('evaluacion/',ListadoEvaluacionLectora.as_view(),name='evaluacion'),
    path('evaluacion_directores/',ListadoEvaluacionLectoraDirectoresView.as_view(),name='evaluacion_directores'),
    path('editarevalum/', EditarEvaluacionAlumnosView.as_view(), name='editarevalum'),
    path('editarevalumdir/', EditarAlumnosDirectoresView.as_view(), name='editarevalumdir'),
    path('eliminareval/', EliminarEvaluacionAlumnoView.as_view(), name='eliminareval'),
    path('eliminaralumdir/', EliminarEvaluacionAlumnoDirectoresView.as_view(), name='eliminaralumdir'),
    path('regalumn/',RegAlumnosFluidezLectoraCreateView.as_view(), name='regalumn'),
    path('regalumndir/',RegAlumnosFluidezLectoraDirectorCreateView.as_view(), name='regalumndir'),
    path('resultados/', tu_vista, name='resultados'),   
    path('cargar_graficoreg/', cargar_grafico_reg, name='cargar_graficoreg'),    
    path('grafico_reg/', mostrar_grafico_reg, name='grafico_reg'),    
    path('portada_eval/', DepEvaluacionPortada, name='portada_eval'),
]
