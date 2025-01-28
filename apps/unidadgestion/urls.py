from django.urls import path
from .views_pers_doc_central import *


app_name = 'unidadgestion'

urlpatterns = [    
    # Unidades de Servicio
    path('ug/list/', UGListView.as_view(), name='ug_list'),
    path('ug/add/', UGCreateView.as_view(), name='ug_create'),
    path('ug/update/<int:pk>/', UGUpdateView.as_view(), name='ug_update'),
    path('ug/delete/<int:pk>/', UGDeleteView.as_view(), name='ug_delete'), 
    path('cargar_cargos/', cargar_cargos, name='cargar_cargos'),            
    # Home
    #path('dashboard/', DashboardView.as_view(), name='dashboard'),
]