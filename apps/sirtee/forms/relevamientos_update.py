from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone

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

    # =========================================
    # VALIDACIONES
    # =========================================
    def clean(self):

        cleaned = super().clean()

        fecha = cleaned.get(
            "fecha"
        )

        estado = cleaned.get(
            "estado"
        )


        observaciones = cleaned.get(
            "observaciones"
        )

        finalizado = cleaned.get(
            "finalizado"
        )
        
        if fecha and fecha > timezone.localdate():

            self.add_error(
                "fecha",
                "La fecha del relevamiento no puede ser futura."
            )

        if finalizado:

            if not observaciones:

                self.add_error(
                    "observaciones",
                    "Debe justificar el relevamiento finalizado."
                )


            cleaned["estado"] = "FINALIZADO"


        return cleaned

    # =========================================
    # SAVE
    # =========================================

    def save(self, commit=True):

        obj = super().save(commit=False)


        if obj.finalizado:


            obj.estado = "FINALIZADO"


            if not obj.fecha_finalizacion:

                obj.fecha_finalizacion = timezone.now()


        else:


            obj.fecha_finalizacion = None


            if obj.estado == "FINALIZADO":

                obj.estado = "EN_PROCESO"



        if commit:

            obj.save()


        return obj