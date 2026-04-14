from django.contrib import admin
from django.utils.html import format_html

from .models import (
    Supervisor2,
    NivelModalidad,
    Region,
    SituacionRevista
)

# =========================================
# 🔹 SUPERVISOR ADMIN
# =========================================

@admin.register(Supervisor2)
class SupervisorAdmin(admin.ModelAdmin):

    # =========================
    # LISTADO
    # =========================
    list_display = (
        "get_cuil",
        "get_apellido",
        "get_nombres",
        "situacion_revista",
        "estado_coloreado",
        "fecha_desde",
        "fecha_hasta",
    )

    search_fields = (
        "usuario__username",
        "usuario__apellido",
        "usuario__nombres",
    )

    list_filter = (
        "activo",
        "situacion_revista",
    )

    ordering = (
        "usuario__apellido",
        "usuario__nombres",
    )

    autocomplete_fields = ("usuario",)

    filter_horizontal = (
        "niveles_modalidad",
        "regiones",
    )

    readonly_fields = (
        "get_cuil",
        "get_apellido",
        "get_nombres",
        "created_at",
        "updated_at",
    )

    fieldsets = (
        ("👤 Datos personales (automáticos)", {
            "fields": ("get_cuil", "get_apellido", "get_nombres")
        }),
        ("💼 Datos laborales", {
            "fields": (
                "situacion_revista",
                "fecha_desde",
                "fecha_hasta",
                "activo",
            )
        }),
        ("📞 Contacto", {
            "fields": ("telefono", "email")
        }),
        ("📍 Cobertura", {
            "fields": (
                "niveles_modalidad",
                "regiones",
            )
        }),
        ("🧾 Auditoría", {
            "fields": ("created_at", "updated_at")
        }),
    )

    # =========================
    # HELPERS (CLAVE)
    # =========================
    def get_cuil(self, obj):
        return obj.usuario.username
    get_cuil.short_description = "CUIL"

    def get_apellido(self, obj):
        return obj.usuario.apellido
    get_apellido.short_description = "Apellido"

    def get_nombres(self, obj):
        return obj.usuario.nombres
    get_nombres.short_description = "Nombres"

    # =========================
    # ESTADO VISUAL
    # =========================
    def estado_coloreado(self, obj):
        color = "green" if obj.activo else "red"
        label = "Activo" if obj.activo else "Inactivo"

        return format_html(
            '<b style="color:{}">{}</b>',
            color,
            label
        )

    estado_coloreado.short_description = "Estado"

    def has_delete_permission(self, request, obj=None):
        return False

    def save_model(self, request, obj, form, change):
        if not obj.usuario:
            obj.usuario = request.user
        super().save_model(request, obj, form, change)


# =========================================
# 🔹 CATÁLOGOS
# =========================================

@admin.register(NivelModalidad)
class NivelModalidadAdmin(admin.ModelAdmin):
    list_display = ("nombre", "codigo")
    search_fields = ("nombre",)
    ordering = ("nombre",)


@admin.register(Region)
class RegionAdmin(admin.ModelAdmin):
    list_display = ("nombre",)
    search_fields = ("nombre",)
    ordering = ("nombre",)


@admin.register(SituacionRevista)
class SituacionRevistaAdmin(admin.ModelAdmin):
    list_display = ("nombre",)
    search_fields = ("nombre",)
    ordering = ("nombre",)