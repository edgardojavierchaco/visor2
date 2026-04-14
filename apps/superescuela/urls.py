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
    path('super/list_gestor/', SupervisoresListViewGestor.as_view(), name='super_list_gestor'),
    path('super/list_propio/', SupervisoresPersonalListView.as_view(), name='super_list_propio'),
    path('super/add/', SupervisorCreateView.as_view(), name='super_create'),
    path('super/add/propio/', SupervisorPersonalCreateView.as_view(), name='super_create_propio'),
    path('super/update/<int:pk>/', SupervisorUpdateView.as_view(), name='super_update'),
    path('super/update/propio/<int:pk>/', SupervisorPersonalUpdateView.as_view(), name='super_update_propio'),
    path('super/delete/propio/<int:pk>/', SupervisorPersonalDeleteView.as_view(), name='super_delete_propio'),
    # Escuelas Supervisadas
    path('escuelas/list/', EscuelasSupervisadasListView.as_view(), name='escuelas_list'),
    path('escuelas/add/', EscuelasSupervisadasCreateView.as_view(), name='escuelas_create'),
    path('escuelas/update/<int:pk>/', EscuelasSupervisadasUpdateView.as_view(), name='escuelas_update'),
    path('escuelas/delete/<int:pk>/', EscuelasSupervisadasDeleteView.as_view(), name='escuelas_delete'),
    # home
    path('dashboard/', DashboardView.as_view(), name='dashboard'),
    path('dashboard_propio/', DashboardSupervisorView.as_view(), name='dashboard_propio'), 
    path('index/', IndexView.as_view(), name='index'),   
    # Asignaciones
    path('asign/add/', AsignacionCreateView.as_view(), name='asign_create'),
    path('asign/add/propio', AsignacionPersonalCreateView.as_view(), name='asign_create_propio'),
    path('asign/list/', AsignacionListView.as_view(), name='asign_list'),
    path('asign/list/propio/', AsignacionPersonalListView.as_view(), name='asign_list_propio'),
    path('asign/list_gestor/', AsignacionListGestorView.as_view(), name='asign_list_gestor'),
    path('asign/list_func/', AsignacionListFuncView.as_view(), name='asign_list_func'),
    path('asign/delete/<int:pk>/', AsignacionDeleteView.as_view(), name='asign_delete'),
    path('asign/delete/propio/<int:pk>/', AsignacionPersonalDeleteView.as_view(), name='asign_delete_propio'),
    path('asign/update/<int:pk>/', AsignacionUpdateView.as_view(), name='asign_update'),
    path('asign/update/propio/<int:pk>/', AsignacionPersonalUpdateView.as_view(), name='asign_update_propio'),
]