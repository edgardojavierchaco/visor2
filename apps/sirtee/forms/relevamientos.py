from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone

from apps.sirtee.forms.base import SirteeBaseForm
from apps.sirtee.forms.validators import validate_cueanexo
from apps.sirtee.models.relevamientos import Relevamiento
from apps.sirtee.data.padron import PadronEscuelas


class RelevamientoForm(SirteeBaseForm):
    """
    Formulario institucional para alta de relevamientos.

    Características

    • Bootstrap automático
    • Select2 automático
    • Validaciones desacopladas
    • Integración con el padrón educativo
    • Autocompletado de datos de escuela
    """
    
    readonly_fields = [
        "cui",
        "oferta",
    ]

    class Meta:

        model = Relevamiento

        fields = [
            "cueanexo",
            "cui",
            "oferta",
            "fecha",
            "estado",
            "tipo_relevamiento",
            "observaciones",
        ]


        widgets = {           


            "fecha": forms.DateInput(
                attrs={
                    "type": "date",
                }
            ),
            
            "observaciones": forms.Textarea(
                attrs={                    
                    "rows": 5,
                }
            ),

        }

    # =====================================================
    # INIT
    # =====================================================

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)

        self.autofocus("cueanexo")

        self.empty_label(
            "estado",
            "Seleccione..."
        )

        self.empty_label(
            "tipo_relevamiento",
            "Seleccione..."
        )

        self.set_help(
            "cueanexo",
            "Ingrese el código oficial de la escuela."
        )

        self.set_help(
            "observaciones",
            "Observaciones generales del relevamiento."
        )
        
    # =====================================================
    # CUEANEXO
    # =====================================================

    def clean_cueanexo(self):

        cue = self.cleaned_data.get("cueanexo", "").strip()

        validate_cueanexo(cue)

        escuela = PadronEscuelas.get(cue)

        if escuela is None:

            raise ValidationError(
                "El CUEANEXO no existe en el padrón educativo."
            )

        self._escuela = escuela

        return cue
    
    # --------------------------------------
    # VALIDACIÓN GENERAL
    # --------------------------------------

    def clean(self):

        cleaned = super().clean()

        escuela = getattr(
            self,
            "_escuela",
            None,
        )

        if escuela:

            cleaned["cui"] = escuela.get(
                "cui",
                "",
            )

            cleaned["oferta"] = escuela.get(
                "oferta",
                "",
            )

        estado = cleaned.get("estado")

        observaciones = cleaned.get("observaciones")

        if estado == "FINALIZADO":

            if not observaciones:

                self.add_error(

                    "observaciones",

                    "Debe indicar una observación antes de finalizar el relevamiento.",

                )

        fecha = cleaned.get("fecha")

        if fecha and fecha > timezone.localdate():

            self.add_error(

                "fecha",

                "La fecha del relevamiento no puede ser futura.",

            )

        return cleaned

    # =====================================================
    # SAVE
    # =====================================================

    def save(self, commit=True):

        obj = super().save(commit=False)

        if obj.estado == "FINALIZADO":

            obj.finalizado = True

            if not obj.fecha_finalizacion:

                obj.fecha_finalizacion = timezone.now()

        else:

            obj.finalizado = False

            obj.fecha_finalizacion = None

        if commit:

            obj.save()

        return obj