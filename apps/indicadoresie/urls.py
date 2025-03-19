from django.urls import path
from .models import SeguimientoSIE2025, SIESegimiento
from .views import SeguimientoSIE2025ListView

app_name='indicsie'

urlpatterns = [
    path('seguimiento/', SeguimientoSIE2025ListView.as_view(), name='seguimiento'),    
]