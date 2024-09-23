from django.urls import path
from .views import ver_normas
app_name = 'digesto'

urlpatterns = [
    path('norma/', ver_normas, name='norma'),
]