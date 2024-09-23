from django.contrib import admin
from .models import EscuelaSupervisor, Supervisor, DirectoresRegionales

class EscuelaSupervisorInline(admin.TabularInline):
    model = EscuelaSupervisor
    extra=1


class SupervisorAdmin(admin.ModelAdmin):
    inlines=[EscuelaSupervisorInline]


admin.site.register(Supervisor, SupervisorAdmin)
admin.site.register(EscuelaSupervisor)
admin.site.register(DirectoresRegionales)

