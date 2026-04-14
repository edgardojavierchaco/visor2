from django.contrib import admin
from .models import Alumno, Evaluacion, Pregunta, OpcionRespuesta, EvaluacionAlumno

# Inline para OpcionRespuesta
class OpcionRespuestaInline(admin.TabularInline):
    model = OpcionRespuesta
    extra = 1

# Registro de Pregunta en el Admin
class PreguntaAdmin(admin.ModelAdmin):
    list_display = ('texto', 'puntaje', 'tipo', 'respuesta_correcta', 'texto_base')
    search_fields = ('texto',)
    list_filter = ('tipo',)
    inlines = [OpcionRespuestaInline]

    fieldsets = (
        (None, {
            'fields': ('texto', 'tipo', 'puntaje', 'evaluacion'),
        }),
        ('Respuestas', {
            'fields': ('respuesta_correcta', 'texto_base'),
        }),
    )

    def get_fields(self, request, obj=None):
        """
        Ajustar los campos mostrados según el tipo de pregunta.
        """
        base_fields = ['texto', 'tipo', 'puntaje', 'evaluacion']
        if obj:
            if obj.tipo == Pregunta.OPCION_UNICA:
                return base_fields + ['respuesta_correcta']
            elif obj.tipo == Pregunta.TEXTO_CLASIFICAR:
                return base_fields + ['texto_base']
        return base_fields + ['respuesta_correcta', 'texto_base']

    def get_inline_instances(self, request, obj=None):
        """
        Mostrar las opciones de respuesta solo para preguntas de opción múltiple.
        """
        inlines = []
        if obj and obj.tipo == Pregunta.OPCION_MULTIPLE:
            inlines = [OpcionRespuestaInline(self.model, self.admin_site)]
        return inlines

admin.site.register(Pregunta, PreguntaAdmin)

# Registro de Evaluacion y EvaluacionAlumno en el Admin
admin.site.register(Evaluacion)
admin.site.register(Alumno)
admin.site.register(EvaluacionAlumno)
