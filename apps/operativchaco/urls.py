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

from .views_dashpresent import dashboard_secundarias

from .views_grafesc import datos_lengua_por_region, datos_matematica_por_region, escuelas_pendientes_lengua, escuelas_pendientes_matematica

from .views_cuentaregresiva import (
    cuenta_regresiva_matematica, 
    cuenta_regresiva_lengua_graficos,
    cuenta_regresiva_matematica_graficos,
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
    # gráficos de carga escuelas
    path('api/datos_lengua/', datos_lengua_por_region, name='datos_lengua'),
    path('api/datos_matematica/', datos_matematica_por_region, name='datos_matematica'),
    path('pendientes_lengua/', escuelas_pendientes_lengua, name='escuelas_pendientes_lengua'),
    path('pendientes_matematica/', escuelas_pendientes_matematica, name='escuelas_pendientes_matematica'),
    # Cuentas regresivas
    path('cuenta_regresiva_matematica/', cuenta_regresiva_matematica, name='cuenta_regresiva_matematica'),
    path('cuenta_regresiva_lengua_graficos/', cuenta_regresiva_lengua_graficos, name='cuenta_regresiva_lengua_graficos'),
    path('cuenta_regresiva_matematica_graficos/', cuenta_regresiva_matematica_graficos, name='cuenta_regresiva_matematica_graficos'),
]




