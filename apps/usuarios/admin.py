from django.contrib import admin
from django.shortcuts import redirect
from django.contrib import messages
from django.contrib.auth.admin import UserAdmin
from .models import UsuariosVisualizador, NivelAcceso, PerfilUsuario, Rol, UsuarioRechazado, SyncLog
from .forms import AdminUserCreationForm
from django import forms
from django.contrib.auth.forms import ReadOnlyPasswordHashField
from apps.usuarios.services.sync_usuarios import sync_usuarios_directores
from django.http import HttpResponse
import openpyxl
from django.utils.html import format_html
from .models import (
    UsuarioRechazadoLog,
    UsuarioAuditoriaLog
)


# --------------------------
# Form para edición (necesario)
# --------------------------
class AdminUserChangeForm(forms.ModelForm):
    password = ReadOnlyPasswordHashField(label="Contraseña")

    class Meta:
        model = UsuariosVisualizador
        fields = '__all__'


# --------------------------
# Inline PerfilUsuario
# --------------------------
class PerfilUsuarioInline(admin.StackedInline):
    model = PerfilUsuario
    can_delete = False
    fk_name = 'usuario'
    extra = 0
    verbose_name_plural = 'Perfil'


# --------------------------
# Admin UsuariosVisualizador
# --------------------------
class UsuariosVisualizadorAdmin(UserAdmin):
    add_form = AdminUserCreationForm
    form = AdminUserChangeForm
    model = UsuariosVisualizador

    list_display = ('username','apellido','nombres','nivelacceso','get_rol','activo','is_staff','is_superuser')
    list_filter = ('nivelacceso','perfil__rol','activo','is_staff','is_superuser')
    search_fields = ('username','apellido','nombres','perfil__rol__nombre')

    inlines = (PerfilUsuarioInline,)

    fieldsets = (
        (None, {'fields': ('username','password')}),
        ('Información', {'fields': ('apellido','nombres','correo','telefono','nivelacceso')}),
        ('Permisos', {'fields': ('activo','is_staff','is_superuser','groups','user_permissions')}),
    )

    # 🔥 IMPORTANTE: password1 y password2
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': (
                'username',
                'password1',
                'password2',
                'apellido',
                'nombres',
                'correo',
                'telefono',
                'nivelacceso',
                'activo',
                'is_staff',
                'is_superuser',
            ),
        }),
    )

    def get_rol(self, obj):
        return obj.perfil.rol.nombre if hasattr(obj,'perfil') and obj.perfil.rol else '-'
    get_rol.short_description = 'Rol'


# --------------------------
# Admin Rol
# --------------------------
class RolAdmin(admin.ModelAdmin):
    list_display = ('nombre','categoria_acceso','descripcion')
    search_fields = ('nombre',)


# --------------------------
# Admin NivelAcceso
# --------------------------
class NivelAccesoAdmin(admin.ModelAdmin):
    list_display = ('tacceso',)
    search_fields = ('tacceso',)   

  
@admin.register(UsuarioRechazado)
class RechazadoAdmin(admin.ModelAdmin):
    list_display = ("cuitcuil", "motivo", "fecha")


@admin.register(SyncLog)
class SyncLogAdmin(admin.ModelAdmin):

    list_display = (
        "inicio",
        "fin",
        "estado",
        "total_procesados",
        "insertados",
        "actualizados",
        "rechazados",
    )

    list_filter = (
        "estado",
        "inicio",
    )

    readonly_fields = (
        "inicio",
        "fin",
        "estado",
        "total_procesados",
        "insertados",
        "actualizados",
        "rechazados",
        "error",
    )

    search_fields = ("estado",)

    ordering = ("-inicio",)

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


# ==========================
# 🔥 AUDITORÍA USUARIOS
# ==========================
@admin.register(UsuarioAuditoriaLog)
class UsuarioAuditoriaAdmin(admin.ModelAdmin):

    list_filter = (
        "accion",
        "created_at",
    )

    search_fields = (
        "username",
    )

    readonly_fields = (
        "username",
        "accion",
        "cambios",
        "payload",
        "created_at"
    )

    ordering = ("-created_at",)
    
    def accion_coloreada(self, obj):
        color = {
            "created": "green",
            "updated": "orange",
            "skipped": "gray"
        }.get(obj.accion, "black")

        return format_html(
            '<b style="color:{}">{}</b>',
            color,
            obj.accion
        )

    accion_coloreada.short_description = "Acción"

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


# ==========================
# 🔥 RECHAZADOS + EXPORT EXCEL
# ==========================
@admin.register(UsuarioRechazadoLog)
class UsuarioRechazadoAdmin(admin.ModelAdmin):

    list_display = (
        "username",
        "motivo",
        "created_at"
    )

    list_filter = (
        "created_at",
        "motivo",
    )

    search_fields = (
        "username",
        "motivo",
    )

    readonly_fields = (
        "username",
        "payload",
        "motivo",
        "created_at"
    )

    ordering = ("-created_at",)

    actions = ["exportar_excel_rechazados"]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    # ==========================
    # 🔥 EXPORT EXCEL
    # ==========================
    def exportar_excel_rechazados(self, request, queryset):

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Rechazados"

        # Header
        ws.append([
            "Username",
            "Motivo",
            "Payload",
            "Fecha"
        ])

        for obj in queryset:
            ws.append([
                obj.username,
                obj.motivo,
                str(obj.payload),
                obj.created_at.strftime("%Y-%m-%d %H:%M:%S")
            ])

        response = HttpResponse(
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

        response["Content-Disposition"] = 'attachment; filename="rechazados.xlsx"'

        wb.save(response)
        return response

    exportar_excel_rechazados.short_description = "📥 Exportar a Excel"

# --------------------------
# Registro admin
# --------------------------
admin.site.register(UsuariosVisualizador, UsuariosVisualizadorAdmin)
admin.site.register(PerfilUsuario)
admin.site.register(Rol, RolAdmin)
admin.site.register(NivelAcceso, NivelAccesoAdmin)
