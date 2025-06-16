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

from .views_list_docnodoc import (
    DocentePonMensualListView,
    NoDocentePonMensualListView
)


from .views_generarpdf import generar_pdf_material_bibliografico
from .views_instituciones import ObtenerEscuelaView
from .views_generarinforme import GenerarInformeView
from .views_planillasanexas import PlanillasAnexasView, PlanillasAnexasListView, PlanillasAnexasUpdateView, PlanillasAnexasDeleteView
from .views_dashboard import DashboardView, DashboardDirView
from .views_reporteinformes import generar_informe_list, generar_informe
from .views_cuemesanio import generar_pdf_cuemesanio, modal_generar_pdf_cuemesanio
from .views_cuemesanio_uno import generar_pdf_cuemesanio_uno, modal_generar_pdf_cuemesanio_uno
from .views_registrofondos import RegistroDestinoFondosView, RegistroDestinoFondosListView, RegistroDestinoFondosDeleteView
from .views import (
    servicio_prestamo_view, 
    filtrar_servicio_prestamo, 
    filtrar_mat_biblio, 
    servicio_matbiblio_view,
    filtrar_servicio_referencia,
    servicio_referencia_view,
    servicio_referencia_virtual_view,
    filtrar_servicio_referencia_virtual,
    informe_pedagogico_view,
    filtrar_informe_pedagogico,
    asistencia_usuario_view,
    filtrar_asistencia_usuario,
    proceso_tecnico_view,
    filtrar_proceso_tecnico,
    destino_fondos_view,
    filtrar_destino_fondos,
    planillas_anexas_view,
    filtrar_planillas_anexas
)

from .views_bibliotecarios import (
    BibliotecariosCueCreateView,
    BibliotecariosCueListView,
    BibliotecariosCueUpdateView,
    BibliotecariosCueDeleteView,
)

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
    
    # Registro Destino de Fondos
    path('regfondos/', RegistroDestinoFondosView.as_view(), name='regfondos'),
    path('regfondos_list/', RegistroDestinoFondosListView.as_view(), name='regfondos_list'),
    path('regfondos/delete/<int:pk>/', RegistroDestinoFondosDeleteView.as_view(), name='regfondos   _delete'),
    
    # Planillas Anexas
    path('plan_anexas/', PlanillasAnexasView.as_view(), name='plan_anexas'),
    path('anexas_list/', PlanillasAnexasListView.as_view(), name='anexas_list'),
    path('anexas/update/<int:pk>/', PlanillasAnexasUpdateView.as_view(), name='anexas_update'),
    path('anexas/delete/<int:pk>/', PlanillasAnexasDeleteView.as_view(), name='anexas_delete'),
    
    # Planillas Docentes y no Docentes
    path('nom_doc/', DocentePonMensualListView.as_view(), name='nom_doc'),
    path('nom_ndoc/', NoDocentePonMensualListView.as_view(), name='nom_ndoc'), 
    
    # home 
    path('generar_pdf/', generar_pdf_material_bibliografico, name='generar_pdf'),
    path('obtener_escuela/', ObtenerEscuelaView.as_view(), name='obtener_escuela'),
    path('generar_info/', GenerarInformeView.as_view(), name='generar_info'),
    path('dashboard/', DashboardView.as_view(), name='dashboard'),
    path('dashboard_dir/', DashboardDirView.as_view(), name='dashboard_dir'),
    path('generar_informe_list/', generar_informe_list, name='generar_informe_list'),
    path('generar_informe/', generar_informe, name='generar_informe'),
    path('generar_pdf_cue/', generar_pdf_cuemesanio, name='generar_pdf_cue'),
    path('modal_generar_pdf_cue/', modal_generar_pdf_cuemesanio, name='modal_generar_pdf_cue'),
    path('generar_pdf_uno/', generar_pdf_cuemesanio_uno, name='generar_pdf_uno'),
    path('modal_generar_pdf_uno/', modal_generar_pdf_cuemesanio_uno, name='modal_generar_pdf_uno'),

    # Resultados
    path("servicio_prestamo/", servicio_prestamo_view, name="servicio_prestamo"),
    path("filtrar_servicio_prestamo/", filtrar_servicio_prestamo, name="filtrar_servicio_prestamo"),
    path("servicio_matbiblio/", servicio_matbiblio_view, name="servicio_matbiblio"),
    path("filtrar_matbiblio/", filtrar_mat_biblio, name="filtrar_matbiblio"),
    path("servicio_referencia/", servicio_referencia_view, name="servicio_referencia"),
    path("filtrar_referencia/", filtrar_servicio_referencia, name="filtrar_referencia"),
    path("servicio_refvirtual/", servicio_referencia_virtual_view, name="servicio_refvirtual"),
    path("filtrar_refvirtual/", filtrar_servicio_referencia_virtual, name="filtrar_refvirtual"),
    path("infopedagres/", informe_pedagogico_view, name="infopedagres"),
    path("filtrar_infopedag/", filtrar_informe_pedagogico, name="filtrar_infopedag"),
    path("asist_usua/", asistencia_usuario_view, name="asist_usua"),
    path("filtrar_asisusua/", filtrar_asistencia_usuario, name="filtrar_asisusua"),
    path("proctecres/", proceso_tecnico_view, name="proctecres"),
    path("filtrar_proctec/", filtrar_proceso_tecnico, name="filtrar_proctec"),
    path("destinofondos/", destino_fondos_view, name="destinofondos"),
    path("filtrar_desfondos/", filtrar_destino_fondos, name="filtrar_desfondos"),
    path("plan_anex/", planillas_anexas_view, name="plan_anex"),
    path("filtrar_plananex/", filtrar_planillas_anexas, name="filtrar_plananex"),
    
    # Bibliotecarios
    path('bibliotecarios/list/', BibliotecariosCueListView.as_view(), name='bibliotecario_list'),
    path('bibliotecarios/add/', BibliotecariosCueCreateView.as_view(), name='bibliotecario_create'),
    path('bibliotecarios/update/<int:pk>/', BibliotecariosCueUpdateView.as_view(), name='bibliotecario_update'),
    path('bibliotecarios/delete/<int:pk>/', BibliotecariosCueDeleteView.as_view(), name='bibliotecario_delete'),
]


