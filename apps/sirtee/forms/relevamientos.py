from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone

from apps.sirtee.forms.base import SirteeBaseForm
from apps.sirtee.forms.validators import validate_cueanexo

from apps.sirtee.models.relevamientos import (
    Relevamiento,
)

from apps.consultasge.models_padron import (
    CapaUnicaOfertas,
)


class RelevamientoForm(SirteeBaseForm):
    """
    Formulario institucional de Relevamientos.

    Características

    • Búsqueda por CUEANEXO
    • Selección múltiple de CUI
    • Selección múltiple de Ofertas
    • Compatible con JSONField
    • Bootstrap 5
    • Select2
    """

    # =====================================================
    # CAMPOS ADICIONALES
    # =====================================================

    cui = forms.MultipleChoiceField(

        label="CUI",

        required=True,

        choices=[],

        widget=forms.SelectMultiple(

            attrs={

                "class": "select2",

                "data-placeholder":
                    "Seleccione uno o más CUI",

            }

        ),

    )



    oferta = forms.MultipleChoiceField(

        label="Ofertas educativas",

        required=True,

        choices=[],

        widget=forms.SelectMultiple(

            attrs={

                "class": "select2",

                "data-placeholder":
                    "Seleccione una o más ofertas",

            }

        ),

    )

    # =====================================================
    # META
    # =====================================================

    class Meta:

        model = Relevamiento

        fields = [

            "cueanexo",

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

                }

            ),

            "observaciones": forms.Textarea(

                attrs={

                    "rows": 5,

                }

            ),

            "finalizado": forms.CheckboxInput(),

        }

    # =====================================================
    # INIT
    # =====================================================

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)

        # -----------------------------------------
        # Helpers
        # -----------------------------------------

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
            "Ingrese el CUEANEXO de la escuela."
        )

        self.set_help(
            "observaciones",
            "Observaciones generales."
        )

        # -----------------------------------------
        # Choices vacíos por defecto
        # -----------------------------------------

        self.fields["cui"].choices = []

        self.fields["oferta"].choices = []

        # -----------------------------------------
        # Determinar CUEANEXO
        # -----------------------------------------

        cueanexo = None

        if self.instance.pk:

            cueanexo = self.instance.cueanexo

        elif self.data.get("cueanexo"):

            cueanexo = self.data.get("cueanexo")

        elif self.initial.get("cueanexo"):

            cueanexo = self.initial.get("cueanexo")

        # -----------------------------------------
        # Cargar CUI y Ofertas disponibles
        # -----------------------------------------

        if cueanexo:

            registros = (

                CapaUnicaOfertas.objects

                .filter(
                    cueanexo=cueanexo
                )

                .order_by(
                    "cui",
                    "oferta",
                )

            )

            cuis = []

            ofertas = []

            for registro in registros:

                if registro.cui:

                    if registro.cui not in cuis:

                        cuis.append(
                            registro.cui
                        )

                if registro.oferta:

                    if registro.oferta not in ofertas:

                        ofertas.append(
                            registro.oferta
                        )

            self.fields["cui"].choices = [

                (x, x)

                for x in cuis

            ]

            self.fields["oferta"].choices = [

                (x, x)

                for x in ofertas

            ]

            # -------------------------------------
            # Edición
            # -------------------------------------

            if self.instance.pk:

                self.initial["cui"] = (

                    self.instance.cui or []

                )

                self.initial["oferta"] = (

                    self.instance.oferta or []

                )

        # ==================================================
        # MUY IMPORTANTE
        # ==================================================
        #
        # Recién aquí se aplican Bootstrap,
        # Select2 y clases CSS.
        #
        # Ahora los choices ya existen.
        #
        # ==================================================

        self.configure_fields()
    
        # ======================================================
    # VALIDACIÓN DEL CUEANEXO
    # ======================================================

    def clean_cueanexo(self):

        cue = (
            self.cleaned_data.get("cueanexo") or ""
        ).strip()

        validate_cueanexo(cue)

        existe = (
            CapaUnicaOfertas.objects
            .filter(cueanexo=cue)
            .exists()
        )

        if not existe:
            raise ValidationError(
                "El CUEANEXO no existe en el padrón."
            )

        return cue


    # ======================================================
    # VALIDACIONES GENERALES
    # ======================================================

    def clean(self):

        cleaned = super().clean()

        cueanexo = cleaned.get("cueanexo")

        cuis = cleaned.get("cui") or []

        ofertas = cleaned.get("oferta") or []

        fecha = cleaned.get("fecha")

        observaciones = cleaned.get("observaciones")

        finalizado = cleaned.get("finalizado")

        # ------------------------------------------
        # Fecha
        # ------------------------------------------

        if fecha and fecha > timezone.localdate():

            self.add_error(
                "fecha",
                "La fecha del relevamiento no puede ser futura."
            )

        # ------------------------------------------
        # Debe seleccionar CUI
        # ------------------------------------------

        if not cuis:

            self.add_error(
                "cui",
                "Debe seleccionar al menos un CUI."
            )

        # ------------------------------------------
        # Debe seleccionar oferta
        # ------------------------------------------

        if not ofertas:

            self.add_error(
                "oferta",
                "Debe seleccionar al menos una oferta."
            )

        # ------------------------------------------
        # Validar contra el padrón
        # ------------------------------------------

        if cueanexo:

            registros = (
                CapaUnicaOfertas.objects
                .filter(cueanexo=cueanexo)
            )

            cuis_validos = set()

            ofertas_validas = set()

            for r in registros:

                if r.cui:
                    cuis_validos.add(str(r.cui))

                if r.oferta:
                    ofertas_validas.add(str(r.oferta))

            # ------------------------------
            # Validar CUI
            # ------------------------------

            for cui in cuis:

                if str(cui) not in cuis_validos:

                    self.add_error(
                        "cui",
                        f'El CUI "{cui}" no pertenece al CUEANEXO seleccionado.'
                    )

            # ------------------------------
            # Validar ofertas
            # ------------------------------

            for oferta in ofertas:

                if str(oferta) not in ofertas_validas:

                    self.add_error(
                        "oferta",
                        f'La oferta "{oferta}" no pertenece al establecimiento.'
                    )

        # ------------------------------------------
        # Finalización
        # ------------------------------------------

        if finalizado:

            if not observaciones:

                self.add_error(
                    "observaciones",
                    "Debe ingresar una observación para finalizar el relevamiento."
                )

        return cleaned
    
        # ======================================================
    # SAVE
    # ======================================================

    def save(self, commit=True):

        obj = super().save(commit=False)

        # ------------------------------------------
        # JSONField CUI
        # ------------------------------------------

        obj.cui = list(
            self.cleaned_data.get(
                "cui",
                []
            )
        )

        # ------------------------------------------
        # JSONField Ofertas
        # ------------------------------------------

        obj.oferta = list(
            self.cleaned_data.get(
                "oferta",
                []
            )
        )

        # ------------------------------------------
        # Estado de finalización
        # ------------------------------------------

        obj.finalizado = self.cleaned_data.get(
            "finalizado",
            False
        )

        if obj.finalizado:

            if hasattr(obj, "estado"):

                obj.estado = "FINALIZADO"

            if (
                hasattr(obj, "fecha_finalizacion")
                and not obj.fecha_finalizacion
            ):

                obj.fecha_finalizacion = timezone.now()

        else:

            if (
                hasattr(obj, "estado")
                and obj.estado == "FINALIZADO"
            ):

                obj.estado = "EN_PROCESO"

            if hasattr(obj, "fecha_finalizacion"):

                obj.fecha_finalizacion = None

        # ------------------------------------------
        # Guardar
        # ------------------------------------------

        if commit:

            obj.save()

            if hasattr(self, "save_m2m"):

                self.save_m2m()

        return obj