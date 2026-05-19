from django.contrib import admin
from .models import DocenteFrenteGrado, Personal


@admin.register(Personal)
class PersonalAdmin(admin.ModelAdmin):
    search_fields = ['cuil', 'apellido', 'nombres']
    list_display = ['cuil', 'apellido', 'nombres']


@admin.register(DocenteFrenteGrado)
class DocenteFrenteGradoAdmin(admin.ModelAdmin):

    autocomplete_fields = [
        'cueanexo',
        'cuil_docente',
        'cargo'
    ]

    list_display = [
        'cueanexo',
        'grado_anio',
        'seccion',
        'turno',
        'cuil_docente',
        'cargo',
        'activo'
    ]

    search_fields = [
        'cueanexo__cueanexo',
        'cuil_docente__cuil',
        'cuil_docente__apellido',
        'cuil_docente__nombres'
    ]