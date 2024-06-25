from django.urls import path
from .views import tu_vista, cargar_grafico_reg, mostrar_grafico_reg, mostrar_pdf_recomendaciones, mostrar_pdf_informefinal

app_name='lectocomprension'

urlpatterns = [    
    path('resultados/', tu_vista, name='resultados'),   
    path('cargar_graficoreg/', cargar_grafico_reg, name='cargar_graficoreg'),
    path('grafico_reg/', mostrar_grafico_reg, name='grafico_reg'),
    path('recomendaciones/', mostrar_pdf_recomendaciones, name='recomendaciones'),
    path('informe/', mostrar_pdf_informefinal, name='informe'),
]