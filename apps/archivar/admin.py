from django.contrib import admin
from .models import (
    AsuntoEvaluacion, 
    AsuntoRegister, 
    ArchRegister, 
    nivel, 
    TNormativa, 
    VCapaUnicaOfertasCuiCuof,
    AsuntoEvaluacion,
    TEvaluacion,
    ArchModelosEvaluacion    
)

admin.site.register(AsuntoRegister)
admin.site.register(ArchRegister)
admin.site.register(nivel)
admin.site.register(TNormativa)
admin.site.register(VCapaUnicaOfertasCuiCuof)
admin.site.register(AsuntoEvaluacion)
admin.site.register(TEvaluacion)
admin.site.register(ArchModelosEvaluacion)
