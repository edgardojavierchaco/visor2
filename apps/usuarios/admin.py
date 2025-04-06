from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import UsuariosVisualizador, NivelAcceso



class UsuariosVisualizadorAdmin(UserAdmin):
    """
    Administración de Usuarios Visualizadores.

    Configura la interfaz de administración para el modelo UsuariosVisualizador.

    Atributos:
        list_display: Campos a mostrar en la lista de usuarios.
        list_filter: Filtros disponibles en la lista de usuarios.
        search_fields: Campos por los cuales se puede buscar usuarios.
        fieldsets: Estructura de campos en el formulario de edición.
        add_fieldsets: Estructura de campos en el formulario de creación.
        ordering: Ordenamiento de usuarios por apellido y nombres.
        filter_horizontal: Campos que pueden ser seleccionados en múltiples relaciones.
    """
    
    list_display = ('username', 'apellido', 'nombres', 'correo', 'telefono', 'nivelacceso', 'activo', 'is_staff', 'is_superuser')
    list_filter = ('nivelacceso', 'activo', 'is_staff', 'is_superuser')
    search_fields = ('username', 'apellido', 'nombres', 'correo', 'telefono')
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Información Personal', {'fields': ('apellido', 'nombres', 'correo', 'telefono', 'nivelacceso')}),
        ('Permisos', {'fields': ('activo', 'is_staff', 'is_superuser','groups','user_permissions')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'password', 'apellido', 'nombres', 'correo', 'telefono', 'nivelacceso', 'activo', 'is_staff', 'is_superuser'),
        }),
    )
    ordering = ('apellido', 'nombres')
    filter_horizontal = ('groups', 'user_permissions')


class NivelAccesoAdmin(admin.ModelAdmin):
    """
    Administración de Niveles de Acceso.

    Configura la interfaz de administración para el modelo NivelAcceso.

    Atributos:
        list_display: Campos a mostrar en la lista de niveles de acceso.
        search_fields: Campos por los cuales se puede buscar niveles de acceso.
    """
    
    list_display = ('tacceso',)
    search_fields = ('tacceso',)


admin.site.register(UsuariosVisualizador, UsuariosVisualizadorAdmin)
admin.site.register(NivelAcceso, NivelAccesoAdmin)


