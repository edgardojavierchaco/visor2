from config.urls import path, include
from .views import CreateRegDocporSeccionView, ListadoDocentesView, EditarDocentesView, EliminarDocentesView, RegistrarEvaluacionLectora, ListadoEvaluacionLectora, EditarEvaluacionAlumnosView
from .views import EliminarEvaluacionAlumnoView, RegAlumnosFluidezLectoraCreateView, ListadoAlumnosDirectoresView, EditarAlumnosDirectoresView, EliminarEvaluacionAlumnoDirectoresView
from .views import RegAlumnosFluidezLectoraDirectorCreateView, ListadoEvaluacionLectoraDirectoresView, DepEvaluacionPortada
from .views_resultados import tu_vista, cargar_grafico_reg, mostrar_grafico_reg
from .views import ListadoAplicadoresView, EditarAplicadorView, RegionalPortada, SupervisorPortada, directoresregistrados, mostrar_directores
from .views_aplicdir import ListadoAplicadoresDirView, EditarAplicadorDirView
from .views_evolcarga import grafico_evaluacion_lectora, grafico_aplicador_region
from .views_resultadosxloc import *
from .views_resultadosescxreg import tu_vistacueanexoreg, mostrar_grafico_cueanexoreg, cargar_grafico_cueanexoreg
from .views_resultadosescxreg_func import *
from .views_resultadosxloc_func import * 

app_name='oplectura'

urlpatterns = [
    path('cargar/',CreateRegDocporSeccionView.as_view(), name='cargar'),
    path('listados/',ListadoDocentesView.as_view(), name='listados'),  
    path('listaplic/',ListadoAplicadoresView.as_view(), name='listaplic'), 
    path('listaplicdir/',ListadoAplicadoresDirView.as_view(), name='listaplicdir'),
    path('list_alumnos/',ListadoAlumnosDirectoresView.as_view(), name='listado_alumnos'),
    path('list_directores/',mostrar_directores, name='listado_directores'),
    path('editar/',EditarDocentesView.as_view(), name='editar'), 
    path('editaraplic/',EditarAplicadorView.as_view(), name='editaraplic'),
    path('editaraplicdir/',EditarAplicadorDirView.as_view(), name='editaraplicdir'),
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
    path('portada_regional/', RegionalPortada, name='portada_regional'),
    path('portada_supervisor/', SupervisorPortada, name='portada_supervisor'),
    path('evol_carga/', grafico_evaluacion_lectora, name='evol_carga'),
    path('evol_aplicador/', grafico_aplicador_region, name='evol_aplicador'),
    path('resultados_loc/', tu_vistaloc, name='resultados_loc'),   
    path('cargar_graficoloc/', mostrar_grafico_localidad, name='cargar_graficoloc'),
    path('grafico_loc/', mostrar_grafico_loc, name='grafico_loc'),
    path('resultados_cueanexo/', tu_vistacueanexoreg, name='resultados_cueanexo'),   
    path('cargar_graficocueanexo/', mostrar_grafico_cueanexoreg, name='cargar_graficocueanexo'),
    path('grafico_cueanexo/', mostrar_grafico_cueanexoreg, name='grafico_cueanexo'),
    path('cargar_graficoloc_func/', mostrar_grafico_localidad_func, name='cargar_graficoloc_func'),
    path('grafico_loc_func/', mostrar_grafico_loc_func, name='grafico_loc_func'),
    path('resultados_cueanexo_func/', tu_vistacueanexoreg_func, name='resultados_cueanexo_func'),   
    path('cargar_graficocueanexo_func/', mostrar_grafico_cueanexoreg_func, name='cargar_graficocueanexo_func'),
    path('grafico_cueanexo_func/', mostrar_grafico_cueanexoreg_func, name='grafico_cueanexo_func'),
]
