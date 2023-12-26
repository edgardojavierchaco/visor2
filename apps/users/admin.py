from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Usuarios

class CustomUserAdmin(UserAdmin):
    # Definir los campos que quieres mostrar en el admin
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Información personal', {'fields': ('nombre', 'apellido', 'email')}),
        ('Permisos', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Fechas importantes', {'fields': ('last_login', 'date_join')}),
    )

    # Especificar qué campos se deben mostrar en la lista de usuarios
    list_display = ('username', 'nombre', 'apellido', 'email', 'is_active', 'is_staff', 'is_superuser', 'last_login', 'date_join')
    list_filter = ('is_active', 'is_staff', 'is_superuser', 'groups')
    search_fields = ('username', 'nombre', 'apellido', 'email')
    ordering = ['username']
    
    def save_model(self, request, obj, form, change):
        # Guardar el modelo y registrar el cambio en el historial de administrador
        super().save_model(request, obj, form, change)

        # Personaliza esto según tus necesidades
        from django.contrib.admin.models import LogEntry, CHANGE
        LogEntry.objects.create(
            user_id=request.user.idusuario,
            content_type_id=None,  # Puedes personalizar esto según tus modelos
            object_id=obj.idusuario,  # Utiliza la clave primaria personalizada
            object_repr=str(obj),
            action_flag=CHANGE,
            change_message="Usuario creado/actualizado a través del panel de administración."
        )
# Registrar el modelo personalizado con la clase CustomUserAdmin
admin.site.register(Usuarios, CustomUserAdmin)
