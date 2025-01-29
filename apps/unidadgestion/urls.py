from django.urls import path
from .views_pers_doc_central import *
from .views_pers_no_doc_central import *
from .views_dashboard import *


app_name = 'unidadgestion'

urlpatterns = [    
    # Personal docente
    path('ug/list/', UGListView.as_view(), name='ug_list'),
    path('ug/add/', UGCreateView.as_view(), name='ug_create'),
    path('ug/update/<int:pk>/', UGUpdateView.as_view(), name='ug_update'),
    path('ug/delete/<int:pk>/', UGDeleteView.as_view(), name='ug_delete'), 
    path('cargar_cargos/', cargar_cargos, name='cargar_cargos'),       
    # Personal no docente
    path('ug/list_admin/', UGListViewAdmin.as_view(), name='ug_list_admin'),
    path('ug/add_admin/', UGCreateViewAdmin.as_view(), name='ug_create_admin'),
    path('ug/update_admin/<int:pk>/', UGUpdateViewAdmin.as_view(), name='ug_update_admin'),
    path('ug/delete_admin/<int:pk>/', UGDeleteViewAdmin.as_view(), name='ug_delete_admin'), 
    # Home
    path('dashboard/', DashboardView.as_view(), name='dashboard'),
]