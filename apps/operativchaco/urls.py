from django.urls import path
import io
import qrcode
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from django.http import FileResponse

from apps.oplectura import views_resultados
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
    dashboard_primarias_segundo,
    dashboard_primarias_tercero,
    dashboard_resultados_final_primaria,
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
    exportar_pdf_resultados_finales_primaria,
    ResultadosRegionSegundo,
    ResultadosRegionTercero,
)

# Fluidez Lectora 2° grado
from .views_fluidez_segundo import (
    buscar_alumno_por_dni_fluidez,
    cargar_examen_fluidez_segundo,
)

from .views_list_fluidez_segundo import (
    ExamenFluidezSegundoListView,
    ExamenFluidezSegundoDetailView,
    exportar_excel_examenes_segundo,
    examen_segundo_detalle_modal,
    cerrar_carga_fluidez_segundo,
    exportar_pdf_segundo,
    cerrar_carga_fluidez_segundo,    
)

# Fluidez Lectora 3° grado
from .views_fluidez_tercero import (
    buscar_alumno_por_dni_fluidezt,
    cargar_examen_fluidez_tercero,
)

from .views_list_fluidez_tercero import (
    ExamenFluidezTerceroListView,
    ExamenFluidezTerceroDetailView,
    exportar_excel_examenes_tercero,
    examen_tercero_detalle_modal,
    cerrar_carga_fluidez_tercero,
    exportar_pdf_tercero,
    cerrar_carga_fluidez_tercero,    
)

from .views_resultados_fluidez_segundo import (
    ResultadosCueanexoFluidezSegundo,
    ResultadosFluidezSegundoView,
    exportar_pdf_segundo,
    exportar_pdf_segundo_cueanexo,
)

from .views_resultados_fluidez_tercero import (
    ResultadosCueanexoFluidezTercero,
    ResultadosFluidezTerceroView,
    exportar_pdf_tercero,
    exportar_pdf_tercero_cueanexo,
)

from .views_grafesc_fluidez import datos_segundo_por_region, datos_tercero_por_region, escuelas_pendientes_segundo, escuelas_pendientes_tercero

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
    # Fluidez Segundo
    path('buscar_dni_fluidez/', buscar_alumno_por_dni_fluidez, name='buscar_dni_fluidez'),
    path('cargar_examen_fluidez_segundo/', cargar_examen_fluidez_segundo, name='carga_examen_fluidez_segundo'),
    path('fluidez/examenes/segundo', ExamenFluidezSegundoListView.as_view(), name='examen_segundo_listado'),
    path('fluidez/examenes/segundo/<int:pk>/', ExamenFluidezSegundoDetailView.as_view(), name='examen_segundo_detalle'),
    path('fluidez/examenes/segundo/exportar/', exportar_excel_examenes_segundo, name='exportar_excel_examenes_segundo'),
    path('examenes/segundo/<int:pk>/modal/', examen_segundo_detalle_modal, name='examen_segundo_detalle_modal'),
    path('cerrar_carga_segundo/',cerrar_carga_fluidez_segundo, name='cerrar_carga_segundo'),
    path('exportar_pdf_segundo/<int:examen_id>/', exportar_pdf_segundo, name='exportar_pdf_segundo'),    
    # Fluidez tercero    
    path('buscar_dni_fluidezt/', buscar_alumno_por_dni_fluidezt, name='buscar_dni_fluidezt'),
    path('cargar_examen_fluidez_tercero/', cargar_examen_fluidez_tercero, name='carga_examen_fluidez_tercero'),
    path('fluidez/examenes/tercero', ExamenFluidezTerceroListView.as_view(), name='examen_tercero_listado'),
    path('fluidez/examenes/tercero/<int:pk>/', ExamenFluidezTerceroDetailView.as_view(), name='examen_tercero_detalle'),
    path('fluidez/examenes/tercero/exportar/', exportar_excel_examenes_tercero, name='exportar_excel_examenes_tercero'),
    path('examenes/tercero/<int:pk>/modal/', examen_tercero_detalle_modal, name='examen_tercero_detalle_modal'),
    path('cerrar_carga_tercero/',cerrar_carga_fluidez_tercero, name='cerrar_carga_tercero'),
    path('exportar_pdf_tercero/<int:examen_id>/', exportar_pdf_tercero, name='exportar_pdf_tercero'),    
    # Resultados Fluidez Lectora Segundo
    path('resultados/cueanexo_segundo/', ResultadosFluidezSegundoView, name='resultados_cueanexo_segundo'),
    path('api/resultados/cueanexo_segundo/', ResultadosCueanexoFluidezSegundo, name='resultados_segundo_api'),
    path('resultados_segundo_pdf/', exportar_pdf_segundo, name='exportar_pdf_segundo'),    
    path('resultados_segundo_cue_pdf/', exportar_pdf_segundo_cueanexo, name='exportar_pdf_segundo_cue'),
    # Resultados Fluidez Lectora Tercero
    path('resultados/cueanexo_tercero/', ResultadosFluidezTerceroView, name='resultados_cueanexo_tercero'),
    path('api/resultados/cueanexo_tercero/', ResultadosCueanexoFluidezTercero, name='resultados_tercero_api'),
    path('resultados_tercero_pdf/', exportar_pdf_tercero, name='exportar_pdf_tercero'),    
    path('resultados_tercero_cue_pdf/', exportar_pdf_tercero_cueanexo, name='exportar_pdf_tercero_cue'),
    # Resultados Finales Fluidez
    path('resultados_final_primaria/', dashboard_primarias_segundo, name='dashboard_primaria'),
    path('resultados_final_primaria_tercero/', dashboard_primarias_tercero, name='dashboard_primarias_tercero'),
    path('resultados_final_primaria_pdf/', dashboard_resultados_final_primaria, name='dashboard_resultados_final_primaria'),
    path('resultados_finales_pdf_primaria/', exportar_pdf_resultados_finales_primaria, name='exportar_pdf_resultados_finales_primaria'),
    path('api/resultados/region_segundo/', ResultadosRegionSegundo, name='resultados_region_segundo_api'),
    path('api/resultados/region_tercero/', ResultadosRegionTercero, name='resultados_region_tercero_api'),
    # gráficos de carga escuelas fluidez segundo y tercero
    path('api/datos_segundo/', datos_segundo_por_region, name='datos_segundo'),
    path('api/datos_tercero/', datos_tercero_por_region, name='datos_tercero'),
    path('pendientes_segundo/', escuelas_pendientes_segundo, name='escuelas_pendientes_segundo'),
    path('pendientes_tercero/', escuelas_pendientes_tercero, name='escuelas_pendientes_tercero'),
]




