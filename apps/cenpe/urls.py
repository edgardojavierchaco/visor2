from django.urls import path
from .views import DatosPersonalCenpeCreateView, cargar_localidades, DatosAcademicosCenpeCreateView, CargosHorasCenpeCreateView
from .views import obtener_cargos_por_nivel, CargosHorasCenpeListView, EliminarDocentesView, IndexCenpe
from .views_reportes import GenerarCertificado

app_name='cenpe'

urlpatterns = [
    path('',IndexCenpe,name='index'),
    path('crear/', DatosPersonalCenpeCreateView.as_view(), name='crear'),
    path('cargar_localidades/', cargar_localidades, name='cargar_localidades'),
    path('academico/', DatosAcademicosCenpeCreateView.as_view(), name='academico'),
    path('cargo_horas/',CargosHorasCenpeCreateView.as_view(),name='cargo_horas'),
    path('listado/',CargosHorasCenpeListView.as_view(),name='listado'),
    path('obtener-cargos-por-nivel/', obtener_cargos_por_nivel, name='obtener_cargos_por_nivel'),
    path('eliminar/',EliminarDocentesView.as_view(),name='eliminar'),
    path('generar-pdf/', GenerarCertificado, name='generar_pdf'),
]


