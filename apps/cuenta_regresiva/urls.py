from django.urls import path
from .views import cuenta_regresiva, cuenta_regresiva_graficos

app_name='countdown'

urlpatterns = [
    path('listado', cuenta_regresiva, name='cuenta_regresival'),
    path('graficos', cuenta_regresiva_graficos, name='cuenta_regresivag'),
]
