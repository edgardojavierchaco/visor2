from django.contrib import admin
from .models import *

admin.site.register(Supervisor)
admin.site.register(EscuelasSupervisadas)
admin.site.register(Asignacion)
admin.site.register(DetalleAsignacion)

