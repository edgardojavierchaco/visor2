import django_filters

from django import forms

from apps.sirtee.models.hallazgos import Hallazgo

from apps.sirtee.models.relevamientos import Relevamiento

from apps.sirtee.catalogos.models import (

    Criticidad,

    EstadoHallazgo,

    AreaAfectada,

)



class HallazgoFilter(
    django_filters.FilterSet
):


    buscar = django_filters.CharFilter(
        method="filtrar_texto",
        label="Buscar"
    )


    criticidad = django_filters.ModelChoiceFilter(

        queryset=Criticidad.objects.all()

    )


    estado = django_filters.ModelChoiceFilter(

        queryset=EstadoHallazgo.objects.all()

    )


    area = django_filters.ModelChoiceFilter(

        field_name="area_afectada",

        queryset=AreaAfectada.objects.all()

    )


    relevamiento = django_filters.ModelChoiceFilter(

        queryset=Relevamiento.objects.all()

    )



    class Meta:

        model = Hallazgo


        fields = [

            "buscar",

            "criticidad",

            "estado",

            "area",

            "relevamiento",

        ]




    def __init__(self,*args,**kwargs):

        super().__init__(*args,**kwargs)


        for field in self.form.fields.values():

            field.widget.attrs.update(

                {

                    "class":
                    "form-select"

                }

            )


        self.form.fields[
            "buscar"
        ].widget = forms.TextInput(

            attrs={

                "class":
                "form-control",

                "placeholder":
                "Buscar hallazgo..."

            }

        )




    def filtrar_texto(
        self,
        queryset,
        name,
        value
    ):


        return queryset.filter(

            titulo__icontains=value

        ) | queryset.filter(

            descripcion__icontains=value

        ) | queryset.filter(

            ubicacion__icontains=value

        )