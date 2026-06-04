from django import forms
from django.forms import inlineformset_factory, BaseInlineFormSet

from .models import (
    Personas,
    RegistroActividades,
    Localidades,
    CodAreasTelefonos
)

from .utils import get_ofertas_usuario


# =====================================================
# PERSONA FORM
# =====================================================
class PersonaForm(forms.ModelForm):

    class Meta:
        model = Personas

        fields = [
            "cuil",
            "dni",
            "apellido",
            "nombre",
            "sexo",
            "provincia",
            "localidad",
            "codigo_area",
            "telefono",
            "whatsapp",
        ]

        widgets = {

            "cuil": forms.TextInput(attrs={
                "class": "form-control",
                "maxlength": 11,
                "autocomplete": "off",
            }),

            "dni": forms.TextInput(attrs={
                "class": "form-control",
                "maxlength": 8,
                "autocomplete": "off",
            }),

            "apellido": forms.TextInput(attrs={
                "class": "form-control",
                "autocomplete": "off",
            }),

            "nombre": forms.TextInput(attrs={
                "class": "form-control",
                "autocomplete": "off",
            }),

            "telefono": forms.TextInput(attrs={
                "class": "form-control",
                "maxlength": 8,
                "autocomplete": "off",
            }),

        }

    # =====================================================
    # INIT
    # =====================================================
    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)

        # ==========================================
        # LOCALIDADES VACIAS INICIALMENTE
        # ==========================================
        self.fields["localidad"].queryset = Localidades.objects.none()

        # ==========================================
        # CODIGOS AREA
        # ==========================================
        self.fields["codigo_area"].queryset = (
            CodAreasTelefonos.objects
            .only("id", "codigo", "localidad")
            .order_by("codigo")
        )

        # ==========================================
        # CUANDO VIENE POST
        # ==========================================
        if "provincia" in self.data:

            try:

                provincia_id = self.data.get("provincia")

                self.fields["localidad"].queryset = (
                    Localidades.objects
                    .filter(c_provincia_id=provincia_id)
                    .order_by("descrip_localidad")
                )

            except (ValueError, TypeError):

                pass

        # =================================================
        # EDICION
        # =================================================
        if self.instance and self.instance.pk:

            if self.instance.provincia_id:

                self.fields["localidad"].queryset = (
                    Localidades.objects.filter(
                        c_provincia_id=self.instance.provincia_id
                    ).order_by("descrip_localidad")
                )

    # =====================================================
    # VALIDACIONES
    # =====================================================
    def clean_cuil(self):

        cuil = self.cleaned_data.get("cuil")

        if cuil:
            cuil = ''.join(filter(str.isdigit, cuil))

        return cuil

    def clean_dni(self):

        dni = self.cleaned_data.get("dni")

        if dni:
            dni = ''.join(filter(str.isdigit, dni))

        return dni

    def clean_apellido(self):

        apellido = self.cleaned_data.get("apellido", "")

        apellido = (
            apellido
            .upper()
            .strip()
        )

        return " ".join(apellido.split())

    def clean_nombre(self):

        nombre = self.cleaned_data.get("nombre", "")

        nombre = (
            nombre
            .upper()
            .strip()
        )

        return " ".join(nombre.split())
    

# =====================================================
# ACTIVIDAD FORM
# =====================================================
class ActividadForm(forms.ModelForm):

    cueanexo = forms.ChoiceField(
        choices=[],
        required=True
    )

    class Meta:

        model = RegistroActividades

        exclude = (
            "persona",
            "usuario_creacion",
            "usuario_modificacion",
        )

        widgets = {

            "f_desde": forms.DateInput(attrs={
                "type": "date"
            }),

            "f_hasta": forms.DateInput(attrs={
                "type": "date"
            }),
            "f_desde_funciones": forms.DateInput(attrs={
                "type": "date"
            }),

            "f_hasta_funciones": forms.DateInput(attrs={
                "type": "date"
            }),

        }    
    


# =====================================================
# BASE FORMSET
# =====================================================
class BaseActividadFormSet(BaseInlineFormSet):

    def __init__(self, *args, **kwargs):

        self.user = kwargs.pop("user", None)

        super().__init__(*args, **kwargs)
        
        self._cue_choices = []
        
        if self.user:

            self._cue_choices = [
                (x.cueanexo, x.cueanexo)
                for x in get_ofertas_usuario(self.user)
            ]

    
    # =================================================
    # CONSTRUCT FORM
    # =================================================
    def _construct_form(self, i, **kwargs):

        form = super()._construct_form(i, **kwargs)

        form.fields["cueanexo"].choices = self._cue_choices

        return form

    # =================================================
    # EMPTY FORM
    # =================================================
    @property
    def empty_form(self):

        form = super().empty_form

        form.fields["cueanexo"].choices = self._cue_choices

        return form


# =====================================================
# INLINE FORMSET
# =====================================================
ActividadFormSet = inlineformset_factory(
    Personas,
    RegistroActividades,
    form=ActividadForm,
    formset=BaseActividadFormSet,
    extra=1,
    can_delete=True
)