from django import forms
from .models import Consulta

class ConsultaForm(forms.ModelForm):
    class Meta:
        model = Consulta
        fields = ['cueanexo', 'regional', 'nivel_modalidad', 'sge_modulo', 'apellido_nombre', 'email', 'mensaje']
        widgets = {
            'cueanexo': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: 220093000'}),
            'regional': forms.Select(attrs={'class': 'form-control'}),
            'nivel_modalidad': forms.Select(attrs={'class': 'form-control'}),
            'sge_modulo': forms.Select(attrs={'class': 'form-control'}),
            'apellido_nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'mensaje': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
        }

