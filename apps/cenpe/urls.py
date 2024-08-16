from django.urls import path
from .views import DatosPersonalCenpeCreateView

app_name='cenpe'

urlpatterns = [
    path('crear/', DatosPersonalCenpeCreateView.as_view(), name='crear_datos_personal_cenpe'),
]


