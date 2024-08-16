from config.urls import path
from .views import CreateRegDocporSeccionView, ListadoDocentesView, EditarDocentesView, EliminarDocentesView, RegistrarEvaluacionLectora, ListadoEvaluacionLectora, EditarEvaluacionAlumnosView
from .views import EliminarEvaluacionAlumnoView, RegAlumnosFluidezLectoraCreateView

app_name='oplectura'

urlpatterns = [
    path('cargar/',CreateRegDocporSeccionView.as_view(), name='cargar'),
    path('listados/',ListadoDocentesView.as_view(), name='listados'),   
    path('editar/',EditarDocentesView.as_view(), name='editar'), 
    path('eliminar/',EliminarDocentesView.as_view(), name='eliminar'),
    path('registrar/',RegistrarEvaluacionLectora, name='registrar'),
    path('evaluacion/',ListadoEvaluacionLectora.as_view(),name='evaluacion'),
    path('editarevalum/', EditarEvaluacionAlumnosView.as_view(), name='editarevalum'),
    path('eliminareval/', EliminarEvaluacionAlumnoView.as_view(), name='eliminareval'),
    path('regalumn/',RegAlumnosFluidezLectoraCreateView.as_view(), name='regalumn'),
]
