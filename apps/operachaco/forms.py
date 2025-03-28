from django import forms
from django.core.validators import MinValueValidator
from django.core.exceptions import ValidationError
from shapely import length
from .models import (
    CategoriasEvaluacion,
    ExamenAlumnoCueanexoL,
)


class ExamenAlumnoCueanexoLForm(forms.ModelForm):
    class Meta:
        model = ExamenAlumnoCueanexoL
        fields = '__all__'
        widgets = {
            'dni_alumno': forms.TextInput(attrs={'class': 'form-control','max_length':'15', 
                'style': 'width: 100px; text-align: center;'}),
            'apellidos':forms.TextInput(attrs={'class': 'form-control','max_length':'255', 
                'style': 'width: 100px; text-align: center;'}),
            'nombres':forms.TextInput(attrs={'class': 'form-control','max_length':'255', 
                'style': 'width: 100px; text-align: center;'}),
            'cueanexo':forms.TextInput(attrs={'class': 'form-control','max_length':'15', 
                'style': 'width: 100px; text-align: center;'}),
            'preg_1':forms.Select(attrs={'class': 'form-control'}),
            'v_1': forms.NumberInput(attrs={'class': 'form-control', 'max_length':'4', 
                'style': 'width: 100px; text-align: center;', 'readonly':'readonly'}),
            'preg_2':forms.Select(attrs={'class': 'form-control'}),
            'v_2': forms.NumberInput(attrs={'class': 'form-control', 'max_length':'4', 
                'style': 'width: 100px; text-align: center;', 'readonly':'readonly'}),
            'preg_3':forms.Select(attrs={'class': 'form-control'}),
            'v_3': forms.NumberInput(attrs={'class': 'form-control', 'max_length':'4', 
                'style': 'width: 100px; text-align: center;', 'readonly':'readonly'}),
            'preg_4':forms.Select(attrs={'class': 'form-control'}),
            'v_4': forms.NumberInput(attrs={'class': 'form-control', 'max_length':'4', 
                'style': 'width: 100px; text-align: center;', 'readonly':'readonly'}),
            'preg_5':forms.Select(attrs={'class': 'form-control'}),
            'v_5': forms.NumberInput(attrs={'class': 'form-control', 'max_length':'4', 
                'style': 'width: 100px; text-align: center;', 'readonly':'readonly'}),
            'preg_6':forms.Select(attrs={'class': 'form-control'}),
            'v_6': forms.NumberInput(attrs={'class': 'form-control', 'max_length':'4', 
                'style': 'width: 100px; text-align: center;', 'readonly':'readonly'}),
            'preg_7':forms.Select(attrs={'class': 'form-control'}),
            'v_7': forms.NumberInput(attrs={'class': 'form-control', 'max_length':'4', 
                'style': 'width: 100px; text-align: center;', 'readonly':'readonly'}),
            'preg_8':forms.Select(attrs={'class': 'form-control'}),
            'v_8': forms.NumberInput(attrs={'class': 'form-control', 'max_length':'4', 
                'style': 'width: 100px; text-align: center;', 'readonly':'readonly'}),
            'preg_9_p':forms.Select(attrs={'class': 'form-control'}),
            'v_9_p': forms.NumberInput(attrs={'class': 'form-control', 'max_length':'4', 
                'style': 'width: 100px; text-align: center;', 'readonly':'readonly'}),
            'preg_9_t':forms.Select(attrs={'class': 'form-control'}),
            'v_9_t': forms.NumberInput(attrs={'class': 'form-control', 'max_length':'4', 
                'style': 'width: 100px; text-align: center;', 'readonly':'readonly'}),
            'preg_9_o':forms.Select(attrs={'class': 'form-control'}),
            'v_9_o': forms.NumberInput(attrs={'class': 'form-control', 'max_length':'4', 
                'style': 'width: 100px; text-align: center;', 'readonly':'readonly'}),
            'preg_9_m':forms.Select(attrs={'class': 'form-control'}),
            'v_9_m': forms.NumberInput(attrs={'class': 'form-control', 'max_length':'4', 
                'style': 'width: 100px; text-align: center;', 'readonly':'readonly'}),
            
        }
                
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['preg_1'].queryset = CategoriasEvaluacion.objects.filter(cod_categ__range=(11,14))
        self.fields['preg_2'].queryset = CategoriasEvaluacion.objects.filter(cod_categ__range=(21,24)) 
        self.fields['preg_3'].queryset = CategoriasEvaluacion.objects.filter(cod_categ__range=(31,34))       
        self.fields['preg_4'].queryset = CategoriasEvaluacion.objects.filter(cod_categ__range=(41,44))
        self.fields['preg_5'].queryset = CategoriasEvaluacion.objects.filter(cod_categ__range=(51,54))
        self.fields['preg_6'].queryset = CategoriasEvaluacion.objects.filter(cod_categ__range=(61,64))
        self.fields['preg_7'].queryset = CategoriasEvaluacion.objects.filter(cod_categ__range=(71,74))
        self.fields['preg_8'].queryset = CategoriasEvaluacion.objects.filter(cod_categ__range=(81,84))
