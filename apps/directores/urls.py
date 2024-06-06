from config.urls import path
from .views import filtrar_tablas_view_directores, filter_matricula_views_directores

app_name='directores'

urlpatterns=[
    path('',filtrar_tablas_view_directores,name='institucional'),   
    path('matricula/',filter_matricula_views_directores,name='matricula'),   
]