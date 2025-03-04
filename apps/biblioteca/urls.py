from django.urls import path
from .views_matbiblio import (
    MaterialBibliograficoCreateView,
    MaterialBibliograficoUpdateView,
    MaterialBibliograficoDeleteView,
    MaterialBibliograficoListView
)

from .views_servref import (
    ServiciosReferenciaCreateView,
    ServiciosReferenciaUpdateView,
    ServiciosReferenciaDeleteView,
    ServiciosReferenciaListView
)

from .views_servrefvirtual import (
    ServiciosRefVirtualCreateView,
    ServiciosRefVirtualUpdateView,
    ServiciosRefVirtualDeleteView,
    ServiciosRefVirtualListView
)

from .views_servprestamo import (
    ServiciosPrestamoCreateView,
    ServiciosPrestamoUpdateView,
    ServiciosPrestamoDeleteView,
    ServiciosPrestamoListView
)

from .views_infopedag import (
    InfoPedagoCreateView,
    InfoPedagoUpdateView,
    InfoPedagoDeleteView,
    InfoPedagoListView
)

from .views_instituciones import (
    InstitucionesCreateView,
    InstitucionesUpdateView,
    InstitucionesDeleteView,
    InstitucionesListView
)

from .views_asistusua import (
    AsistUsuarioCreateView,
    AsistUsuaUpdateView,
    AsistUsuaDeleteView,
    AsistUsuaListView
)

from .views_proctec import (
    ProcTecCreateView,
    ProcTecUpdateView,
    ProcTecDeleteView,
    ProcTecListView
)

from .views_aguapey import (
    AguapeyCreateView,
    AguapeyUpdateView,
    AguapeyDeleteView,
    AguapeyListView
)

from .views_generarpdf import generar_pdf_material_bibliografico
from .views_instituciones import ObtenerEscuelaView
from .views_generarinforme import GenerarInformeView
from .views_planillasanexas import PlanillasAnexasView, PlanillasAnexasListView, PlanillasAnexasUpdateView, PlanillasAnexasDeleteView
from .views_dashboard import DashboardView
from .views_reporteinformes import generar_informe_list, generar_informe
from .views_cuemesanio import generar_pdf_cuemesanio, modal_generar_pdf_cuemesanio
from .views_cuemesanio_uno import generar_pdf_cuemesanio_uno, modal_generar_pdf_cuemesanio_uno
app_name = 'bibliotecas'

urlpatterns = [
    # Material Bibliográfico
    path('materialbibliografico/list/', MaterialBibliograficoListView.as_view(), name='materialbibliografico_list'),
    path('materialbibliografico/add/', MaterialBibliograficoCreateView.as_view(), name='materialbibliografico_create'),
    path('materialbibliografico/update/<int:pk>/', MaterialBibliograficoUpdateView.as_view(), name='materialbibliografico_update'),
    path('materialbibliografico/delete/<int:pk>/', MaterialBibliograficoDeleteView.as_view(), name='materialbibliografico_delete'),

    # Servicios de Referencia
    path('servref/list/', ServiciosReferenciaListView.as_view(), name='servref_list'),
    path('servref/add/', ServiciosReferenciaCreateView.as_view(), name='servref_create'),
    path('servref/update/<int:pk>/', ServiciosReferenciaUpdateView.as_view(), name='servref_update'),
    path('servref/delete/<int:pk>/', ServiciosReferenciaDeleteView.as_view(), name='servref_delete'),
    
    # Servicios de Referencia Virtual
    path('servrefvirtual/list/', ServiciosRefVirtualListView.as_view(), name='servrefvirtual_list'),
    path('servrefvirtual/add/', ServiciosRefVirtualCreateView.as_view(), name='servrefvirtual_create'),
    path('servrefvirtual/update/<int:pk>/', ServiciosRefVirtualUpdateView.as_view(), name='servrefvirtual_update'),
    path('servrefvirtual/delete/<int:pk>/', ServiciosRefVirtualDeleteView.as_view(), name='servrefvirtual_delete'),
    
    # Servicios de Préstamos
    path('servprestamo/list/', ServiciosPrestamoListView.as_view(), name='servprestamo_list'),
    path('servprestamo/add/', ServiciosPrestamoCreateView.as_view(), name='servprestamo_create'),
    path('servprestamo/update/<int:pk>/', ServiciosPrestamoUpdateView.as_view(), name='servprestamo_update'),
    path('servprestamo/delete/<int:pk>/', ServiciosPrestamoDeleteView.as_view(), name='servprestamo_delete'),
    
    # Informe Pedagógico
    path('infopedago/list/', InfoPedagoListView.as_view(), name='infopedago_list'),
    path('infopedago/add/', InfoPedagoCreateView.as_view(), name='infopedago_create'),
    path('infopedago/update/<int:pk>/', InfoPedagoUpdateView.as_view(), name='infopedago_update'),
    path('infopedago/delete/<int:pk>/', InfoPedagoDeleteView.as_view(), name='infopedago_delete'),
    
    # Instituciones
    path('instituciones/list/', InstitucionesListView.as_view(), name='instituciones_list'),
    path('instituciones/add/', InstitucionesCreateView.as_view(), name='instituciones_create'),
    path('instituciones/update/<int:pk>/', InstitucionesUpdateView.as_view(), name='instituciones_update'),
    path('instituciones/delete/<int:pk>/', InstitucionesDeleteView.as_view(), name='instituciones_delete'),
    
    # Asistencia Usuarios
    path('asistusua/list/', AsistUsuaListView.as_view(), name='asistusua_list'),
    path('asistusua/add/', AsistUsuarioCreateView.as_view(), name='asistusua_create'),
    path('asistusua/update/<int:pk>/', AsistUsuaUpdateView.as_view(), name='asistusua_update'),
    path('asistusua/delete/<int:pk>/', AsistUsuaDeleteView.as_view(), name='asistusua_delete'),
    
    # Procesos Técnicos
    path('proctec/list/', ProcTecListView.as_view(), name='proctec_list'),
    path('proctec/add/', ProcTecCreateView.as_view(), name='proctec_create'),
    path('proctec/update/<int:pk>/', ProcTecUpdateView.as_view(), name='proctec_update'),
    path('proctec/delete/<int:pk>/', ProcTecDeleteView.as_view(), name='proctec_delete'),
    
    # Aguapey
    path('aguapey/list/', AguapeyListView.as_view(), name='aguapey_list'),
    path('aguapey/add/', AguapeyCreateView.as_view(), name='aguapey_create'),
    path('aguapey/update/<int:pk>/', AguapeyUpdateView.as_view(), name='aguapey_update'),
    path('aguapey/delete/<int:pk>/', AguapeyDeleteView.as_view(), name='aguapey_delete'),
   
    # Planillas Anexas
    path('plan_anexas/', PlanillasAnexasView.as_view(), name='plan_anexas'),
    path('anexas_list/', PlanillasAnexasListView.as_view(), name='anexas_list'),
    path('anexas/update/<int:pk>/', PlanillasAnexasUpdateView.as_view(), name='anexas_update'),
    path('anexas/delete/<int:pk>/', PlanillasAnexasDeleteView.as_view(), name='anexas_delete'),
     
    # home 
    path('generar_pdf/', generar_pdf_material_bibliografico, name='generar_pdf'),
    path('obtener_escuela/', ObtenerEscuelaView.as_view(), name='obtener_escuela'),
    path('generar_info/', GenerarInformeView.as_view(), name='generar_info'),
    path('dashboard/', DashboardView.as_view(), name='dashboard'),
    path('generar_informe_list/', generar_informe_list, name='generar_informe_list'),
    path('generar_informe/', generar_informe, name='generar_informe'),
    path('generar_pdf_cue/', generar_pdf_cuemesanio, name='generar_pdf_cue'),
    path('modal_generar_pdf_cue/', modal_generar_pdf_cuemesanio, name='modal_generar_pdf_cue'),
    path('generar_pdf_uno/', generar_pdf_cuemesanio_uno, name='generar_pdf_uno'),
    path('modal_generar_pdf_uno/', modal_generar_pdf_cuemesanio_uno, name='modal_generar_pdf_uno'),

]

