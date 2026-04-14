from django.contrib import admin

# Register your models here.
from .models import *


admin.site.register(Alumno)

admin.site.register(Grado)

admin.site.register(EvaluacionFluidezLectora)

admin.site.register(Seccion)