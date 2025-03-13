from django import forms
from django.core.validators import MinValueValidator
from django.core.exceptions import ValidationError
from shapely import length

from .models import (
    DatosEscuela, DominioEscuela, EspaciosPedagogicos,
    Sanitarios, Accesibilidad, Seguridad, Departamento, Localidad
)


# Formulario para Datos Escuela
class DatosEscuelaForm(forms.ModelForm):            
    class Meta:
        model = DatosEscuela
        fields = '__all__'
        widgets = {
            'cueanexo': forms.TextInput(attrs={'class': 'form-control', 'max_length': '10', 'style': 'width: 100px; text-align: center;'}),
            'nom_est': forms.TextInput(attrs={'class': 'form-control', 'style': 'width: 100px; text-align: center;'}),
            'calle': forms.TextInput(attrs={'class': 'form-control'}),
            'nro': forms.NumberInput(attrs={'class': 'form-control', 'max_length': '4', 'style': 'width: 100px; text-align: center;'}),
            'circ': forms.TextInput(attrs={'class': 'form-control', 'max_length': '5', 'style': 'width: 100px; text-align: center;'}),
            'mz': forms.TextInput(attrs={'class': 'form-control', 'max_length': '5', 'style': 'width: 100px; text-align: center;'}),
            'pc': forms.TextInput(attrs={'class': 'form-control', 'max_length': '5', 'style': 'width: 100px; text-align: center;'}),
            'departamento': forms.TextInput(attrs={'class': 'form-control'}),
            'localidad': forms.TextInput(attrs={'class': 'form-control'}),
            'anio_edif': forms.NumberInput(attrs={'class': 'form-control', 'max_length': '5', 'style': 'width: 100px; text-align: center;'}),
            'patrimonio': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'antiguedad': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Ingrese antigüedad en años'}),
            'dist_munic': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': 'Distancia al municipio'}),
            'dist_tierra': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': 'Distancia en camino de tierra'}),
            'dist_pavim': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': 'Distancia en pavimento'}),
        }
    

# Dominio Escuela
class DominioEscuelaForm(forms.ModelForm):            
    class Meta:
        model = DominioEscuela
        fields = '__all__'
        widgets = {
            'cueanexo': forms.TextInput(attrs={'class': 'form-control', 'max_length': '10', 'style': 'width: 100px; text-align: center;'}),
            'mes':forms.Select(attrs={'class':'form-control'}),
            'anio': forms.NumberInput(attrs={'class':'form-control', 'max_length': '10', 'style': 'width: 100px; text-align: center;'}),
            'dominio':forms.Select(attrs={'class': 'form-control'}),
            'plan_const':forms.TextInput(attrs={'class':'form-control'}),
            'ampliacion':forms.NumberInput(attrs={'class':'form-control', 'max_length': '10', 'style': 'width: 100px; text-align: center;'}),
            'plan_ampl':forms.TextInput(attrs={'class':'form-control'}),
            'sup_terreno': forms.NumberInput(attrs={'class':'form-control','max_length': '10', 'style': 'width: 100px; text-align: center;'}),
            'sup_cub': forms.NumberInput(attrs={'class':'form-control','max_length': '10', 'style': 'width: 100px; text-align: center;'}),
            
        }
    

# Espacios Pedagógicos
class EspaciosPedagogicosForm(forms.ModelForm):            
    class Meta:
        model = EspaciosPedagogicos
        fields = '__all__'
        widgets = {
            'cueanexo': forms.TextInput(attrs={'class': 'form-control', 'max_length': '10', 'style': 'width: 100px; text-align: center;'}),
            'mes':forms.Select(attrs={'class':'form-control'}),
            'anio': forms.NumberInput(attrs={'class':'form-control', 'max_length': '10', 'style': 'width: 100px; text-align: center;'}),
            'aulas_comunes':forms.NumberInput(attrs={'class':'form-control', 'max_length': '10', 'style': 'width: 100px; text-align: center;'}),
            'aulas_aire':forms.NumberInput(attrs={'class':'form-control', 'max_length': '10', 'style': 'width: 100px; text-align: center;'}),
            'sum':forms.NumberInput(attrs={'class':'form-control', 'max_length': '5', 'style': 'width: 100px; text-align: center;'}),
            'laboratorio':forms.NumberInput(attrs={'class':'form-control', 'max_length': '5', 'style': 'width: 100px; text-align: center;'}),
            'playon_depo':forms.NumberInput(attrs={'class':'form-control', 'max_length': '5', 'style': 'width: 100px; text-align: center;'}),
        }


# Sanitarios
class SanitariosForm(forms.ModelForm):            
    class Meta:
        model = Sanitarios
        fields = '__all__'
        widgets = {
            'cueanexo': forms.TextInput(attrs={'class': 'form-control', 'max_length': '10', 'style': 'width: 100px; text-align: center;'}),
            'mes':forms.Select(attrs={'class':'form-control'}),
            'anio': forms.NumberInput(attrs={'class':'form-control', 'max_length': '10', 'style': 'width: 100px; text-align: center;'}),
            'bebederos':forms.NumberInput(attrs={'class':'form-control', 'max_length': '10', 'style': 'width: 100px; text-align: center;'}),
            'inodoros':forms.NumberInput(attrs={'class':'form-control', 'max_length': '10', 'style': 'width: 100px; text-align: center;'}),
            'lavatorios':forms.NumberInput(attrs={'class':'form-control', 'max_length': '5', 'style': 'width: 100px; text-align: center;'}),
            'mingitorios':forms.NumberInput(attrs={'class':'form-control', 'max_length': '5', 'style': 'width: 100px; text-align: center;'}),
            'bidet':forms.NumberInput(attrs={'class':'form-control', 'max_length': '5', 'style': 'width: 100px; text-align: center;'}),
            'letrinas':forms.NumberInput(attrs={'class':'form-control', 'max_length': '5', 'style': 'width: 100px; text-align: center;'}),
        }
        

# Accesibilidad
class AccesibilidadForm(forms.ModelForm):            
    class Meta:
        model = Accesibilidad
        fields = '__all__'
        widgets = {
            'cueanexo': forms.TextInput(attrs={'class': 'form-control', 'max_length': '10', 'style': 'width: 100px; text-align: center;'}),
            'mes':forms.Select(attrs={'class':'form-control'}),
            'anio': forms.NumberInput(attrs={'class':'form-control', 'max_length': '10', 'style': 'width: 100px; text-align: center;'}),
            'sanitarios':forms.NumberInput(attrs={'class':'form-control', 'max_length': '10', 'style': 'width: 100px; text-align: center;'}),
            'asensores':forms.NumberInput(attrs={'class':'form-control', 'max_length': '10', 'style': 'width: 100px; text-align: center;'}),
            'montacargas':forms.NumberInput(attrs={'class':'form-control', 'max_length': '5', 'style': 'width: 100px; text-align: center;'}),
            'escaleras':forms.NumberInput(attrs={'class':'form-control', 'max_length': '5', 'style': 'width: 100px; text-align: center;'}),
            'rampas':forms.NumberInput(attrs={'class':'form-control', 'max_length': '5', 'style': 'width: 100px; text-align: center;'}),
        }


