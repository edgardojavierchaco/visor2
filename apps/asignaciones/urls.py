from django.urls import path
from .views import (
    # =========================
    # CORE SUPERVISOR
    # =========================
    ajax_escuelas,
    ajax_asignar,
    crear_asignacion,
    editar_asignacion,
    enviar_asignacion,
    listar_asignaciones,
    panel_asignaciones,

    # =========================
    # REGIONAL
    # =========================
    panel_regional,
    aprobar_asignacion,
    rechazar_asignacion,

    # =========================
    # 🏛 ADMIN POWERBI (SALA DE SITUACIÓN)
    # =========================
    panel_admin_powerbi,
    dashboard_realtime_api,
    export_pdf_admin,
    filtros_catalogo,
)

app_name = "asignacionesuperv"


urlpatterns = [

    # =========================================================
    # 👨‍🏫 FLUJO SUPERVISOR
    # =========================================================
    path("crear/", crear_asignacion, name="crear_asignacion"),
    path("editar/<int:pk>/", editar_asignacion, name="editar_asignacion"),
    path("panel/", panel_asignaciones, name="panel"),

    # =========================================================
    # ⚙️ AJAX CORE
    # =========================================================
    path("ajax/escuelas/", ajax_escuelas, name="ajax_escuelas"),
    path("ajax/asignar/", ajax_asignar, name="ajax_asignar"),
    path("ajax/listar/", listar_asignaciones, name="listar_asignaciones"),
    path("ajax/enviar/", enviar_asignacion, name="enviar_asignacion"),

    # =========================================================
    # 🏢 PANEL REGIONAL
    # =========================================================
    path("regional/", panel_regional, name="panel_regional"),
    path("ajax/aprobar/", aprobar_asignacion, name="aprobar_asignacion"),
    path("ajax/rechazar/", rechazar_asignacion, name="rechazar_asignacion"),

    # =========================================================
    # 🏛 CENTRO DE CONTROL MINISTERIAL (POWERBI)
    # =========================================================
    path("admin/panel/", panel_admin_powerbi, name="panel_admin_powerbi"),
    path("admin/realtime/", dashboard_realtime_api, name="dashboard_realtime_api"),
    path("admin/export/pdf/", export_pdf_admin, name="export_pdf_admin"),
    path("admin/filtros/", filtros_catalogo, name="filtros_catalogo"),
]