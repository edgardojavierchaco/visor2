from django.contrib import admin
from .models import Area, Categoria, Pregunta, TipoOpcion, Opcion, AlumnosSecundaria, ExamenSecundaria, Respuesta

class OpcionInline(admin.TabularInline):
    model = Opcion
    extra = 1  

@admin.register(Pregunta)
class PreguntaAdmin(admin.ModelAdmin):
    list_display = ('texto', 'mostrar_categorias', 'area')
    filter_horizontal = ('categorias',) 
    inlines = [OpcionInline]  
    
    def mostrar_categorias(self, obj):
        return ", ".join([c.nombre for c in obj.categorias.all()])
    mostrar_categorias.short_description = "Categorías"

admin.site.register(Area)
admin.site.register(Categoria)
admin.site.register(TipoOpcion)
admin.site.register(Opcion)
admin.site.register(AlumnosSecundaria)
admin.site.register(ExamenSecundaria)
admin.site.register(Respuesta)
