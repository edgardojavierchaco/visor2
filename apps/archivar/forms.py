from django import forms
from .models import ArchRegister

class ArchRegisterForm(forms.ModelForm):
    class Meta:
        model = ArchRegister
        fields = ['cueanexo', 'asunto', 'nro_normativa', 'descripcion', 'archivo']
