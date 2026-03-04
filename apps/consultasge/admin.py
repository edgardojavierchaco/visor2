from django.contrib import admin
from .models_padron import CapaUnicaOfertas
from .models import Categoria, Consulta, Respuesta, Adjunto, Auditoria


@admin.register(CapaUnicaOfertas)
class CapaUnicaOfertasAdmin(admin.ModelAdmin):
    list_display = (
        "cueanexo",
        "nom_est",
        "region_loc",
        "ref_loc",
        "localidad",
        "departamento"
    )
    search_fields = ("cueanexo", "nom_est", "localidad")
    list_filter = ("region_loc", "departamento")


@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ("nombre", "sla_horas")


@admin.register(Consulta)
class ConsultaAdmin(admin.ModelAdmin):
    list_display = ("asunto", "usuario", "categoria", "estado", "fecha_creacion")
    list_filter = ("estado", "categoria")
    search_fields = ("asunto", "escuela")


admin.site.register(Respuesta)
admin.site.register(Adjunto)
admin.site.register(Auditoria)