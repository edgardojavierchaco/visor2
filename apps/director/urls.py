from django.urls import path
from .views import tu_vista

app_name='director'

urlpatterns=[
    path('matricula/',tu_vista,name='matricula'),
    ]