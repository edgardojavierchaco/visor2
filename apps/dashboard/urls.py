from config.urls import path
from .views import portada, directores

app_name='dash'

urlpatterns=[
    path('',portada,name='portada'),
    path('director/',directores, name='director'),
]