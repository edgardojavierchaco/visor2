from django import forms
from .models import Datos_Personal_Cenpe, Estado_Civil_Cenpe, Gestion_Institucion_Cenpe, Nivel_Formacion_Cenpe, Tipo_Formacion_Cenpe, Tipo_Institucion_Cenpe, documento_tipo, nacionalidad, provincia_tipo, localidad_tipo, pais, Academica_Cenpe, sexo_tipo
import re

class DatosPersonalCenpeForm(forms.ModelForm):
    apellidos = forms.CharField(
        max_length=255,
        min_length=1,        
        widget=forms.TextInput (attrs={'class': 'form-control select2'}),
        error_messages={
        'max_length': 'El apellido no puede tener más de 255 caracteres.',
        'min_length': 'El apellido debe tener al menos 1 caracter.'
        }
    )
    
    nombres = forms.CharField(
        max_length=255,
        min_length=1,        
        widget=forms.TextInput (attrs={'class': 'form-control select2'}),
        error_messages={
        'max_length': 'El apellido no puede tener más de 255 caracteres.',
        'min_length': 'El apellido debe tener al menos 1 caracter.'
        }
    )
    
    pais_nac = forms.ModelChoiceField(
        queryset=pais.objects.all(),
        widget=forms.Select(attrs={'class': 'form-control select2'})
    )
    
    nacionalidad = forms.ModelChoiceField(
        queryset=nacionalidad.objects.all(),
        widget=forms.Select(attrs={'class': 'form-control select2'})
    )
    
    t_doc = forms.ModelChoiceField(
        queryset=documento_tipo.objects.all(),
        widget=forms.Select(attrs={'class': 'form-control select2'})
    )
    
    dni = forms.CharField(
        max_length=8,
        min_length=7,        
        widget=forms.TextInput (attrs={'class': 'form-control select2'}),
        error_messages={
        'max_length': 'El apellido no puede tener más de 8 dígitos.',
        'min_length': 'El apellido debe tener al menos 7 dígitos.'
        }
    )
    
    cuil = forms.CharField(
        max_length=11,
        min_length=10,        
        widget=forms.TextInput (attrs={'class': 'form-control select2'}),
        error_messages={
        'max_length': 'El apellido no puede tener más de 11 dígitos.',
        'min_length': 'El apellido debe tener al menos 10 dígitos.'
        }
    )
    
    sexo = forms.ModelChoiceField(
        queryset=sexo_tipo.objects.all(),
        widget=forms.Select(attrs={'class': 'form-control select2'})
    )
    
    estado_civil = forms.ModelChoiceField(
        queryset=Estado_Civil_Cenpe.objects.all(),
        widget=forms.Select(attrs={'class': 'form-control select2'})
    )
    
    nivel_form = forms.ModelChoiceField(
        queryset=Nivel_Formacion_Cenpe.objects.all(),
        widget=forms.Select(attrs={'class': 'form-control select2'}),
        help_text='Seleccionar máximo Nivel de Formación Alcanzado',
    )
    
    telfijo = forms.CharField(
        max_length=10,
        min_length=10,        
        widget=forms.TextInput (attrs={'class': 'form-control select2'}),
        error_messages={
        'max_length': 'El número de teléfono debe contener 10 dígitos sin anteponer 0 al código de área.',
        'min_length': 'El número de teléfono debe contener 10 dígitos sin anteponer 0 al código de área.'
        },
        help_text='Ej.: 3624123456',
    )
    
    celular = forms.CharField(
        max_length=10,
        min_length=10,        
        widget=forms.TextInput (attrs={'class': 'form-control select2'}),
        error_messages={
        'max_length': 'El número de teléfono debe contener 10 dígitos sin anteponer 0 al código de área.',
        'min_length': 'El número de teléfono debe contener 10 dígitos sin anteponer 0 al código de área.'
        },
        help_text='Ej.: 3734123456',
    )
    
    prov_nac = forms.ModelChoiceField(
        queryset=provincia_tipo.objects.all(),
        widget=forms.Select(attrs={'class': 'form-control select2'})
    )
    
    prov_resid = forms.ModelChoiceField(
        queryset=provincia_tipo.objects.all(),
        widget=forms.Select(attrs={'class': 'form-control select2'})
    )

    loc_nac = forms.ModelChoiceField(
        queryset=localidad_tipo.objects.none(),  # Inicialmente vacío
        widget=forms.Select(attrs={'class': 'form-control select2'})  # Select2 para loc_nac
    )
    
    f_nac = forms.DateField(
    widget=forms.DateInput(attrs={'class': 'form-control select2', 'type': 'date'})
    )
    
    loc_resid = forms.ModelChoiceField(
        queryset=localidad_tipo.objects.none(),  # Inicialmente vacío
        widget=forms.Select(attrs={'class': 'form-control select2'})  # Select2 para loc_resid
    )
    
    calle = forms.CharField(                
        widget=forms.TextInput (attrs={'class': 'form-control select2'}),        
    )
    
    nro = forms.CharField(                
        widget=forms.TextInput (attrs={'class': 'form-control select2'}),        
    )
    
    mz = forms.CharField(                
        widget=forms.TextInput (attrs={'class': 'form-control select2'}),        
    )
    
    pc = forms.CharField(                
        widget=forms.TextInput (attrs={'class': 'form-control select2'}),        
    )
    
    casa = forms.CharField(                
        widget=forms.TextInput (attrs={'class': 'form-control select2'}),        
    )
    
    piso = forms.CharField(                
        widget=forms.TextInput (attrs={'class': 'form-control select2'}),        
    )
    
    uf = forms.CharField(                
        widget=forms.TextInput (attrs={'class': 'form-control select2'}),        
    )
    
    barrio = forms.CharField(                
        widget=forms.TextInput (attrs={'class': 'form-control select2'}),        
    )

    class Meta:
        model = Datos_Personal_Cenpe
        fields = '__all__'
        widgets = {
            'usuario': forms.HiddenInput(),  # Oculta el campo usuario en el formulario
        }
        help_texts = {
            'dni': 'Ej. 12345678',
            'cuil': 'Ej. 20123456781',
            'telfijo': 'Ej. 3624412345',
            'celular': 'Ej. 3734412345',
            'nivel_form': 'Seleccionar máximo Nivel de Formación.',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Si hay una provincia de nacimiento seleccionada, carga las localidades correspondientes
        if 'prov_nac' in self.data:
            try:
                provincia_id = int(self.data.get('prov_nac'))
                print('provincia_id', provincia_id)  # Depuración
                self.fields['loc_nac'].queryset = localidad_tipo.objects.filter(c_provincia_id=provincia_id).order_by('descripcion_loc')
            except (ValueError, TypeError):
                pass  # Maneja los errores de valor y tipo
        elif self.instance.pk:
            # Si hay una instancia existente, muestra las localidades correspondientes a la provincia guardada
            self.fields['loc_nac'].queryset = localidad_tipo.objects.filter(c_provincia=self.instance.prov_nac).order_by('descripcion_loc')
        
        # Si hay una provincia de residencia seleccionada, carga las localidades correspondientes
        if 'prov_resid' in self.data:
            try:
                provincia2_id = int(self.data.get('prov_resid'))
                print('provincia2_id', provincia2_id)  # Depuración
                self.fields['loc_resid'].queryset = localidad_tipo.objects.filter(c_provincia_id=provincia2_id).order_by('descripcion_loc')
            except (ValueError, TypeError):
                pass  # Maneja los errores de valor y tipo
        elif self.instance.pk:
            # Si hay una instancia existente, muestra las localidades correspondientes a la provincia guardada
            self.fields['loc_resid'].queryset = localidad_tipo.objects.filter(c_provincia=self.instance.prov_resid).order_by('descripcion_loc')

    def clean_apellidos(self):
        # Asegura que apellidos esté en mayúsculas y solo contenga caracteres válidos
        apellidos = self.cleaned_data['apellidos'].upper()
        allowed_chars = re.compile(r"^[A-ZÁÉÍÓÚÑ' ]+$")
        if not allowed_chars.match(apellidos):
            raise forms.ValidationError(_('Solo se permiten letras mayúsculas, espacios, tildes y apóstrofes.'))
        return apellidos

    def clean_nombres(self):
        # Asegura que nombres esté en mayúsculas y solo contenga caracteres válidos
        nombres = self.cleaned_data['nombres'].upper()
        allowed_chars = re.compile(r"^[A-ZÁÉÍÓÚÑ' ]+$")
        if not allowed_chars.match(nombres):
            raise forms.ValidationError(_('Solo se permiten letras mayúsculas, espacios, tildes y apóstrofes.'))
        return nombres


class DatosAcademicosCenpeForm(forms.ModelForm):
    titulo = forms.CharField (
        max_length=255,
        min_length=1,        
        widget=forms.TextInput (attrs={'class': 'form-control select2'}),
        error_messages={
        'max_length': 'El título no puede tener más de 255 caracteres.',
        'min_length': 'El título debe tener al menos 1 caracter.'
    }
    )
    
    tipo_form = forms.ModelChoiceField(
        queryset=Tipo_Formacion_Cenpe.objects.all(),
        widget=forms.Select(attrs={'class': 'form-control select2'})
    )

    nivel_form = forms.ModelChoiceField(
        queryset=Nivel_Formacion_Cenpe.objects.all(),
        widget=forms.Select(attrs={'class': 'form-control select2'})
    )

    tipo_inst = forms.ModelChoiceField(
        queryset=Tipo_Institucion_Cenpe.objects.all(),
        widget=forms.Select(attrs={'class': 'form-control select2'})
    )

    gestion_inst = forms.ModelChoiceField(
        queryset=Gestion_Institucion_Cenpe.objects.all(),
        widget=forms.Select(attrs={'class': 'form-control select2'})
    )
    
    reg_nro = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control select2'})
    )
    
    f_egreso = forms.DateField(
    widget=forms.DateInput(attrs={'class': 'form-control select2', 'type': 'date'})
    )


    class Meta:
        model = Academica_Cenpe  # Nombre correcto del modelo
        fields = '__all__'
        widgets = {
            'usuario': forms.HiddenInput(),  # Oculta el campo usuario en el formulario
        }