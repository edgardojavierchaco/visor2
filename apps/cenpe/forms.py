from logging import PlaceHolder
from attr import field
from django import forms
from .models import CeicPuntos, Datos_Personal_Cenpe, Estado_Civil_Cenpe, Gestion_Institucion_Cenpe, Nivel_Formacion_Cenpe, Nivel_Sistema, PadronCenpe, SituacionRevista, Tipo_Formacion_Cenpe, Tipo_Institucion_Cenpe, documento_tipo, nacionalidad, provincia_tipo, localidad_tipo, pais, Academica_Cenpe, sexo_tipo
from .models import CargosHoras_Cenpe, TipoJornada_Cueanexo, Zona_Cueanexo, Categoria_Cueanexo, funciones
from .models import condicionactividad, PadronCenpe
import re

class DatosPersonalCenpeForm(forms.ModelForm):    
    
    apellidos=forms.CharField(
        widget=forms.TextInput(attrs={'class':'form-control textinput'})
    ) 
    
    nombres=forms.CharField(
        widget=forms.TextInput(attrs={'class':'form-control textinput'})
    )
    
    dni=forms.CharField(
        widget=forms.TextInput(attrs={'class':'form-control textinput'}),
        help_text='Ej. 12345678',
        label='DNI N°'
    )
    
    cuil=forms.CharField(
        widget=forms.TextInput(attrs={'class':'form-control textinput'}),
        help_text='Ej. 20123456782',
        label='CUIL N°'
    )
    
    telfijo=forms.CharField(
        widget=forms.TextInput(attrs={'class':'form-control textinput'}),
        help_text='Sin 0 del código de área. Ej: 3624123456',
        label='Teléfono Fijo'
    )    
    
    
    celular=forms.CharField(
        widget=forms.TextInput(attrs={'class':'form-control textinput'}),
        help_text='Sin 0 del código de área, ni 15. Ej: 3734123456'
    )
    
    f_nac=forms.DateField(
        widget=forms.DateInput(attrs={'class':'form-control date', 'type':'date'}),
        help_text='Ej. 01/01/2000',
        label='Fecha Nacimiento'
    )
    
    calle=forms.CharField(
        widget=forms.TextInput(attrs={'class':'form-control textinput'})
    )   
    
    nro=forms.CharField(
        widget=forms.TextInput(attrs={'class':'form-control textinput'})
    )   
    
    mz=forms.CharField(
        widget=forms.TextInput(attrs={'class':'form-control textinput'})
    ) 
    
    pc=forms.CharField(
        widget=forms.TextInput(attrs={'class':'form-control textinput'})
    )     
    
    casa=forms.CharField(
        widget=forms.TextInput(attrs={'class':'form-control textinput'})
    )  
    
    piso=forms.CharField(
        widget=forms.TextInput(attrs={'class':'form-control textinput'})
    )     
    
    uf=forms.CharField(
        widget=forms.TextInput(attrs={'class':'form-control textinput'})
    )   
    
    barrio=forms.CharField(
        widget=forms.TextInput(attrs={'class':'form-control textinput'}),
        help_text='Si no tiene nombre de Barrio, consignar SIN DATOS'
    )   
    
    pais_nac = forms.ModelChoiceField(
        queryset=pais.objects.all(),
        widget=forms.Select(attrs={'class': 'form-control select2'}),
        label='País Nacimiento'
    )
    
    nacionalidad = forms.ModelChoiceField(
        queryset=nacionalidad.objects.all(),
        widget=forms.Select(attrs={'class': 'form-control select2'})
    )
    
    t_doc = forms.ModelChoiceField(
        queryset=documento_tipo.objects.all(),
        widget=forms.Select(attrs={'class': 'form-control select2'}),
        label='Tipo Documento'
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
        label='Nivel Formación'
    )   
    
    
    prov_nac = forms.ModelChoiceField(
        queryset=provincia_tipo.objects.all(),
        widget=forms.Select(attrs={'class': 'form-control select2'}),
        label='Provincia Nacimiento'
    )
    
    prov_resid = forms.ModelChoiceField(
        queryset=provincia_tipo.objects.all(),
        widget=forms.Select(attrs={'class': 'form-control select2'}),
        label='Provincia Residencia'
    )

    loc_nac = forms.ModelChoiceField(
        queryset=localidad_tipo.objects.none(),  # Inicialmente vacío
        widget=forms.Select(attrs={'class': 'form-control select2'}),  # Select2 para loc_nac
        label='Localidad Nacimiento'
    )    
    
    
    loc_resid = forms.ModelChoiceField(
        queryset=localidad_tipo.objects.none(),  # Inicialmente vacío
        widget=forms.Select(attrs={'class': 'form-control select2'}),  # Select2 para loc_resid
        label='Localidad Resisdencia'
    )   
    

    class Meta:
        model = Datos_Personal_Cenpe
        fields = '__all__'
        widgets = {
            'usuario': forms.HiddenInput(),  # Oculta el campo usuario en el formulario
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
        widget=forms.TextInput (attrs={'class': 'form-control textinput'}),
        error_messages={
        'max_length': 'El título no puede tener más de 255 caracteres.',
        'min_length': 'El título debe tener al menos 1 caracter.'
    }
    )
    
    tipo_form = forms.ModelChoiceField(
        queryset=Tipo_Formacion_Cenpe.objects.all(),
        widget=forms.Select(attrs={'class': 'form-control select2'}),
        label='Tipo Formación'
    )

    nivel_form = forms.ModelChoiceField(
        queryset=Nivel_Formacion_Cenpe.objects.all(),
        widget=forms.Select(attrs={'class': 'form-control select2'}),
        label='Nivel Formación'
    )

    tipo_inst = forms.ModelChoiceField(
        queryset=Tipo_Institucion_Cenpe.objects.all(),
        widget=forms.Select(attrs={'class': 'form-control select2'}),
        label='Tipo Institución'
    )

    gestion_inst = forms.ModelChoiceField(
        queryset=Gestion_Institucion_Cenpe.objects.all(),
        widget=forms.Select(attrs={'class': 'form-control select2'}),
        label='Tipo Gestión'
    )
    
    reg_nro = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control textinput'}),
        help_text='Otorgado por la Dirección de Títulos y Equivalencias de la provincia del Chaco',
        label='Registro N°'
    )
    
    f_egreso = forms.DateField(
    widget=forms.DateInput(attrs={'class': 'form-control date', 'type': 'date'}),
    label='Fecha egreso'
    )


    class Meta:
        model = Academica_Cenpe  # Nombre correcto del modelo
        fields = '__all__'
        widgets = {
            'usuario': forms.HiddenInput(),  # Oculta el campo usuario en el formulario
        }
        
    def clean_titulo(self):
        # Asegura que el titulo esté en mayúsculas y solo contenga caracteres válidos
        titulo = self.cleaned_data['titulo'].upper()
        allowed_chars = re.compile(r"^[A-ZÁÉÍÓÚÑ' ]+$")
        if not allowed_chars.match(titulo):
            raise forms.ValidationError(('Solo se permiten letras mayúsculas, espacios, tildes y apóstrofes.'))
        return titulo


class CargosHorasCenpeForm(forms.ModelForm):
    cueanexo= forms.ModelChoiceField(
        queryset=PadronCenpe.objects.all(),
        widget=forms.Select(attrs={'class':'form-control select2'}),
        label='Cueanexo'
    )
    
    
    categoria=forms.ModelChoiceField(
        queryset=Categoria_Cueanexo.objects.all(),
        widget=forms.Select(attrs={'class':'form-control select2'}),
        label='Categoría Escuela'
    )
    
    jornada=forms.ModelChoiceField(
        queryset=TipoJornada_Cueanexo.objects.all(),
        widget=forms.Select(attrs={'class':'form-control select2'}),
        label='Tipo Jornada'
    )
    
    zona=forms.ModelChoiceField(
        queryset=Zona_Cueanexo.objects.all(),
        widget=forms.Select(attrs={'class':'form-control select2'}),
        label='Zona'
    )
    
    nivel_cargohora=forms.ModelChoiceField(
        queryset=Nivel_Sistema.objects.all(),
        widget=forms.Select(attrs={'class':'form-control select2'}),
        label='Nivel Cargo/ Hora Cátedra'
    )
    
    cargos_horas=forms.ModelChoiceField(
        queryset=CeicPuntos.objects.all(),
        widget=forms.Select(attrs={'class':'form-control select2'}),
        label='Cargos/ Hora Cátedra'        
    )
    
    cant_horas=forms.IntegerField(
        widget=forms.NumberInput(attrs={'class':'form-control integer', 'placeholder':'En caso de cargos, consignar valor 0'}),
        label='Cantidad Horas'
    )
    
    lunes=forms.BooleanField(
        widget=forms.CheckboxInput(attrs={'class':'form-control checkbox'}),
        label='Lunes',
        required=False
    )
    
    martes=forms.BooleanField(
        widget=forms.CheckboxInput(attrs={'class':'form-control checkbox'}),
        label='Martes',
        required=False
    )
    
    miercoles=forms.BooleanField(
        widget=forms.CheckboxInput(attrs={'class':'form-control checkbox'}),
        label='Miércoles',
        required=False
    )
    
    jueves=forms.BooleanField(
        widget=forms.CheckboxInput(attrs={'class':'form-control checkbox'}),
        label='Jueves',
        required=False
    )
    
    viernes=forms.BooleanField(
        widget=forms.CheckboxInput(attrs={'class':'form-control checkbox'}),
        label='Viernes',
        required=False
    )
    
    situacion_revista=forms.ModelChoiceField(
        queryset=SituacionRevista.objects.all(),
        widget=forms.Select(attrs={'class':'form-control select2'}),
        label='Situación Revista'
    )
    
    funciones=forms.ModelChoiceField(
        queryset=funciones.objects.all(),
        widget=forms.Select(attrs={'class':'form-control select2'}),
        label='Funciones'
    )
    
    condicion_actividad=forms.ModelChoiceField(
        queryset=condicionactividad.objects.all(),
        widget=forms.Select(attrs={'class':'form-control select2'}),
        label='Condición Actividad'
    )
    
    fecha_desde = forms.DateField(
    widget=forms.DateInput(attrs={'class': 'form-control date', 'type': 'date'}),
    label='Fecha desde'
    )
    
    fecha_hasta=forms.DateField(
        initial='2060-12-31',
        widget=forms.DateInput(attrs={'class': 'form-control date', 'type': 'date'}),
        label='Fecha hasta'
    )
    
    cuof=forms.IntegerField(
        widget=forms.NumberInput(attrs={'class':'form-control integer'}),
        label='CUOF'
    )
    
    cuof_anexo=forms.IntegerField(
        widget=forms.NumberInput(attrs={'class':'form-control integer'}),
        label='CUOF_Anexo'
    )
    
    class Meta:
        model = CargosHoras_Cenpe
        fields = '__all__'
        widgets = {
            'usuario': forms.HiddenInput(),  # Oculta el campo usuario en el formulario
        }         

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['cueanexo'].label_from_instance = self.label_from_instance_cueanexo
        
    # Método personalizado para mostrar en el select
    def label_from_instance_cueanexo(self, obj):
        return f"{obj.cueanexo} - {obj.nom_est}"
    

           
    