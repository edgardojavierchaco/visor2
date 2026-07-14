from django.urls import path, include

from apps.sirtee.views.dashboard import SirteeDashboardView

# CRUD VIEWS
from apps.sirtee.views.relevamientos import (
    RelevamientoListView,
    RelevamientoCreateView,
    RelevamientoUpdateView,
    RelevamientoDetailView,
    RelevamientoDeleteView,
    RelevamientosEscuelaView,
    RelevamientoDetailMapaView
)

from apps.sirtee.views.hallazgos import (
    HallazgoListView,
    HallazgoCreateView,
    HallazgoUpdateView,
    HallazgoDetailView,
    HallazgoDeleteView,
)

from apps.sirtee.views.intervenciones import (
    IntervencionListView,
    IntervencionCreateView,
    IntervencionUpdateView,
    IntervencionDetailView,
    IntervencionDeleteView,
    IntervencionIniciarView,
    IntervencionPausarView,
    IntervencionCancelarView,
    IntervencionFinalizarView,
)

from apps.sirtee.views.empresas import (
    EmpresaListView,
    EmpresaCreateView,
    EmpresaUpdateView,
    EmpresaDetailView,
    EmpresaDeleteView,
    filtrar_localidades,
)

from apps.sirtee.views.reportes import (
    ReporteGeneralView,
    ExportRelevamientosCSV,
)

from apps.sirtee.views.reports import (
    ReporteDashboardView
)

from apps.sirtee.api.views_select2 import escuelas_select2

from apps.sirtee.api.views import escuela

from apps.sirtee.dashboard.views.dashboard import (
    DashboardView
)

from apps.sirtee.dashboard.views.mapa import (
    DashboardMapaView    
)

from apps.sirtee.api.views_mapa import mapa_operativo

from apps.sirtee.views.excel_reports import (
    exportar_intervenciones_excel,
    exportar_empresas_excel,
)

from apps.sirtee.views.excel_reports import (
    exportar_general_excel,
)

from apps.sirtee.views.seguimiento import (
    SeguimientoListView,
    SeguimientoCreateView,
    SeguimientoUpdateView,
    SeguimientoDetailView,
    SeguimientoDeleteView,
)

from apps.sirtee.dashboard.views.dashboard import (
    DashboardView
)

from apps.sirtee.dashboard.views.mapa import (
    DashboardMapaView
)


from apps.sirtee.dashboard.api.mapa import (
    mapa_api
)

app_name = "sirtee"

urlpatterns = [

    # ---------------- DASHBOARD ----------------
    path("dashboard_sirtee/", SirteeDashboardView.as_view(), name="sirtee-dashboard"),
    path("dashboard/", DashboardView.as_view(), name="dashboard"),
    path(
        "mapa/",
        DashboardMapaView.as_view(),
        name="dashboard-mapa"
    ),
    path(
        "api/mapa/",
        mapa_api,
        name="dashboard-mapa-api"
    ),    

    # ---------------- SELECT2 ----------------
    path("select2/escuelas/", escuelas_select2, name="select2-escuelas"),

    # ---------------- RELEVAMIENTOS ----------------
    path("relevamientos/", RelevamientoListView.as_view(), name="relevamientos-list"),
    path("relevamientos/nuevo/", RelevamientoCreateView.as_view(), name="relevamientos-create"),
    path("relevamientos/<int:pk>/", RelevamientoDetailView.as_view(), name="relevamientos-detail"),
    path("relevamientos/<int:pk>/editar/", RelevamientoUpdateView.as_view(), name="relevamientos-update"),
    path("relevamientos/<int:pk>/eliminar/",RelevamientoDeleteView.as_view(),name="relevamientos-delete"),
    path("relevamientos/escuela/<str:cueanexo>/",RelevamientosEscuelaView.as_view(),name="relevamientos-escuela"),
    path("relevamientos/mapa/<int:pk>/",RelevamientoDetailMapaView.as_view(),name="relevamientos-mapa"),

    # ---------------- HALLAZGOS ----------------
    path("hallazgos/", HallazgoListView.as_view(), name="hallazgos-list"),
    path("hallazgos/nuevo/", HallazgoCreateView.as_view(), name="hallazgos-create"),
    path("hallazgos/<int:pk>/", HallazgoDetailView.as_view(), name="hallazgos-detail"),
    path("hallazgos/<int:pk>/editar/", HallazgoUpdateView.as_view(), name="hallazgos-update"),
    path("hallazgos/<int:pk>/eliminar/", HallazgoDeleteView.as_view(), name="hallazgos-delete"),

    # ---------------- INTERVENCIONES ----------------
    path("intervenciones/", IntervencionListView.as_view(), name="intervenciones-list"),
    path("intervenciones/nuevo/", IntervencionCreateView.as_view(), name="intervenciones-create"),
    path("intervenciones/<int:pk>/", IntervencionDetailView.as_view(), name="intervenciones-detail"),
    path("intervenciones/<int:pk>/editar/", IntervencionUpdateView.as_view(), name="intervenciones-update"),
    path("intervenciones/<int:pk>/eliminar/", IntervencionDeleteView.as_view(), name="intervenciones-delete"),
    path("intervenciones/<int:pk>/iniciar/", IntervencionIniciarView.as_view(), name="intervenciones-iniciar"),
    path("intervenciones/<int:pk>/pausar/", IntervencionPausarView.as_view(), name="intervenciones-pausar"),
    path("intervenciones/<int:pk>/finalizar/", IntervencionFinalizarView.as_view(), name="intervenciones-finalizar"),
    path("intervenciones/<int:pk>/cancelar/", IntervencionCancelarView.as_view(), name="intervenciones-cancelar"),

    # ---------------- EMPRESAS ----------------
    path("empresas/", EmpresaListView.as_view(), name="empresas-list"),
    path("empresas/nuevo/", EmpresaCreateView.as_view(), name="empresas-create"),
    path("empresas/<int:pk>/", EmpresaDetailView.as_view(), name="empresas-detail"),
    path("empresas/<int:pk>/editar/", EmpresaUpdateView.as_view(), name="empresas-update"),
    path("empresas/<int:pk>/eliminar/", EmpresaDeleteView.as_view(), name="empresas-delete"),
    path(
        "ajax/localidades/",
        filtrar_localidades,
        name="filtrar-localidades"
    ),
    

    # ---------------- REPORTES ----------------
    path("reportes/general/", ReporteGeneralView.as_view(), name="reportes-general"),
    path("reportes/relevamientos/csv/", ExportRelevamientosCSV.as_view(), name="reportes-relevamientos-csv"),
    path("reportes/dashboard/", ReporteDashboardView.as_view(), name="reportes-dashboard"),
    
    
    # ---------------- FLUJO OPERATIVO ----------------
    path("relevamientos/<int:pk>/hallazgos/nuevo/",HallazgoCreateView.as_view(),name="relevamientos-hallazgo-create"),
    path("hallazgos/<int:pk>/intervenciones/nueva/",IntervencionCreateView.as_view(),name="hallazgos-intervencion-create"),
    
    # ---------------- MAPA ----------------
    path("dashboard/mapa/",DashboardMapaView.as_view(),name="dashboard-mapa"),    
    path("api/mapa/",mapa_operativo,name="api-mapa"),
    
    
    # ============================
    # EXPORTACIÓN EXCEL
    # ============================

    path(
        "reportes/excel/intervenciones/",
        exportar_intervenciones_excel,
        name="excel-intervenciones"
    ),


    path(
        "reportes/excel/empresas/",
        exportar_empresas_excel,
        name="excel-empresas"
    ),
    
    path(
        "reportes/excel/general/",
        exportar_general_excel,
        name="excel-general"
    ),
    
    # ---------------- SEGUIMIENTOS ----------------

    path(
        "seguimientos/",
        SeguimientoListView.as_view(),
        name="seguimientos-list"
    ),

    path(
        "seguimientos/nuevo/",
        SeguimientoCreateView.as_view(),
        name="seguimientos-create"
    ),

    path(
        "seguimientos/<int:pk>/",
        SeguimientoDetailView.as_view(),
        name="seguimientos-detail"
    ),

    path(
        "seguimientos/<int:pk>/editar/",
        SeguimientoUpdateView.as_view(),
        name="seguimientos-update"
    ),

    path(
        "seguimientos/<int:pk>/eliminar/",
        SeguimientoDeleteView.as_view(),
        name="seguimientos-delete"
    ),
    
    path("api/",include("apps.sirtee.api.urls")),
]