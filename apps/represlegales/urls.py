from django.urls import path
from .views_asingacion import *
from .views_escuelasrepresentadas import *
from .views_representante import *
from .views_dashboard import *
from .views_index import IndexView

app_name = 'representantes'

urlpatterns = [    
    # Representantes Legales
    path('super/list/', RepresentantesLegalesListView.as_view(), name='super_list'),
    path('super/add/', RepresentantesLegalesCreateView.as_view(), name='super_create'),
    path('super/update/<int:pk>/', RepresentanteLegalUpdateView.as_view(), name='super_update'),
    path('super/delete/<int:pk>/', RepresentanteLegalDeleteView.as_view(), name='super_delete'),
    # Escuelas Representadas
    path('escuelas/list/', EscuelasRepresentadasListView.as_view(), name='escuelas_list'),
    path('escuelas/add/', EscuelasRepresentadasCreateView.as_view(), name='escuelas_create'),
    path('escuelas/update/<int:pk>/', EscuelasRepresentadasUpdateView.as_view(), name='escuelas_update'),
    path('escuelas/delete/<int:pk>/', EscuelasRepresentadasUpdateView.as_view(), name='escuelas_delete'),
    # home
    path('dashboard/', DashboardView.as_view(), name='dashboard'), 
    path('index/', IndexView.as_view(), name='index'),   
    # Asignaciones
    path('asign/add/', AsignacionCreateView.as_view(), name='asign_create'),
    path('asign/list/', AsignacionListView.as_view(), name='asign_list'),
    path('asign/delete/<int:pk>/', AsignacionDeleteView.as_view(), name='asign_delete'),
    path('asign/update/<int:pk>/', AsignacionUpdateView.as_view(), name='asign_update'),
]