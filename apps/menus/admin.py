from django.contrib import admin
from .models import MenuItem


@admin.register(MenuItem)
class MenuItemAdmin(admin.ModelAdmin):

    list_display = ("label", "parent", "orden", "activo")
    list_filter = ("activo", "parent")
    search_fields = ("label", "clave")

    ordering = ("orden",)

    fieldsets = (
        ("General", {
            "fields": ("label", "icon", "url", "parent")
        }),
        ("Permisos", {
            "fields": ("roles", "categorias")
        }),
        ("Configuración", {
            "fields": ("orden", "activo", "clave")
        }),
    )