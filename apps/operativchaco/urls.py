from django.urls import path
import io
import qrcode
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from django.http import FileResponse
from .views import cargar_examen_lengua, buscar_alumno_por_dni
from .views_list import (
    ExamenLenguaListView,
    ExamenLenguaDetailView,
    exportar_excel_examenes,
    examen_lengua_detalle_modal,
    cerrar_carga_lengua,
    exportar_pdf,
    cerrar_carga_lengua,
)
from .views_matem import (
    cargar_examen_matematica,
    buscar_alumnom_por_dni,
)

from .views_list_matem import (
    ExamenMatematicaListView,
    ExamenMatematicaDetailView,
    exportar_excel_examenes_matematica,
    examen_matematica_detalle_modal,
    cerrar_carga_matematica,
    exportar_pdf_matematica,
)

from .views_dashpresent import(
    dashboard_secundarias, 
    dashboard_secundarias_superv, 
    dashboard_resultados_final,
    dashboard_resultados_final_superv,
    dashboard_secundarias_func,
    dashboard_resultados_final_func,
    dashboard_secundarias_regional,
    dashboard_resultados_final_regional,
)

from .views_grafesc import datos_lengua_por_region, datos_matematica_por_region, escuelas_pendientes_lengua, escuelas_pendientes_matematica

from .views_cuentaregresiva import (
    cuenta_regresiva_matematica, 
    cuenta_regresiva_lengua_graficos,
    cuenta_regresiva_matematica_graficos,
)

from .views_resultados import (
    ResultadosCueanexoLengua, 
    ResultadosLenguaView, 
    exportar_pdf_lengua,
    ResultadosMatematicaView,
    ResultadosCueanexoMatematica,
    exportar_pdf_matematica,
    exportar_pdf_lengua_cueanexo,
    exportar_pdf_matematica_cueanexo,   
)

from .views_resultados_reg import (
    ResultadosRegionLengua,
    ResultadosLenguaRegionalView,    
    ResultadosRegionMatematica,
    ResultadosMatematicaRegionalView,
    exportar_pdf_resultados_finales,
)


app_name='operativ'

urlpatterns = [
    # lengua
    path('examen-lengua/', cargar_examen_lengua, name='cargar_examen_lengua'),    
    path('buscar-alumno/', buscar_alumno_por_dni, name='buscar_alumno_por_dni'),  
    path('lengua/examenes/', ExamenLenguaListView.as_view(), name='examen_lengua_listado'),
    path('lengua/examenes/<int:pk>/', ExamenLenguaDetailView.as_view(), name='examen_lengua_detalle'),
    path('lengua/examenes/exportar/', exportar_excel_examenes, name='exportar_excel_examenes'),
    path('examenes/lengua/<int:pk>/modal/', examen_lengua_detalle_modal, name='examen_lengua_detalle_modal'),
    path('cerrar-carga/',cerrar_carga_lengua, name='cerrar_carga_lengua'),
    path('exportar_pdf/<int:examen_id>/', exportar_pdf, name='exportar_pdf'),
    path('cerrar-carga-lengua/', cerrar_carga_lengua, name='cerrar_carga_lengua'),
    # Matematica
    path('examen-matematica/', cargar_examen_matematica, name='cargar_examen_matematica'),
    path('buscar-alumnom/', buscar_alumnom_por_dni, name='buscar_alumnom_por_dni'),
    path('matematica/examenes/', ExamenMatematicaListView.as_view(), name='examen_matematica_listado'),
    path('matematica/examenes/<int:pk>/', ExamenMatematicaDetailView.as_view(), name='examen_matematica_detalle'),
    path('matematica/examenes/exportar/', exportar_excel_examenes_matematica, name='exportar_excel_examenes_matematica'),
    path('examenes/matematica/<int:pk>/modal/', examen_matematica_detalle_modal, name='examen_matematica_detalle_modal'),
    path('cerrar-carga-matematica/', cerrar_carga_matematica, name='cerrar_carga_matematica'),
    path('exportar_pdf_matematica/<int:examen_id>/', exportar_pdf_matematica, name='exportar_pdf_matematica'),
    path('cerrar-carga-matematica/', cerrar_carga_matematica, name='cerrar_carga_matematica'),
    path('dashboard/secundarias/', dashboard_secundarias, name='dashboard_secundarias'),
    path('dashboard/secundarias_superv/', dashboard_secundarias_superv, name='dashboard_secundarias_superv'),
    path('dashboard/secundarias_func/', dashboard_secundarias_func, name='dashboard_secundarias_func'),
    path('dashboard/secundarias_reg/', dashboard_secundarias_regional, name='dashboard_secundarias_regional'),
    # gráficos de carga escuelas
    path('api/datos_lengua/', datos_lengua_por_region, name='datos_lengua'),
    path('api/datos_matematica/', datos_matematica_por_region, name='datos_matematica'),
    path('pendientes_lengua/', escuelas_pendientes_lengua, name='escuelas_pendientes_lengua'),
    path('pendientes_matematica/', escuelas_pendientes_matematica, name='escuelas_pendientes_matematica'),
    # Cuentas regresivas
    path('cuenta_regresiva_matematica/', cuenta_regresiva_matematica, name='cuenta_regresiva_matematica'),
    path('cuenta_regresiva_lengua_graficos/', cuenta_regresiva_lengua_graficos, name='cuenta_regresiva_lengua_graficos'),
    path('cuenta_regresiva_matematica_graficos/', cuenta_regresiva_matematica_graficos, name='cuenta_regresiva_matematica_graficos'),
    # Resultados lengua y matematica cueanexo
    path('resultados/cueanexo_lengua/', ResultadosLenguaView, name='resultados_cueanexo_lengua'),
    path('api/resultados/cueanexo_lengua/', ResultadosCueanexoLengua, name='resultados_lengua_api'),
    path('resultados_lengua_pdf/', exportar_pdf_lengua, name='exportar_pdf_lengua'),
    path('resultados/cueanexo_matematica/', ResultadosMatematicaView, name='resultados_cueanexo_matematica'),
    path('api/resultados/cueanexo_matematica/', ResultadosCueanexoMatematica, name='resultados_matematica_api'),
    path('resultados_matematica_pdf/', exportar_pdf_matematica, name='exportar_pdf_matematica'),
    path('resultados_matematica_cue_pdf/', exportar_pdf_matematica_cueanexo, name='exportar_pdf_matematica_cue'),
    path('resultados_lengua_cue_pdf/', exportar_pdf_lengua_cueanexo, name='exportar_pdf_lengua_cue'),
    # Resultados lengua y matematica regional
    path('resultados/region_lengua/', ResultadosLenguaRegionalView, name='resultados_region_lengua'),
    path('api/resultados/region_lengua/', ResultadosRegionLengua, name='resultados_region_lengua_api'),    
    path('resultados/region_matematica/', ResultadosMatematicaRegionalView, name='resultados_region_matematica'),
    path('api/resultados/region_matematica/', ResultadosRegionMatematica, name='resultados_region_matematica_api'),
    path('resultados_finales_pdf/', exportar_pdf_resultados_finales, name='exportar_pdf_resultados_finales'),
    # Resultados finales
    path('resultados_final/', dashboard_resultados_final, name='dashboard_resultados_final'),
    path('resultados_final_superv/', dashboard_resultados_final_superv, name='dashboard_resultados_final_superv'),
    path('resultados_final_func/', dashboard_resultados_final_func, name='dashboard_resultados_final_func'),
    path('resultados_final_reg/', dashboard_resultados_final_regional, name='dashboard_resultados_final_regional'),
]




