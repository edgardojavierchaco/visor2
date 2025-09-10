from django.contrib import admin
from .models import FAQ, Concepto

@admin.register(FAQ)
class FAQAdmin(admin.ModelAdmin):
    list_display = ("pregunta", "orden")
    search_fields = ("pregunta", "respuesta")
    ordering = ("orden",)

@admin.register(Concepto)
class ConceptoAdmin(admin.ModelAdmin):
    list_display = ("termino", "orden")
    search_fields = ("termino", "definicion")
    ordering = ("orden",)
