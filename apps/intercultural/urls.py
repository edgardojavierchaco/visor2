from django.urls import path
from .views import buscar_escuelas, cargar_alumno_bilingue, filtrar_cursos
from .views import AlumnosBilingueCreateView, AlumnosBilingueCreateView2, AlumnosBilingueUpdateView, AlumnosBilingueDeleteView, AlumnosBilingueListView, AlumnosBilingueListView2, AlumnosBilingueUpdateView2, AlumnosBilingueDeleteView2
from .views_dashboard import DashboardView, DashboardComunView, DashboardFuncView, DashboardRegView
from .views_func import VistaAlumnosBilingueListView, VistaAlumnosBilingueListView2
from .views_index import IndexView
from .views_reg import VistaAlumnosBilingueListRegView, VistaAlumnosBilingueListRegView2

app_name='intercultural'

urlpatterns = [
    path('buscar_escuelas/', buscar_escuelas, name='buscar_escuelas'),
    path('cargar-alumno/', cargar_alumno_bilingue, name='cargar_alumno_bilingue'),
    path('filtrar_cursos/', filtrar_cursos, name='filtrar_cursos'),
    # Alumnos Bilingües
    path('alumnos/list/', AlumnosBilingueListView.as_view(), name='alumnos_list'),
    path('alumnos/list_comun/', AlumnosBilingueListView2.as_view(), name='alumnos_list_comun'),
    path('alumnos/add/', AlumnosBilingueCreateView.as_view(), name='alumnos_create'),
    path('alumnos/add_comun/', AlumnosBilingueCreateView2.as_view(), name='alumnos_create_comun'),
    path('alumnos/update/<int:pk>/', AlumnosBilingueUpdateView.as_view(), name='alumnos_update'),
    path('alumnos/update_comun/<int:pk>/', AlumnosBilingueUpdateView2.as_view(), name='alumnos_update_comun'),
    path('alumnos/delete/<int:pk>/', AlumnosBilingueDeleteView.as_view(), name='alumnos_delete'),
    path('alumnos/delete_comun/<int:pk>/', AlumnosBilingueDeleteView2.as_view(), name='alumnos_delete_comun'),
    path('alumnos/list_func/', VistaAlumnosBilingueListView.as_view(), name='alumnos_list_func'),
    path('alumnos/list_func_cue/<str:cueanexo>/', VistaAlumnosBilingueListView2.as_view(), name='alumnos_list_func_cue'),
    path('alumnos/list_reg/', VistaAlumnosBilingueListRegView.as_view(), name='alumnos_list_reg'),
    path('alumnos/list_reg_cue/<str:cueanexo>/', VistaAlumnosBilingueListRegView2.as_view(), name='alumnos_list_reg_cue'),
    # home
    path('dashboard/', DashboardView.as_view(), name='dashboard'),
    path('dashboard_comun/', DashboardComunView.as_view(), name='dashboard_comun'),
    path('dashboard_func/', DashboardFuncView.as_view(), name='dashboard_func'), 
    path('dashboard_reg/', DashboardRegView.as_view(), name='dashboard_reg'), 
    path('index/', IndexView.as_view(), name='index'),   
]



