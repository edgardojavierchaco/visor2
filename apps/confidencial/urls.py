from apps.confidencial import views_supervisor
from config.urls import path
from apps.confidencial.views_director_matric import *

app_name='confidencial'

urlpatterns=[
    path('selector/',TuVista.as_view(),name='selector'),]