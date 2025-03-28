import email
from django.forms import *
from django import forms
from .models import CargosCeicUegp, FuncionesDocUegp, EscalafonUegp, PersonalDocUegp, PersonalNoDocUegp

class PersonalDocUegpForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Enfocar en el campo 'T_DNI' al cargar el formulario
        self.fields['t_dni'].widget.attrs['autofocus'] = True
        self.fields['f_nac'].initial = self.instance.f_nac
        self.fields['f_designacion'].initial = self.instance.f_designacion
        self.fields['f_desde'].initial = self.instance.f_desde
        self.fields['f_hasta'].initial = self.instance.f_hasta
            
        # Si se ha seleccionado un nivelmod, carga los niveles correspondientes
        if 'nivelmod' in self.data:
            try:
                nivelmod_id = self.data.get('nivelmod')
                self.fields['cargo'].queryset = CargosCeicUegp.objects.filter(nivel=nivelmod_id).order_by('descripcion_ceic')
            except (ValueError, TypeError):
                pass  # Manejo de errores si `nivelmod` no es válido
        else:
            self.fields['cargo'].queryset = CargosCeicUegp.objects.none()

    class Meta:
        model = PersonalDocUegp
        fields = '__all__'
        widgets = {
            't_dni': forms.Select(attrs={'class': 'form-control select2', 'placeholder': 'Seleccione Tipo DNI'}),
            'dni': forms.TextInput(attrs={'placeholder': 'Ingrese DNI sin puntos', 'maxlength': '8'}),
            'cuil': forms.TextInput(attrs={'placeholder': 'Ingrese CUIL sin puntos ni guión medio', 'maxlength': '11'}),
            'apellido': forms.TextInput(attrs={'placeholder': 'Ingrese Apellido', 'style': 'text-transform: uppercase;'}),
            'nombres': forms.TextInput(attrs={'placeholder': 'Ingrese Nombres', 'style': 'text-transform: uppercase;'}),
            'f_nac': forms.DateInput(attrs={'type': 'date', 'placeholder': 'Ingrese fecha nacimiento'}),
            'sexo': forms.Select(attrs={'class': 'form-control select2', 'placeholder': 'Seleccione sexo'}),
            'nivelmod': forms.Select(attrs={'class': 'form-control select2', 'placeholder': 'Seleccione Nivel-Modalidad'}),
            'sector': forms.Select(attrs={'class': 'form-control select2', 'placeholder': 'Seleccione Sector'}),
            'cargo': forms.Select(attrs={'class': 'form-control select2', 'placeholder': 'Seleccione Cargo'}),
            'sit_revista': forms.Select(attrs={'class': 'form-control select2', 'placeholder': 'Seleccione Situación de Revista'}),
            'f_designacion': forms.DateInput(attrs={'type': 'date', 'placeholder': 'Ingrese fecha designación'}),
            'subvencionado': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'nom_funcion': forms.Select(attrs={'class': 'form-control select2', 'placeholder': 'Seleccione función'}),
            'f_desde': forms.DateInput(attrs={'type': 'date', 'placeholder': 'Ingrese fecha ingreso en la función'}),
            'f_hasta': forms.DateInput(attrs={'type': 'date', 'placeholder': 'Ingrese fecha finalización en la función'}),
            'carga_horaria_sem': forms.TextInput(
                attrs={
                    'placeholder': 'Ingrese Carga Horaria Semanal',
                    'style': 'text-transform: uppercase;',
                    'pattern': r'^\d{1,2}(\.\d{1,2})?$',
                    'title': 'Ingrese un número con hasta 2 enteros y 2 decimales (ej: 99.99)',
                }
            ),
            'email': forms.EmailInput(attrs={'placeholder': 'Ingrese email'}),
            'telefono': forms.TextInput(attrs={'placeholder': 'Ingrese teléfono'}),
            'region': forms.Select(attrs={'class': 'form-control select2', 'placeholder': 'Seleccione Región'}),
            'cueanexo': forms.TextInput(attrs={'type': 'hidden'}),
        }

    def save(self, commit=True):
        # Guardar el formulario con las posibles modificaciones
        instance = super().save(commit=False)
        
        # Guardar los datos si es necesario
        if commit:
            instance.save()
        
        return instance


class PersonalNoDocUegpForm(ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Enfocar en el campo 'T_DNI' al cargar el formulario
        self.fields['t_dni'].widget.attrs['autofocus'] = True
        self.fields['f_nac'].initial = self.instance.f_nac
        self.fields['f_designacion'].initial = self.instance.f_designacion
        self.fields['f_desde'].initial = self.instance.f_desde
        self.fields['f_hasta'].initial = self.instance.f_hasta
    
    class Meta:
        model = PersonalNoDocUegp
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
            'subvencionado': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
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
            'cueanexo': TextInput(
                attrs={
                    'type': 'hidden',
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