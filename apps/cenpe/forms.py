from django import forms
from .models import Datos_Personal_Cenpe, provincia_tipo

class DatosPersonalCenpeForm(forms.ModelForm):
    prov_nac = forms.ModelChoiceField(
        queryset=provincia_tipo.objects.all(),
        widget=forms.Select(attrs={'class': 'form-control select2'})
    )

    class Meta:
        model = Datos_Personal_Cenpe
        fields = '__all__'
        widgets = {
            'usuario': forms.HiddenInput(),  # Oculta el campo usuario en el formulario
        }

