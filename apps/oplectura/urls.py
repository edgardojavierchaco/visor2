from django.urls import path
from apps.oplectura.views import DocenteCreateView, DocentesListView, DocentesUpdateView, DocentesDeleteView, mostrar_grafico, cargar_grafico_reg, mostrar_grafico_reg

app_name = 'lectura'

urlpatterns = [
    path('cargar/', DocenteCreateView.as_view(), name='cargar'),
    path('listado/', DocentesListView.as_view(), name='listado'),
    path('editar/', DocentesUpdateView.as_view(), name='editar'),
    path('eliminar/', DocentesDeleteView.as_view(), name='eliminar'),
    path('mostrar_grafico/', mostrar_grafico, name='mostrar_grafico'),
    path('cargar_graficoreg/', cargar_grafico_reg, name='cargar_graficoreg'),
    path('grafico_reg/', mostrar_grafico_reg, name='grafico_reg'),
]
