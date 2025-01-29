from config.urls import path
from .views import filtrar_tablas_view_directores, filter_matricula_views_directores
from .views_uegp import filter_matricula_views_directores_uegp, filtrar_tablas_view_directores_uegp

app_name='directores'

urlpatterns=[
    path('',filtrar_tablas_view_directores,name='institucional'),   
    path('matricula/',filter_matricula_views_directores,name='matricula'),   
    path('inst_uegp/',filtrar_tablas_view_directores_uegp,name='institucional_uegp'),   
    path('mat_uegp/',filter_matricula_views_directores_uegp,name='matricula_uegp'), 
]