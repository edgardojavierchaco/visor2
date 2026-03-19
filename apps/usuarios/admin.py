from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import UsuariosVisualizador, NivelAcceso, PerfilUsuario, Rol
from .forms import AdminUserCreationForm
from django import forms
from django.contrib.auth.forms import ReadOnlyPasswordHashField


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

    #inlines = (PerfilUsuarioInline,)

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


# --------------------------
# Registro admin
# --------------------------
admin.site.register(UsuariosVisualizador, UsuariosVisualizadorAdmin)
admin.site.register(PerfilUsuario)
admin.site.register(Rol, RolAdmin)
admin.site.register(NivelAcceso, NivelAccesoAdmin)