from config.urls import path
from .views import portada

app_name='dash'

urlpatterns=[
    path('',portada,name='portada'),
]