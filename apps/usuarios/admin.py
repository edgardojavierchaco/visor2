from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import UsuariosVisualizador, NivelAcceso


class UsuariosVisualizadorAdmin(UserAdmin):
    list_display = ('username', 'apellido', 'nombres', 'correo', 'telefono', 'nivelacceso', 'activo', 'is_staff', 'is_superuser')
    list_filter = ('nivelacceso', 'activo', 'is_staff', 'is_superuser')
    search_fields = ('username', 'apellido', 'nombres', 'correo', 'telefono')
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Información Personal', {'fields': ('apellido', 'nombres', 'correo', 'telefono', 'nivelacceso')}),
        ('Permisos', {'fields': ('activo', 'is_staff', 'is_superuser')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'password', 'apellido', 'nombres', 'correo', 'telefono', 'nivelacceso', 'activo', 'is_staff', 'is_superuser'),
        }),
    )
    ordering = ('apellido', 'nombres')
    filter_horizontal = ()


class NivelAccesoAdmin(admin.ModelAdmin):
    list_display = ('tacceso',)
    search_fields = ('tacceso',)


admin.site.register(UsuariosVisualizador, UsuariosVisualizadorAdmin)
admin.site.register(NivelAcceso, NivelAccesoAdmin)

