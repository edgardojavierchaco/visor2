from django import forms
from django.forms import inlineformset_factory, BaseInlineFormSet

from .models import Personas, RegistroActividades, Localidades, CodAreasTelefonos
from apps.consultasge.models_padron import CapaUnicaOfertas
from .utils import get_cueanexos_usuario


# =========================
# PERSONA
# =========================
class PersonaForm(forms.ModelForm):

    class Meta:
        model = Personas
        fields = "__all__"
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # 🔥 importante: arrancar vacío
        self.fields["localidad"].queryset = Localidades.objects.none()
        
        self.fields["codigo_area"].queryset = (
            CodAreasTelefonos.objects
            .only("codigo", "localidad")
            .order_by("codigo")
        )


# =========================
# ACTIVIDAD FORM
# =========================
class ActividadForm(forms.ModelForm):

    cueanexo = forms.ModelChoiceField(
        queryset=CapaUnicaOfertas.objects.none(),  # placeholder inicial
        to_field_name="cueanexo",
        required=True
    )

    class Meta:
        model = RegistroActividades
        exclude = ("persona",)
        widgets = {
            "f_desde": forms.DateInput(attrs={"type": "date"}),
            "f_hasta": forms.DateInput(attrs={"type": "date"}),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)

        # 🔥 seguridad: si no hay user, no hay datos
        if user is None:            
            return
        
        if user:

            cueanexos = get_cueanexos_usuario(user)

            self.fields["cueanexo"].queryset = CapaUnicaOfertas.objects.filter(
                cueanexo__in=cueanexos
            )

        else:
            self.fields["cueanexo"].queryset = CapaUnicaOfertas.objects.none()


# =========================
# BASE FORMSET
# =========================
class BaseActividadFormSet(BaseInlineFormSet):
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

    def _construct_form(self, i, **kwargs):
        kwargs["user"] = self.user
        return super()._construct_form(i, **kwargs)


# =========================
# INLINE FORMSET
# =========================
ActividadFormSet = inlineformset_factory(
    Personas,
    RegistroActividades,
    form=ActividadForm,
    formset=BaseActividadFormSet,
    extra=1,
    can_delete=True
)