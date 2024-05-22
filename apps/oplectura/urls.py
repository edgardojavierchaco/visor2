from config.urls import path
from apps.oplectura.views import *

app_name='oplectura'

urlpatterns=[    
    path('cargar/',DocenteCreateView.as_view(),name='cargar'),
    path('listado/',DocentesListView.as_view(),name='listado'),
    ]