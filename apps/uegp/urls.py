from django.urls import path
from .views_pers_doc_uegp import *
from .views_pers_no_doc_uegp import *
from .views_dashboard import *


app_name = 'privada'

urlpatterns = [    
    # Personal docente
    path('uegp/list/', UEGPListView.as_view(), name='uegp_list'),
    path('uegp/add/', UEGPCreateView.as_view(), name='uegp_create'),
    path('uegp/update/<int:pk>/', UEGPUpdateView.as_view(), name='uegp_update'),
    path('uegp/delete/<int:pk>/', UEGPDeleteView.as_view(), name='uegp_delete'), 
    path('cargar_cargos/', cargar_cargos, name='cargar_cargos'),       
    # Personal no docente
    path('uegp/list_admin/', UEGPListViewAdmin.as_view(), name='uegp_list_admin'),
    path('uegp/add_admin/', UEGPCreateViewAdmin.as_view(), name='uegp_create_admin'),
    path('uegp/update_admin/<int:pk>/', UEGPUpdateViewAdmin.as_view(), name='uegp_update_admin'),
    path('uegp/delete_admin/<int:pk>/', UEGPDeleteViewAdmin.as_view(), name='uegp_delete_admin'), 
    # Home
    path('dashboard/', DashboardView.as_view(), name='dashboard'),
]