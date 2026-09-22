from django.contrib import admin
from .models import (
    Personas, RegistroActividades, AccesoRegional, EventoAuditoria,
    ModalidadNivel, ModalidadNivelCeic, ModalidadTipo, NivelServicioTipo,
    TitulacionNombre, TitulacionSuperior, TitulacionFP, EspacioCurricularNombre,
    TipoPersonal, CondicionActividadNombre, RevisionCatalogos,
)

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
    list_display = ("id_puesto", "persona", "cueanexo", "tipo_personal", "eliminado", "validacion")
    list_filter = ("tipo_personal", "eliminado", "validacion")
    search_fields = ("id_puesto", "cueanexo", "persona__apellido", "persona__nombre", "persona__dni", "persona__cuil")
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
    list_display = ("fecha", "operacion_id", "usuario", "entidad", "objeto_id", "cueanexo", "accion")
    list_filter = ("entidad", "accion")
    search_fields = ("cueanexo", "motivo")
    list_select_related = ("usuario",)

admin.site.register(ModalidadNivel, SuperuserAdmin)
admin.site.register(ModalidadNivelCeic, SuperuserAdmin)


# Catálogos curriculares: sólo lectura desde admin.
admin.site.register(ModalidadTipo, ReadOnlyAdmin)
admin.site.register(NivelServicioTipo, ReadOnlyAdmin)
admin.site.register(TitulacionNombre, ReadOnlyAdmin)
admin.site.register(TitulacionSuperior, ReadOnlyAdmin)
admin.site.register(TitulacionFP, ReadOnlyAdmin)
admin.site.register(EspacioCurricularNombre, ReadOnlyAdmin)

admin.site.register(TipoPersonal, ReadOnlyAdmin)
admin.site.register(CondicionActividadNombre, ReadOnlyAdmin)


@admin.register(RevisionCatalogos)
class RevisionCatalogosAdmin(ReadOnlyAdmin):
    list_display = ("version", "actualizado_en", "actualizado_por")
    list_select_related = ("actualizado_por",)
