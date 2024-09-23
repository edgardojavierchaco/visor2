from django.urls import path
from .views import tu_vista, cargar_grafico_reg, mostrar_grafico_reg, mostrar_pdf_recomendaciones, mostrar_pdf_informefinal
from .views import mostrar_grafico_localidad, cargar_grafico_loc, mostrar_grafico_loc

app_name = 'lectocomprension'

urlpatterns = [    
    path('resultados/', tu_vista, name='resultados'),   
    path('cargar_graficoreg/', cargar_grafico_reg, name='cargar_graficoreg'),
    path('cargar_graficoloc/', mostrar_grafico_localidad, name='cargar_graficoloc'),
    path('grafico_reg/', mostrar_grafico_reg, name='grafico_reg'),
    path('grafico_loc/', mostrar_grafico_loc, name='grafico_loc'),
    path('recomendaciones/', mostrar_pdf_recomendaciones, name='recomendaciones'),
    path('informe/', mostrar_pdf_informefinal, name='informe'),       
]
