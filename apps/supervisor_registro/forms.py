from django import forms

from .models import (
    SupervisorSituacionRevista
)

from apps.supervisa2.models import (
    SituacionRevista,
    NivelModalidad,
    Region
)


class SituacionRevistaForm(forms.ModelForm):

    class Meta:

        model = SupervisorSituacionRevista

        fields = (
            "situacion_revista",
            "fecha_desde",
            "fecha_hasta",
            "activo"
        )

        widgets = {

            "situacion_revista":
                forms.Select(
                    attrs={"class": "form-control"}
                ),

            "fecha_desde":
                forms.DateInput(
                    attrs={
                        "type": "date",
                        "class": "form-control"
                    }
                ),

            "fecha_hasta":
                forms.DateInput(
                    attrs={
                        "type": "date",
                        "class": "form-control"
                    }
                ),

            "vigente":
                forms.CheckboxInput(
                    attrs={
                        "class": "form-check-input"
                    }
                )
        }


class NivelForm(forms.Form):

    nivel = forms.ModelChoiceField(
        queryset=NivelModalidad.objects.all(),
        widget=forms.Select(
            attrs={
                "class": "form-control"
            }
        )
    )


class RegionForm(forms.Form):

    region = forms.ModelChoiceField(
        queryset=Region.objects.all(),
        widget=forms.Select(
            attrs={
                "class": "form-control"
            }
        )
    )