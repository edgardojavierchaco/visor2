from django.urls import path
from .views import DatosPersonalCenpeCreateView, cargar_localidades, DatosAcademicosCenpeCreateView

app_name='cenpe'

urlpatterns = [
    path('crear/', DatosPersonalCenpeCreateView.as_view(), name='crear_datos_personal_cenpe'),
    path('ajax/cargar-localidades/', cargar_localidades, name='ajax_cargar_localidades'),
    path('academico/', DatosAcademicosCenpeCreateView.as_view(), name='crear_datos_academico_cenpe'),
]


