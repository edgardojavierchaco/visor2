import email
from django.forms import *
from .models import Supervisor, EscuelasSupervisadas, Asignacion

class EscuelasSupervisadasForm(ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args,**kwargs)
        self.fields['cueanexo'].widget.attrs['autofocus']=True
        
    class Meta:
        model=EscuelasSupervisadas
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

class SupervisorForm(ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['dni'].widget.attrs['autofocus'] = True
        
    class Meta:
        model = Supervisor
        fields = '__all__'
        widgets = {
            'dni': TextInput(
                attrs={
                    'placeholder': 'Ingrese un DNI',
                    'maxlength': '8'
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
                    'placeholder': 'Ingrese teléfono',
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
            'supervisor': Select(attrs={
                'class': 'form-control select2',
                'style': 'width: 100%'
            }),            
            'total': TextInput(attrs={
                'readonly': True,
                'class': 'form-control',
            })
        }