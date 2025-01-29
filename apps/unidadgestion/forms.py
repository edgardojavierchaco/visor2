import email
from django.forms import *
from .models import CargosCeic, FuncionesDoc, EscalafonAdmin, PersonalDocCentral, PersonalNoDocCentral

class PersonalDocCentralForm(ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Enfocar en el campo 'T_DNI' al cargar el formulario
        self.fields['t_dni'].widget.attrs['autofocus'] = True

# Si se ha seleccionado un nivelmod, carga las localidades correspondientes
        if 'nivelmod' in self.data:
            try:
                nivelmod_id = self.data.get('nivelmod')
                self.fields['cargo'].queryset = CargosCeic.objects.filter(nivel=nivelmod_id).order_by('descripcion_ceic')
            except (ValueError, TypeError):
                pass  # Manejo de errores si `nivelmod` no es válido
        else:
            self.fields['cargo'].queryset = CargosCeic.objects.none()
    
    class Meta:
        model = PersonalDocCentral
        fields = '__all__'
        widgets = {
            't_dni': Select(
                attrs={
                    'class': 'form-control select2',
                    'placeholder': 'Seleccione Tipo DNI',
                }
            ),
            'dni': TextInput(
                attrs={
                    'placeholder': 'Ingrese DNI sin puntos',
                    'maxleght': '8',
                }
            ),
            'cuil': TextInput(
                attrs={
                    'placeholder': 'Ingrese CUIL sin puntos ni guión medio',
                    'maxleght': '11',
                }
            ),
            'apellido': TextInput(
                attrs={
                    'placeholder': 'Ingrese Apellido',
                    'style': 'text-transform: uppercase;'
                }
            ),
            'nombres': TextInput(
                attrs={
                    'placeholder': 'Ingrese Nombres',
                    'style': 'text-transform: uppercase;',
                }
            ),
            'f_nac': DateInput(
                attrs={
                    'type': 'date',
                    'placeholder': 'Ingrese fecha nacimiento',
                }
            ),
            'sexo': Select(
                attrs={
                    'class':'form-control select2',
                    'placeholder': 'Seleccione sexo',
                }
            ),
            'nivelmod': Select(
                attrs={
                    'class':'form-control select2',
                    'placeholder': 'Seleccione Nivel-Modalidad',
                }
            ),
            'sector': Select(
                attrs={
                    'class':'form-control select2',
                    'placeholder': 'Seleccione Sector',
                }
            ),
            'cargo': Select(
                attrs={
                    'class':'form-control select2',
                    'placeholder': 'Seleccione Cargo',
                }
            ),
            'sit_revista': Select(
                attrs={
                    'class':'form-control select2',
                    'placeholder': 'Seleccione Situación de Revista',
                }
            ),
            'f_designacion': DateInput(
                attrs={
                    'type': 'date',
                    'placeholder': 'Ingrese fecha designación',
                }
            ),
            'nom_funcion': Select(
                attrs={
                    'class':'form-control select2',
                    'placeholder': 'Seleccione función',
                }
            ),
            'f_desde': DateInput(
                attrs={
                    'type': 'date',
                    'placeholder': 'Ingrese fecha ingreso en la función',
                }
            ),
            'f_hasta': DateInput(
                attrs={
                    'type': 'date',
                    'placeholder': 'Ingrese fecha finalización en la función',
                }
            ),
            'carga_horaria_sem': TextInput(
                attrs={
                    'placeholder': 'Ingrese Carga Horaria Semanal',
                    'style': 'text-transform: uppercase;',
                    'pattern': r'^\d{1,2}(\.\d{1,2})?$',
                    'title': 'Ingrese un número con hasta 2 enteros y 2 decimales (ej: 99.99)',
                }
            ),
            'cuof': TextInput(
                attrs={
                    'placeholder':'Ingrese CUOF',
                    'maxlenght':'4',
                }
            ),
            'cuof_anexo': TextInput(
                attrs={
                    'placeholder':'Ingrese anexo CUOF',
                    'maxlenght':'2',
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


class PersonalNoDocCentralForm(ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Enfocar en el campo 'T_DNI' al cargar el formulario
        self.fields['t_dni'].widget.attrs['autofocus'] = True

    
    class Meta:
        model = PersonalNoDocCentral
        fields = '__all__'
        widgets = {
            't_dni': Select(
                attrs={
                    'class': 'form-control select2',
                    'placeholder': 'Seleccione Tipo DNI',
                }
            ),
            'dni': TextInput(
                attrs={
                    'placeholder': 'Ingrese DNI sin puntos',
                    'maxleght': '8',
                }
            ),
            'cuil': TextInput(
                attrs={
                    'placeholder': 'Ingrese CUIL sin puntos ni guión medio',
                    'maxleght': '11',
                }
            ),
            'apellido': TextInput(
                attrs={
                    'placeholder': 'Ingrese Apellido',
                    'style': 'text-transform: uppercase;'
                }
            ),
            'nombres': TextInput(
                attrs={
                    'placeholder': 'Ingrese Nombres',
                    'style': 'text-transform: uppercase;',
                }
            ),
            'f_nac': DateInput(
                attrs={
                    'type': 'date',
                    'placeholder': 'Ingrese fecha nacimiento',
                }
            ),
            'sexo': Select(
                attrs={
                    'class':'form-control select2',
                    'placeholder': 'Seleccione sexo',
                }
            ),
            'categoria': Select(
                attrs={
                    'class':'form-control select2',
                    'placeholder': 'Seleccione Categoría',
                }
            ),            
            'sit_nom': Select(
                attrs={
                    'class':'form-control select2',
                    'placeholder': 'Seleccione Situación de Revista',
                }
            ),
            'f_designacion': DateInput(
                attrs={
                    'type': 'date',
                    'placeholder': 'Ingrese fecha designación',
                }
            ),
            'nom_funcion': Select(
                attrs={
                    'class':'form-control select2',
                    'placeholder': 'Seleccione función',
                }
            ),
            'f_desde': DateInput(
                attrs={
                    'type': 'date',
                    'placeholder': 'Ingrese fecha ingreso en la función',
                }
            ),
            'f_hasta': DateInput(
                attrs={
                    'type': 'date',
                    'placeholder': 'Ingrese fecha finalización en la función',
                }
            ),
            'carga_horaria_sem': TextInput(
                attrs={
                    'placeholder': 'Ingrese Carga Horaria Semanal',
                    'style': 'text-transform: uppercase;',
                    'pattern': r'^\d{1,2}(\.\d{1,2})?$',
                    'title': 'Ingrese un número con hasta 2 enteros y 2 decimales (ej: 99.99)',
                }
            ),
            'cuof': TextInput(
                attrs={
                    'placeholder':'Ingrese CUOF',
                    'maxlenght':'4',
                }
            ),
            'cuof_anexo': TextInput(
                attrs={
                    'placeholder':'Ingrese anexo CUOF',
                    'maxlenght':'2',
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