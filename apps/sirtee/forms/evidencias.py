from django import forms
from django.forms import inlineformset_factory
from apps.sirtee.models.hallazgos import Hallazgo

from apps.sirtee.models.evidencias import (
    EvidenciaHallazgo
)

from apps.sirtee.forms.base import SirteeBaseForm



class EvidenciaHallazgoForm(SirteeBaseForm):


    class Meta:

        model = EvidenciaHallazgo


        fields = [

            "archivo",

            "tipo_archivo",

            "descripcion",

            "principal",

        ]


        widgets = {


            "archivo": forms.ClearableFileInput(

                attrs={

                    "class":
                    "form-control",

                    "accept":
                    ".jpg,.jpeg,.png,.webp,.pdf,.doc,.docx,.xls,.xlsx"

                }

            ),



            "tipo_archivo": forms.Select(

                attrs={

                    "class":
                    "form-select select2"

                }

            ),



            "descripcion": forms.TextInput(

                attrs={

                    "class":
                    "form-control",

                    "placeholder":
                    "Descripción de la evidencia"

                }

            ),



            "principal": forms.CheckboxInput(

                attrs={

                    "class":
                    "form-check-input"

                }

            ),

        }



    # ======================================================
    # VALIDACIÓN ARCHIVO
    # ======================================================


    def clean_archivo(self):

        archivo = (
            self.cleaned_data
            .get("archivo")
        )


        if not archivo:

            return archivo



        # ------------------------------------------
        # Tamaño máximo
        # ------------------------------------------

        limite = 10 * 1024 * 1024


        if archivo.size > limite:

            raise forms.ValidationError(

                "El archivo no puede superar los 10 MB."

            )



        # ------------------------------------------
        # Extensiones permitidas
        # ------------------------------------------

        permitidas = [

            ".jpg",
            ".jpeg",
            ".png",
            ".webp",

            ".pdf",

            ".doc",
            ".docx",

            ".xls",
            ".xlsx",

        ]


        nombre = archivo.name.lower()



        if not any(
            nombre.endswith(ext)
            for ext in permitidas
        ):

            raise forms.ValidationError(

                "Formato de archivo no permitido."

            )


        return archivo


EvidenciaHallazgoFormSet = inlineformset_factory(

    Hallazgo,

    EvidenciaHallazgo,

    form=EvidenciaHallazgoForm,

    extra=1,

    can_delete=True

)