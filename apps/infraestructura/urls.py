from django.urls import path
from .views_datosescuela import DatosEscuelaCreateView, autocompletar_departamento, autocompletar_localidad, listado
from .views_dominio import DominioEscuelaCreateView
from .views_espaciopedagogico import EspacioPedagogicoCreateView
from .views_sanitarios import SanitariosCreateView

app_name='infraestructura'

urlpatterns = [
    path('datos_escuela/', DatosEscuelaCreateView.as_view(), name='datos_escuela'),
    path('autocompletar_localidad/', autocompletar_localidad.as_view(), name='autocompletar_localidad'),
    path('autocompletar_departamento/', autocompletar_departamento.as_view(), name='autocompletar_departamento'),
    path('datos_escuela_exito/', listado, name='datos_escuela_exito'),
    path('dominio_escuela/', DominioEscuelaCreateView.as_view(), name='dominio_escuela'),
    path('espa_ped/', EspacioPedagogicoCreateView.as_view(), name='espa_ped'),
    path('sanitarios/', SanitariosCreateView.as_view(), name='sanitarios'),
]
