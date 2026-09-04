from django.contrib import admin
from .models import Personas, RegistroActividades, AccesoRegional, EventoAuditoria, ModalidadNivel, ModalidadNivelCeic

class SuperuserAdmin(admin.ModelAdmin):
    def has_module_permission(self, request):
        return request.user.is_superuser
    def has_view_permission(self, request, obj=None):
        return request.user.is_superuser
    def has_add_permission(self, request):
        return request.user.is_superuser
    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser
    def has_delete_permission(self, request, obj=None):
        return False

class ReadOnlyAdmin(SuperuserAdmin):
    def has_add_permission(self, request):
        return False
    def has_change_permission(self, request, obj=None):
        return False

@admin.register(Personas)
class PersonasAdmin(ReadOnlyAdmin):
    list_display = ("apellido", "nombre", "dni", "archivada")
    search_fields = ("apellido", "nombre", "dni", "cuil")

@admin.register(RegistroActividades)
class RegistroAdmin(ReadOnlyAdmin):
    list_display = ("persona", "cueanexo", "categoria", "eliminado", "validacion")
    list_filter = ("categoria", "eliminado", "validacion")
    list_select_related = ("persona",)

@admin.register(AccesoRegional)
class AccesoRegionalAdmin(SuperuserAdmin):
    list_display = ("usuario", "region", "activo")
    raw_id_fields = ("usuario",)
    exclude = ("usuario_creacion", "usuario_modificacion")
    def save_model(self, request, obj, form, change):
        from .services.crud import audit, snapshot
        from django.db import transaction
        with transaction.atomic():
            before = snapshot(AccesoRegional.objects.select_for_update().get(pk=obj.pk)) if change else {}
            if not change:
                obj.usuario_creacion = request.user
            obj.usuario_modificacion = request.user
            super().save_model(request, obj, form, change)
            audit(request.user, obj, "CAMBIAR_ACCESO", before)

@admin.register(EventoAuditoria)
class AuditoriaAdmin(ReadOnlyAdmin):
    list_display = ("fecha", "usuario", "entidad", "objeto_id", "cueanexo", "accion")
    list_filter = ("entidad", "accion")
    search_fields = ("cueanexo", "motivo")
    list_select_related = ("usuario",)

admin.site.register(ModalidadNivel, SuperuserAdmin)
admin.site.register(ModalidadNivelCeic, SuperuserAdmin)
