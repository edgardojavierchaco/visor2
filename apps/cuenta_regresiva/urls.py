from django.urls import path
from .views import cuenta_regresiva

app_name='countdown'

urlpatterns = [
    path('', cuenta_regresiva, name='cuenta_regresiva'),
]
