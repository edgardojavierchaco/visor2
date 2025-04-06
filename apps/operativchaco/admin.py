from django.contrib import admin
from .models import (
    AlumnosSecundariaDiagnostico, 
    ConceptosLengua, 
    ExamenLenguaAlumno, 
    RegistroAsistenciaLengua,
    ConceptosMatematica,
    ExamenMatematicaAlumno,
    RegistroAsistenciaMatematica,
    EscuelasSecundarias,
)

admin.site.register(AlumnosSecundariaDiagnostico)
admin.site.register(ConceptosLengua)
admin.site.register(ExamenLenguaAlumno)
admin.site.register(RegistroAsistenciaLengua)
admin.site.register(ConceptosMatematica)
admin.site.register(ExamenMatematicaAlumno)
admin.site.register(RegistroAsistenciaMatematica)
admin.site.register(EscuelasSecundarias)

