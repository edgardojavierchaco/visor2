from django.urls import path
from .views import (
    filtrar_tablas_view_directores,
    filter_matricula_views_directores,
    ajax_filtrar_matricula
)
from .views_uegp import (
    filter_matricula_views_directores_uegp,
    filtrar_tablas_view_directores_uegp
)

app_name = 'directores'

urlpatterns = [
    # Institucional principal
    path('', filtrar_tablas_view_directores, name='institucional'),   
    
    # Matrícula principal
    path('matricula/', filter_matricula_views_directores, name='matricula'),   
    
    # AJAX para filtrar matrícula sin recargar la página
    path('ajax/filtrar_matricula/', ajax_filtrar_matricula, name='ajax_filtrar_matricula'),
    
    # Vistas UEGP
    path('inst_uegp/', filtrar_tablas_view_directores_uegp, name='institucional_uegp'),   
    path('mat_uegp/', filter_matricula_views_directores_uegp, name='matricula_uegp'), 
]