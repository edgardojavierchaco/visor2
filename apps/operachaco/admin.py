from django.contrib import admin
from .models import Area, Categoria, Pregunta

@admin.register(Pregunta)
class PreguntaAdmin(admin.ModelAdmin):
    list_display = ('texto', 'mostrar_categorias', 'area')
    filter_horizontal = ('categorias',)  # Muestra un widget de selección múltiple

    def mostrar_categorias(self, obj):
        return ", ".join([c.nombre for c in obj.categorias.all()])
    mostrar_categorias.short_description = "Categorías"

admin.site.register(Area)
admin.site.register(Categoria)
