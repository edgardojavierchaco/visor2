from django.urls import path
from .views import guardar_examen, examen_guardado, buscar_alumno_por_dni
from .views_list import ExamenAlumnoCueanexoLenListView
from .views_listmatem import ExamenAlumnoCueanexoMatListView
from .views_matem import guardar_examen_matematica
from .views_grafico import grafico_examen
from .views_grafmat import GraficoMatematicaView
from .views_export import exportar_excel
from .views_dashboard import DashboardView, DashboardFluidezView, DashboardMatemQuintoView, DashboardMatemSegundoAnioView
from .views_export_matem import exportar_excel_matematica_lista
from .views_qr import cerrar_carga
from .views_qrm import cerrar_carga_matem
from .views_listlgral import ExamenAlumnoCueanexoLenGralListView
from .views_lengua import ListadoAlumnosLenguaView

app_name='operative'

urlpatterns = [
    path('lengua/', guardar_examen, name='guardar_examen'),
    path('examen_guardado/', examen_guardado, name='examen_guardado'),  # Una vista de éxito
    path('buscar-alumno/', buscar_alumno_por_dni, name='buscar_alumno'),
    path('listadol/', ExamenAlumnoCueanexoLenListView.as_view(), name='listadol'),
    path('listadomat/', ExamenAlumnoCueanexoMatListView.as_view(), name='listadomat'),
    path('matematica/', guardar_examen_matematica, name='guardar_examen_matematica'),
    path('grafico/', grafico_examen, name='grafico_examen'),
    path('grafico-matematica/', GraficoMatematicaView.as_view(), name='grafico_matematica'),
    path('export/excel/', exportar_excel, name='exportar_excel'),
    path('dashboard/', DashboardView.as_view(), name='dashboard'),
    path('dashboard_fluidez/', DashboardFluidezView.as_view(), name='dashboard_fluidez'),
    path('dashboard_matem_quinto/', DashboardMatemQuintoView.as_view(), name='dashboard_matem_quinto'),
    path('dashboard_matem_segundo_anio/', DashboardMatemSegundoAnioView.as_view(), name='dashboard_matem_segundo_anio'),
    path('exportar_excel_matematica_lista/', exportar_excel_matematica_lista, name='exportar_excel_matematica_lista'),
    path('cerrar_carga/', cerrar_carga, name='cerrar_carga'),
    path('cerrar_carga_m/', cerrar_carga_matem, name='cerrar_carga_m'),
    path('listadolgral/', ExamenAlumnoCueanexoLenGralListView.as_view(), name='listadolgral'),
    path('listalengua/', ListadoAlumnosLenguaView.as_view(), name='listalengua'),
]
