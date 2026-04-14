from django.urls import path
from . import views

app_name = "supervisores2"

urlpatterns = [

    # =========================================================
    # 📊 LISTADO GENERAL (SEGÚN ROL)
    # =========================================================
    path("list/", views.supervisor_list, name="list"),

    # =========================================================
    # 👤 MI SUPERVISOR (ATAJO UX)
    # =========================================================
    path("mi/", views.mi_supervisor, name="mi"),

    # =========================================================
    # ➕ CREAR SUPERVISOR
    # =========================================================
    path("nuevo/", views.supervisor_create, name="create"),

    # =========================================================
    # ✏️ EDITAR SUPERVISOR
    # =========================================================
    path("<int:pk>/editar/", views.supervisor_update, name="update"),

    # =========================================================
    # 🗑️ ELIMINAR SUPERVISOR
    # =========================================================
    path("<int:pk>/eliminar/", views.supervisor_delete, name="delete"),

    # =========================================================
    # 🗺️ MAPA OPERATIVO
    # =========================================================
    path("mapa/", views.mapa_supervisores, name="mapa"),

    # =========================================================
    # 🧠 WORKFLOW (ACCIONES REGIONALES)
    # =========================================================

    # 📤 enviar a revisión (reintento / corrección)
    path(
        "<int:pk>/enviar-revision/",
        views.supervisor_send_review,
        name="send_review"
    ),

    # ✅ aprobar (REGIONAL)
    path(
        "<int:pk>/aprobar/",
        views.supervisor_approve,
        name="approve"
    ),

    # ❌ rechazar (REGIONAL)
    path(
        "<int:pk>/rechazar/",
        views.supervisor_reject,
        name="reject"
    ),
]