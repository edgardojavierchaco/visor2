from django import forms
from .models import DocenteFrenteGrado


class DocenteFrenteGradoForm(forms.ModelForm):

    class Meta:
        model = DocenteFrenteGrado
        fields = '__all__'
        widgets = {
            'cueanexo': forms.TextInput(attrs={
                'id': 'cueanexo',
                'autocomplete': 'off'
            }),
            'cuil_docente': forms.TextInput(attrs={
                'id': 'cuil_docente',
                'autocomplete': 'off'
            }),
            'nom_est': forms.TextInput(attrs={
                'id': 'nom_est',
                'readonly': True
            }),
            'oferta': forms.TextInput(attrs={
                'id': 'oferta',
                'readonly': True
            }),
        }