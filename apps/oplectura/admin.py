from django.contrib import admin
from .models import RegDocporSeccion, curso, division, turno, RegEvaluacionFluidezLectora, Periodos
from .models import RegAplicador

admin.site.register(RegDocporSeccion)
admin.site.register(curso)
admin.site.register(division)
admin.site.register(turno)
admin.site.register(RegEvaluacionFluidezLectora)
admin.site.register(Periodos)
admin.site.register(RegAplicador)