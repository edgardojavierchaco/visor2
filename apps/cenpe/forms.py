from logging import PlaceHolder
from attr import field
from django import forms
from .models import CeicPuntos, Datos_Personal_Cenpe, Estado_Civil_Cenpe, Gestion_Institucion_Cenpe, Nivel_Formacion_Cenpe, Nivel_Sistema, PadronCenpe, SituacionRevista, Tipo_Formacion_Cenpe, Tipo_Institucion_Cenpe, documento_tipo, nacionalidad, provincia_tipo, localidad_tipo, pais, Academica_Cenpe, sexo_tipo
from .models import CargosHoras_Cenpe, TipoJornada_Cueanexo, Zona_Cueanexo, Categoria_Cueanexo, funciones
from .models import condicionactividad, PadronCenpe
import re

class DatosPersonalCenpeForm(forms.ModelForm):   
    """
    Formulario para capturar los datos personales del usuario del sistema CENPE.

    Campos:
        apellidos (CharField): Campo de texto para el apellido.
        nombres (CharField): Campo de texto para el nombre en mayúsculas.
        dni (CharField): Campo de texto para ingresar el DNI.
        cuil (CharField): Campo de texto para ingresar el CUIL.
        telfijo (CharField): Campo de texto para ingresar el teléfono fijo.
        celular (CharField): Campo de texto para ingresar el número de celular.
        f_nac (DateField): Campo para ingresar la fecha de nacimiento.
        calle (CharField): Campo de texto para la calle de la dirección.
        nro (CharField): Campo de texto para el número de la dirección.
        mz (CharField): Campo de texto para el bloque o manzana.
        pc (CharField): Campo de texto para el código postal.
        casa (CharField): Campo de texto para el número de casa.
        piso (CharField): Campo de texto para el piso de la dirección.
        uf (CharField): Campo de texto para la unidad funcional.
        barrio (CharField): Campo de texto para el barrio.
        pais_nac (ModelChoiceField): Campo de selección para el país de nacimiento.
        nacionalidad (ModelChoiceField): Campo de selección para la nacionalidad.
        t_doc (ModelChoiceField): Campo de selección para el tipo de documento.
        sexo (ModelChoiceField): Campo de selección para el sexo.
        estado_civil (ModelChoiceField): Campo de selección para el estado civil.
        nivel_form (ModelChoiceField): Campo de selección para el nivel de formación alcanzado.
        prov_nac (ModelChoiceField): Campo de selección para la provincia de nacimiento.
        prov_resid (ModelChoiceField): Campo de selección para la provincia de residencia.
        loc_nac (ModelChoiceField): Campo de selección para la localidad de nacimiento.
        loc_resid (ModelChoiceField): Campo de selección para la localidad de residencia.

    Métodos:
        clean_apellidos(): Limpia y valida el campo de apellidos.
        clean_nombres(): Limpia y valida el campo de nombres.
        __init__(): Inicializa el formulario y carga dinámicamente las localidades según la provincia seleccionada.
    """ 
    
    apellidos=forms.CharField(
        widget=forms.TextInput(attrs={'class':'form-control textinput'})
    ) 
    
    nombres=forms.CharField(
        widget=forms.TextInput(attrs={'class':'form-control textinput', 'placeholder':'Sin abreviaturas, todo en mayúsculas'})
    )
    
    dni=forms.CharField(
        widget=forms.TextInput(attrs={'class':'form-control textinput','placeholder':'Sin puntos. Ej: 22345678'}),
        
        label='DNI N°'
    )
    
    cuil=forms.CharField(
        widget=forms.TextInput(attrs={'class':'form-control textinput','placeholder':'Sin puntos ni guiones medios. Ej: 27223456782'}),
        
        label='CUIL N°'
    )
    
    telfijo=forms.CharField(
        widget=forms.TextInput(attrs={'class':'form-control textinput', 'placeholder':'Sin el 0 del código de área. Ej: 3624123456'}),
        
        label='Teléfono Fijo'
    )    
    
    
    celular=forms.CharField(
        widget=forms.TextInput(attrs={'class':'form-control textinput', 'placeholder':'Sin el 0 del código de área ni el 15. Ej: 3734123456'}),
        
    )
    
    f_nac=forms.DateField(
        widget=forms.DateInput(attrs={'class':'form-control date', 'type':'date'}),
        
        label='Fecha Nacimiento'
    )
    
    calle=forms.CharField(
        widget=forms.TextInput(attrs={'class':'form-control textinput', 'placeholder':'Sin abreviaturas, todo en mayúsculas'})
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
        widget=forms.TextInput(attrs={'class':'form-control textinput', 'placeholder':'Si desconoce/ no tiene, consignar "SIN DATOS"'}),
        
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
        queryset=localidad_tipo.objects.none(),  
        widget=forms.Select(attrs={'class': 'form-control select2'}), 
        label='Localidad Nacimiento'
    )    
    
    
    loc_resid = forms.ModelChoiceField(
        queryset=localidad_tipo.objects.none(),  
        widget=forms.Select(attrs={'class': 'form-control select2'}), 
        label='Localidad Resisdencia'
    )   
    

    class Meta:
        model = Datos_Personal_Cenpe
        fields = '__all__'
        widgets = {
            'usuario': forms.HiddenInput(),  
        }
        

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['apellidos'].widget.attrs['autofocus']=True
        
        # Si hay una provincia de nacimiento seleccionada, carga las localidades correspondientes
        if 'prov_nac' in self.data:
            try:
                provincia_id = int(self.data.get('prov_nac'))
                print('provincia_id', provincia_id)  
                self.fields['loc_nac'].queryset = localidad_tipo.objects.filter(c_provincia_id=provincia_id).order_by('descripcion_loc')
            except (ValueError, TypeError):
                pass  
        elif self.instance.pk:
            
            # Si hay una instancia existente, muestra las localidades correspondientes a la provincia guardada
            self.fields['loc_nac'].queryset = localidad_tipo.objects.filter(c_provincia=self.instance.prov_nac).order_by('descripcion_loc')
        
        # Si hay una provincia de residencia seleccionada, carga las localidades correspondientes
        if 'prov_resid' in self.data:
            try:
                provincia2_id = int(self.data.get('prov_resid'))
                print('provincia2_id', provincia2_id)  
                self.fields['loc_resid'].queryset = localidad_tipo.objects.filter(c_provincia_id=provincia2_id).order_by('descripcion_loc')
            except (ValueError, TypeError):
                pass  
        elif self.instance.pk:
            # Si hay una instancia existente, muestra las localidades correspondientes a la provincia guardada
            self.fields['loc_resid'].queryset = localidad_tipo.objects.filter(c_provincia=self.instance.prov_resid).order_by('descripcion_loc')

    def clean_apellidos(self):
        """
        Asegura que el campo de apellidos esté en mayúsculas y solo contenga caracteres válidos.
        
        Returns:
            str: Apellido validado y convertido a mayúsculas.
        """
        
        # Asegura que apellidos esté en mayúsculas y solo contenga caracteres válidos
        apellidos = self.cleaned_data['apellidos'].upper()
        allowed_chars = re.compile(r"^[A-ZÁÉÍÓÚÑ' ]+$")
        if not allowed_chars.match(apellidos):
            raise forms.ValidationError(_('Solo se permiten letras mayúsculas, espacios, tildes y apóstrofes.'))
        return apellidos

    def clean_nombres(self):
        """
        Asegura que el campo de nombres esté en mayúsculas y solo contenga caracteres válidos.
        
        Returns:
            str: Nombre validado y convertido a mayúsculas.
        """
        
        # Asegura que nombres esté en mayúsculas y solo contenga caracteres válidos
        nombres = self.cleaned_data['nombres'].upper()
        allowed_chars = re.compile(r"^[A-ZÁÉÍÓÚÑ' ]+$")
        if not allowed_chars.match(nombres):
            raise forms.ValidationError(_('Solo se permiten letras mayúsculas, espacios, tildes y apóstrofes.'))
        return nombres


class DatosAcademicosCenpeForm(forms.ModelForm):
    """
    Formulario para capturar los datos académicos del usuario en el sistema CENPE.

    Campos:
        titulo (CharField): Campo de texto para el título académico.
        tipo_form (ModelChoiceField): Campo de selección para el tipo de formación.
        nivel_form (ModelChoiceField): Campo de selección para el nivel de formación alcanzado.
        tipo_inst (ModelChoiceField): Campo de selección para el tipo de institución.
        gestion_inst (ModelChoiceField): Campo de selección para la gestión de la institución.
        reg_nro (CharField): Campo de texto para el número de registro del título.
        f_egreso (DateField): Campo de fecha para la fecha de egreso.

    Métodos:
        clean_titulo(): Limpia y valida el campo de título.
        __init__(): Inicializa el formulario y establece el foco en el campo título.
    """
    
    titulo = forms.CharField (
        max_length=255,
        min_length=1,        
        widget=forms.TextInput (attrs={'class': 'form-control textinput','placeholder':'Sin abreviaturas, todo mayúsculas'}),
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
        widget=forms.TextInput(attrs={'class': 'form-control textinput','placeholder':'Otorgado por la Dirección de Títulos y Equivalencias de la provincia del Chaco'}),
        help_text='Otorgado por la Dirección de Títulos y Equivalencias de la provincia del Chaco',
        label='Registro N°'
    )
    
    f_egreso = forms.DateField(
    widget=forms.DateInput(attrs={'class': 'form-control date', 'type': 'date'}),
    label='Fecha egreso'
    )


    class Meta:
        model = Academica_Cenpe 
        fields = '__all__'
        widgets = {
            'usuario': forms.HiddenInput(),  
        }
        
    def clean_titulo(self):
        """
        Asegura que el campo de título esté en mayúsculas y solo contenga caracteres válidos.
        
        Returns:
            str: Título validado y convertido a mayúsculas.
        """
        
        # Asegura que el titulo esté en mayúsculas y solo contenga caracteres válidos
        titulo = self.cleaned_data['titulo'].upper()
        allowed_chars = re.compile(r"^[A-ZÁÉÍÓÚÑ' ]+$")
        if not allowed_chars.match(titulo):
            raise forms.ValidationError(('Solo se permiten letras mayúsculas, espacios, tildes y apóstrofes.'))
        return titulo

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['titulo'].widget.attrs['autofocus']=True
        

class CargosHorasCenpeForm(forms.ModelForm):
    """
    Formulario para capturar los datos de cargos y horas en el sistema CENPE.

    Campos:
        cueanexo (ModelChoiceField): Campo de selección para el Cueanexo.
        categoria (ModelChoiceField): Campo de selección para la categoría de la escuela.
        jornada (ModelChoiceField): Campo de selección para el tipo de jornada.
        zona (ModelChoiceField): Campo de selección para la zona.
        nivel_cargohora (ModelChoiceField): Campo de selección para el nivel del cargo o la hora cátedra.
        cargos_horas (ModelChoiceField): Campo de selección para los cargos u horas cátedra.
        cant_horas (DecimalField): Campo numérico para ingresar la cantidad de horas.
        lunes, martes, miercoles, jueves, viernes (BooleanField): Checkboxes para indicar los días de trabajo.
        situacion_revista (ModelChoiceField): Campo de selección para la situación de revista.
        funciones (ModelChoiceField): Campo de selección para las funciones.
        condicion_actividad (ModelChoiceField): Campo de selección para la condición de actividad.
        fecha_desde, fecha_hasta (DateField): Campos de fecha para indicar el período.
        cuof, cuof_anexo (IntegerField): Campos numéricos para ingresar el CUOF y CUOF anexo.

    Métodos:
        __init__(): Inicializa el formulario, estableciendo el foco y personalizando las etiquetas.
        label_from_instance_cueanexo(): Método personalizado para mostrar el Cueanexo y el nombre de la institución.
    """
    
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
    
    cant_horas=forms.DecimalField(
        widget=forms.NumberInput(attrs={'class':'form-control decimal', 'placeholder':'Cargos = Hs. reloj (ej. 36.30), Otros = Hs. Cát. (ej. 12.00)'}),
        label='Cantidad Horas',
        max_digits=4,
        decimal_places=2    
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
        widget=forms.NumberInput(attrs={'class':'form-control integer','placeholder':'Lo puede encontrar en su Recibo de Haberes.'}),
        label='CUOF'
    )
    
    cuof_anexo=forms.IntegerField(
        widget=forms.NumberInput(attrs={'class':'form-control integer','placeholder':'Lo puede encontrar en su Recibo de Haberes.'}),
        label='CUOF_Anexo'
    )
    
    class Meta:
        model = CargosHoras_Cenpe
        fields = '__all__'
        widgets = {
            'usuario': forms.HiddenInput(),  
        }         

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['cueanexo'].widget.attrs['autofocus']=True
        self.fields['cueanexo'].label_from_instance = self.label_from_instance_cueanexo
        
    # Método personalizado del select
    def label_from_instance_cueanexo(self, obj):
        """
        Devuelve la etiqueta personalizada para el campo `cueanexo` mostrando el Cueanexo y el nombre de la institución.
        
        Args:
            obj: Instancia de PadronCenpe.

        Returns:
            str: Texto formateado que muestra el Cueanexo y el nombre de la institución.
        """
        return f"{obj.cueanexo} - {obj.nom_est}"
    

           
    