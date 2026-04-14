from django import forms
from .models import Consulta, ConsultaRenpe, ConsultaDocentesRenpe

class ConsultaForm(forms.ModelForm):
    class Meta:
        model = Consulta
        fields = ['cueanexo', 'regional', 'nivel_modalidad', 'sge_modulo', 'sge_rol','apellido_nombre', 'email', 'mensaje']
        widgets = {
            'cueanexo': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: 220093000'}),
            'regional': forms.Select(attrs={'class': 'form-control'}),
            'nivel_modalidad': forms.Select(attrs={'class': 'form-control'}),
            'sge_modulo': forms.Select(attrs={'class': 'form-control'}),
            'sge_rol': forms.Select(attrs={'class': 'form-control'}),
            'apellido_nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'mensaje': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
        }

class ConsultaRenpeForm(forms.ModelForm):
    class Meta:
        model = ConsultaRenpe
        fields = ['cueanexo', 'regional', 'renpe_modulo', 'apellido_nombre', 'email', 'mensaje']
        widgets = {
            'cueanexo': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: 220093000'}),
            'regional': forms.Select(attrs={'class': 'form-control'}),
            'renpe_modulo': forms.Select(attrs={'class': 'form-control'}),
            'apellido_nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'mensaje': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
        }


class ConsultaDocentesRenpeForm(forms.ModelForm):
    class Meta:
        model = ConsultaDocentesRenpe
        exclude = ['estado', 'estado_usuario', 'estado_fecha']
        widgets = {
            "apellido": forms.TextInput(attrs={"class": "form-control"}),
            "nombre": forms.TextInput(attrs={"class": "form-control"}),
            "cuil": forms.TextInput(attrs={"class": "form-control", "maxlength": "11"}),
            "categoria": forms.Select(attrs={"class": "form-select"}),
            "cuenta_miargentina": forms.Select(attrs={"class": "form-select"}),
            "ingreso_miargentina": forms.Select(attrs={"class": "form-select"}),
            "reseteo_contraseña_miargentina": forms.Select(attrs={"class": "form-select"}),
            "formulario_sin_miargentina": forms.Select(attrs={"class": "form-select"}),
            "email": forms.EmailInput(attrs={"class": "form-control"}),
            "mensaje": forms.Textarea(attrs={"class": "form-control", "rows": 4}),
            "imagen": forms.ClearableFileInput(attrs={"class": "form-control"}),
        }
