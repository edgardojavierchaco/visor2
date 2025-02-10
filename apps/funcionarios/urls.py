from config.urls import path, include
from apps.oplectura.views_resultados import tu_vista, cargar_grafico_reg, mostrar_grafico_reg
from apps.oplectura.views_resultadosxloc import *
from apps.oplectura.views_resultadosescxreg import tu_vistacueanexoreg, mostrar_grafico_cueanexoreg, cargar_grafico_cueanexoreg
from .views import DepFuncionarioPortada
from .views_dashboard import *
from .views_supervisor import AsignacionListViewFunc, SupervisoresListViewFunc
from apps.oplectura.views_resultadosescxreg_func import *
from apps.oplectura.views_resultadosxloc_func import *
from apps.oplectura.views_resultados_func import *

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
    path('resultados_func/', tu_vista_func, name='resultados_func'),   
    path('cargar_graficoreg_func/', cargar_grafico_reg_func, name='cargar_graficoreg_func'),    
    path('grafico_reg_func/', mostrar_grafico_reg_func, name='grafico_reg_func'), 
    path('resultados_loc_func/', tu_vistaloc_func, name='resultados_loc_func'),   
    path('cargar_graficoloc_func/', mostrar_grafico_localidad_func, name='cargar_graficoloc_func'),
    path('grafico_loc_func/', mostrar_grafico_loc_func, name='grafico_loc_func'),
    path('resultados_cueanexo_func/', tu_vistacueanexoreg_func, name='resultados_cueanexo_func'),   
    path('cargar_graficocueanexo_func/', mostrar_grafico_cueanexoreg_func, name='cargar_graficocueanexo_func'),
    path('grafico_cueanexo_func/', mostrar_grafico_cueanexoreg_func, name='grafico_cueanexo_func'),
]
