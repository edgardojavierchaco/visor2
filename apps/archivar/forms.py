from django import forms
from .models import ArchRegister

class ArchRegisterForm(forms.ModelForm):
    class Meta:
        model = ArchRegister
        fields = ['cueanexo', 'asunto', 'nivel', 't_norma','nro_normativa', 'año', 'descripcion', 'archivo']
        widgets= {
            'descripcion': forms.Textarea(attrs={
                'rows':2,
                'cols':30,
                'style':'resize:both;',
            }),
        }