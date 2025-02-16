from django.urls import path
from .views import buscar_escuelas, cargar_alumno_bilingue, filtrar_cursos
from .views import AlumnosBilingueCreateView, AlumnosBilingueUpdateView, AlumnosBilingueDeleteView, AlumnosBilingueListView
from .views_dashboard import DashboardView, DashboardComunView
from .views_index import IndexView

app_name='intercultural'

urlpatterns = [
    path('buscar_escuelas/', buscar_escuelas, name='buscar_escuelas'),
    path('cargar-alumno/', cargar_alumno_bilingue, name='cargar_alumno_bilingue'),
    path('filtrar_cursos/', filtrar_cursos, name='filtrar_cursos'),
    # Alumnos Bilingües
    path('alumnos/list/', AlumnosBilingueListView.as_view(), name='alumnos_list'),
    path('alumnos/add/', AlumnosBilingueCreateView.as_view(), name='alumnos_create'),
    path('alumnos/update/<int:pk>/', AlumnosBilingueUpdateView.as_view(), name='alumnos_update'),
    path('alumnos/delete/<int:pk>/', AlumnosBilingueDeleteView.as_view(), name='alumnos_delete'),
    # home
    path('dashboard/', DashboardView.as_view(), name='dashboard'),
    path('dashboard_comun/', DashboardComunView.as_view(), name='dashboard_comun'), 
    path('index/', IndexView.as_view(), name='index'),   
]



