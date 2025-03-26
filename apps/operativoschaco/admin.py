from django.contrib import admin
from .models import Alumno, Categoria, OpcionesRespuestasAreas, PreguntasporArea, Subcategoria, Pregunta, Opcion, Respuesta, Examen

admin.site.register(Alumno)
admin.site.register(Categoria)
admin.site.register(Subcategoria)
admin.site.register(Pregunta)
admin.site.register(Opcion)
admin.site.register(Respuesta)
admin.site.register(Examen)
admin.site.register(PreguntasporArea)
admin.site.register(OpcionesRespuestasAreas)


