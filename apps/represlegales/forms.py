import email
from django.forms import *
from .models import RepresentantesLegales, EscuelasRepresentadas, Asignacion

class EscuelasRepresentadasForm(ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args,**kwargs)
        self.fields['cueanexo'].widget.attrs['autofocus']=True
        
    class Meta:
        model=EscuelasRepresentadas
        fields='__all__'        
        widgets = {
            'cueanexo': TextInput(
                attrs={
                    'placeholder': 'Ingrese un Cueanexo',
                }
            ),
            'nom_est': TextInput(
                attrs={
                    'placeholder': 'Ingrese un nombre de escuela',                    
                }
            ),
            'oferta': TextInput(
                attrs={
                    'placeholder': 'Ingrese oferta',                    
                }
            ),
            'region': TextInput(
                attrs={
                    'placeholder': 'Ingrese una regional',                    
                }
            ),
            
        }

    def save(self, commit=True):
        data = {}
        form = super()
        try:
            if form.is_valid():
                form.save()
            else:
                data['error'] = form.errors
        except Exception as e:
            data['error'] = str(e)
        return data

class RepresentantesLegalesForm(ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['dni'].widget.attrs['autofocus'] = True
        
    class Meta:
        model = RepresentantesLegales
        fields = '__all__'
        widgets = {
            'dni': TextInput(
                attrs={
                    'placeholder': 'Ingrese un DNI sin puntos',
                    'maxlength': '8'
                }
            ),
            'cuil': TextInput(
                attrs={
                    'placeholder': 'Ingrese un CUIL',
                    'maxlength': '11'
                }
            ),
            'apellido': TextInput(
                attrs={
                    'placeholder': 'Ingrese apellidos',
                    'style': 'text-transform: uppercase;'
                }
            ),
            'nombres': TextInput(
                attrs={
                    'placeholder': 'Ingrese nombres',
                    'style': 'text-transform: uppercase;'
                }
            ),
            'f_nac': DateInput(
                attrs={
                    'type': 'date',
                    'placeholder': 'Ingrese Fecha de Nacimiento',
                }
            ),
            'sexo': Select(
                attrs={
                    'class': 'form-control select2',
                    'placeholder': 'Seleccione sexo',
                }
            ),
            'sit_revista': Select(
                attrs={
                    'class': 'form-control select2',
                    'placeholder': 'Seleccione Situación de Revista',
                }
            ),
            'f_designacion': DateInput(
                attrs={
                    'type': 'date',
                    'placeholder': 'Ingrese Fecha de Designación',
                }
            ),            
            'email': EmailInput(
                attrs={
                    'placeholder': 'Ingrese email',
                    }),
            'telefono': TextInput(
                attrs={
                    'placeholder': 'Ingrese teléfono',
                }
            ),
            'region': Select(
                attrs={
                    'class': 'form-control select2',
                    'placeholder': 'Seleccione Región',
                }
            ),
        }
    
    def save(self, commit=True):
        data = {}
        form = super()
        try:
            if form.is_valid():
                form.save()
            else:
                data['error'] = form.errors
        except Exception as e:
            data['error'] = str(e)
        return data


class AsignacionForm(ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    class Meta:
        model = Asignacion
        fields = '__all__'
        widgets = {
            'replegales': Select(attrs={
                'class': 'form-control select2',
                'style': 'width: 100%'
            }),            
            'total': TextInput(attrs={
                'readonly': True,
                'class': 'form-control',
            })
        }