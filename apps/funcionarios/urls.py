from config.urls import path, include
from apps.oplectura.views_resultados import tu_vista, cargar_grafico_reg, mostrar_grafico_reg
from apps.oplectura.views_resultadosxloc import *
from apps.oplectura.views_resultadosescxreg import tu_vistacueanexoreg, mostrar_grafico_cueanexoreg, cargar_grafico_cueanexoreg
from .views import DepFuncionarioPortada
from .views_dashboard import *
from .views_supervisor import AsignacionListViewFunc, SupervisoresListViewFunc

app_name='funcionario'

urlpatterns = [    
    path('resultados/', tu_vista, name='resultados'),   
    path('cargar_graficoreg/', cargar_grafico_reg, name='cargar_graficoreg'),    
    path('grafico_reg/', mostrar_grafico_reg, name='grafico_reg'),    
    path('portada_func/', DepFuncionarioPortada, name='portada_func'),    
    path('resultados_loc/', tu_vistaloc, name='resultados_loc'),   
    path('cargar_graficoloc/', mostrar_grafico_localidad, name='cargar_graficoloc'),
    path('grafico_loc/', mostrar_grafico_loc, name='grafico_loc'),
    path('resultados_cueanexo/', tu_vistacueanexoreg, name='resultados_cueanexo'),   
    path('cargar_graficocueanexo/', mostrar_grafico_cueanexoreg, name='cargar_graficocueanexo'),
    path('grafico_cueanexo/', mostrar_grafico_cueanexoreg, name='grafico_cueanexo'),
    path('dashboard/', DashboardView.as_view(), name='dashboard'),
    path('super/list/', SupervisoresListViewFunc.as_view(), name='super_list'), 
    path('asigna/list/', AsignacionListViewFunc.as_view(), name='asigna_list'),
]
