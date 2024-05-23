from config.urls import path
from apps.oplectura.views import *

app_name='oplectura'

urlpatterns=[    
    path('cargar/',DocenteCreateView.as_view(),name='cargar'),
    path('listado/',DocentesListView.as_view(),name='listado'),
    path('editar/',DocentesUpdateView.as_view(),name='editar'),
    path('eliminar/',DocentesDeleteView.as_view(),name='eliminar') 
    ]