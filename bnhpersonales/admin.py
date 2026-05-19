from django.contrib import admin
from .models import Personas, Provincias, Localidades, Sexo, RegistroActividades, NomencladorCeic
from django.db.models import Q

@admin.register(Personas)
class PersonasAdmin(admin.ModelAdmin):

    list_display = (
        'apellido', 'nombre', 'dni',
        'provincia', 'localidad'
    )

    list_filter = (
        'provincia',
        'sexo',
    )

    search_fields = (
        'apellido',
        'nombre',
        'dni',
    )

    ordering = ('apellido',)

    list_select_related = ('provincia', 'localidad', 'sexo')


@admin.register(Provincias)
class ProvinciasAdmin(admin.ModelAdmin):
    search_fields = ('descrip_provincia',)


@admin.register(Localidades)
class LocalidadesAdmin(admin.ModelAdmin):
    search_fields = ('descrip_localidad',)


@admin.register(Sexo)
class SexoAdmin(admin.ModelAdmin):
    search_fields = ('descrip_sexo',)

@admin.register(RegistroActividades)
class RegistroActividadesAdmin(admin.ModelAdmin):

    list_display = (
        'persona',
        'cueanexo',
        'modalidad',
        'niveles',
        'ceic',
        'carga_horaria',
        'estado'
    )

    autocomplete_fields = ['persona']

    class Media:
        js = ('admin/js/ceic_filter.js',)

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)

        class FormWithCEIC(form):
            def __init__(self2, *args, **kwargs2):
                super().__init__(*args, **kwargs2)

                data = self2.data or None

                modalidad = data.get('modalidad') if data else getattr(self2.instance, 'modalidad_id', None)
                nivel = data.get('niveles') if data else getattr(self2.instance, 'niveles_id', None)

                qs = NomencladorCeic.objects.none()

                if modalidad:
                    modalidad = int(modalidad)

                    if modalidad == 1 and nivel:
                        qs = NomencladorCeic.objects.filter(
                            t_nivel='Nivel',
                            c_niv=nivel
                        )
                    else:
                        qs = NomencladorCeic.objects.filter(
                            t_nivel='Modalidad',
                            c_niv=modalidad
                        )

                self2.fields['ceic'].queryset = qs.order_by('descripcion')

        return FormWithCEIC