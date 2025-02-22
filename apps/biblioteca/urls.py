from django.urls import path
from .views_matbiblio import (
    MaterialBibliograficoCreateView,
    MaterialBibliograficoUpdateView,
    MaterialBibliograficoDeleteView,
    MaterialBibliograficoListView
)

from .views_generarpdf import generar_pdf_material_bibliografico

app_name = 'bibliotecas'

urlpatterns = [
    # Material Bibliográfico
    path('materialbibliografico/list/', MaterialBibliograficoListView.as_view(), name='materialbibliografico_list'),
    path('materialbibliografico/add/', MaterialBibliograficoCreateView.as_view(), name='materialbibliografico_create'),
    path('materialbibliografico/update/<int:pk>/', MaterialBibliograficoUpdateView.as_view(), name='materialbibliografico_update'),
    path('materialbibliografico/delete/<int:pk>/', MaterialBibliograficoDeleteView.as_view(), name='materialbibliografico_delete'),

    # home (faltaba definir la ruta, agrégala si es necesario)
    path('generar_pdf/', generar_pdf_material_bibliografico, name='generar_pdf'),
]
