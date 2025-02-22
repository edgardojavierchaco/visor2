from django.urls import path
from .views_asingacion import *
from .views_escuelasupervisada import *
from .views_supervisor import *
from .views_dashboard import *
from .views_index import IndexView

app_name = 'superescuela'

urlpatterns = [    
    # Supervisores
    path('super/list/', SupervisoresListView.as_view(), name='super_list'),
    path('super/add/', SupervisorCreateView.as_view(), name='super_create'),
    path('super/update/<int:pk>/', SupervisorUpdateView.as_view(), name='super_update'),
    path('super/delete/<int:pk>/', SupervisorDeleteView.as_view(), name='super_delete'),
    # Escuelas Supervisadas
    path('escuelas/list/', EscuelasSupervisadasListView.as_view(), name='escuelas_list'),
    path('escuelas/add/', EscuelasSupervisadasCreateView.as_view(), name='escuelas_create'),
    path('escuelas/update/<int:pk>/', EscuelasSupervisadasUpdateView.as_view(), name='escuelas_update'),
    path('escuelas/delete/<int:pk>/', EscuelasSupervisadasDeleteView.as_view(), name='escuelas_delete'),
    # home
    path('dashboard/', DashboardView.as_view(), name='dashboard'), 
    path('index/', IndexView.as_view(), name='index'),   
    # Asignaciones
    path('asign/add/', AsignacionCreateView.as_view(), name='asign_create'),
    path('asign/list/', AsignacionListView.as_view(), name='asign_list'),
    path('asign/list_gestor/', AsignacionListGestorView.as_view(), name='asign_list_gestor'),
    path('asign/list_func/', AsignacionListFuncView.as_view(), name='asign_list_func'),
    path('asign/delete/<int:pk>/', AsignacionDeleteView.as_view(), name='asign_delete'),
    path('asign/update/<int:pk>/', AsignacionUpdateView.as_view(), name='asign_update'),
]