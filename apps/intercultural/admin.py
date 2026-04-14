from django.contrib import admin
from .models import EscuelasBilingues, Nivel_curso, Alumnos_Bilingue, VistaAlumnosBilingue, ExportarAlumnoBilingueConId

admin.site.register(EscuelasBilingues)
admin.site.register(Nivel_curso)
admin.site.register(Alumnos_Bilingue)
admin.site.register(VistaAlumnosBilingue)
admin.site.register(ExportarAlumnoBilingueConId)


