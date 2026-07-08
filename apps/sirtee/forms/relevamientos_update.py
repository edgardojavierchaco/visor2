from django import forms

from apps.sirtee.models.relevamientos import Relevamiento
from apps.sirtee.forms.base import SirteeBaseForm


class RelevamientoUpdateForm(SirteeBaseForm):

    class Meta:

        model = Relevamiento

        fields = [
            "fecha",
            "estado",
            "tipo_relevamiento",
            "observaciones",
            "finalizado",
        ]


        widgets = {

            "fecha": forms.DateInput(
                attrs={
                    "type": "date",
                    "class": "form-control",
                }
            ),


            "estado": forms.Select(
                attrs={
                    "class": "form-select",
                }
            ),


            "tipo_relevamiento": forms.Select(
                attrs={
                    "class": "form-select",
                }
            ),


            "observaciones": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                }
            ),


            "finalizado": forms.CheckboxInput(
                attrs={
                    "class": "form-check-input",
                }
            ),

        }


    def clean(self):

        cleaned = super().clean()


        estado = cleaned.get(
            "estado"
        )


        observaciones = cleaned.get(
            "observaciones"
        )


        if (
            estado == "FINALIZADO"
            and not observaciones
        ):

            self.add_error(
                "observaciones",
                "Debe justificar el relevamiento finalizado."
            )


        return cleaned