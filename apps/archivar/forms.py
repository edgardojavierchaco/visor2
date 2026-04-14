from django import forms
from django.forms import *
from .models import ArchRegister, ArchModelosEvaluacion

class ArchRegisterForm(ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args,**kwargs)
        self.fields['cueanexo'].widget.attrs['autofocus']=True
        
    class Meta:
        model = ArchRegister
        fields = '__all__'
        widgets= {
            'cueanexo': TextInput(
                attrs={
                    'placeholder': 'Ingrese un Cueanexo',
                }
            ),
            'asunto': Select(
                attrs={
                    'class': 'form-control select2',
                    'placeholder': 'Seleccione Asunto',
                }
            ),
            'nivel': Select(
                attrs={
                    'class': 'form-control select2',
                    'placeholder': 'Seleccione Nivel',
                }
            ),
            't_norma': Select(
                attrs={
                    'class': 'form-control select2',
                    'placeholder': 'Seleccione Tipo Norma',
                }
            ),
            'nro_normativa': TextInput(
                attrs={
                    'placeholder': 'Ingrese un Número Norma',
                }
            ),
            'anio': NumberInput(
                attrs={
                    'placeholder': 'Ingrese un año',
                }
            ),
            'descripcion': Textarea(attrs={
                'rows':2,
                'cols':30,
                'style':'resize:both;',
            }),
            'archivo': FileInput(
                attrs={
                    'placeholder': 'Suba el archivo',
                }
            ),
            'ruta': TextInput(
                attrs={
                    'placeholder': 'ruta',
                }
            ),
        }


class ArchModelosEvaluacionForm(ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args,**kwargs)
        self.fields['asunto'].widget.attrs['autofocus']=True
        
    class Meta:
        model = ArchModelosEvaluacion
        fields = '__all__'
        widgets= {            
            'asunto': Select(
                attrs={
                    'class': 'form-control select2',
                    'placeholder': 'Seleccione Asunto',
                }
            ),
            'nivel': Select(
                attrs={
                    'class': 'form-control select2',
                    'placeholder': 'Seleccione Nivel',
                }
            ),
            't_eval': Select(
                attrs={
                    'class': 'form-control select2',
                    'placeholder': 'Seleccione Tipo Evaluacion',
                }
            ),
            'mes': Select(
                attrs={
                    'class': 'form-control select2',
                    'placeholder': 'Seleccione Mes',
                }
            ),
            'anio': NumberInput(
                attrs={
                    'placeholder': 'Ingrese un año',
                }
            ),
            'descripcion': Textarea(attrs={
                'rows':2,
                'cols':30,
                'style':'resize:both;',
            }),
            'archivo': FileInput(
                attrs={
                    'placeholder': 'Suba el archivo',
                }
            ),
            'ruta': TextInput(
                attrs={
                    'placeholder': 'ruta',
                }
            ),
        }
