import re
from django import forms
from django.forms import ModelForm
from .models import RegDocporSeccion, RegEvaluacionFluidezLectora
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator

class RegDocporSeccionForm(forms.ModelForm):
    """
    Formulario para registrar documentos por sección.

    Fields:
        - id: Identificador del registro.
        - dni_docen: DNI del docente.
        - apellido_docen: Apellido del docente.
        - nombres_docen: Nombres del docente.
        - cueanexo: Código único de anexos (debe comenzar con '22').
        - curso: Curso al que pertenece el documento.
        - division: División del curso.
        - turno: Turno del curso.
        - operativos: Información adicional sobre operativos.
        - validacion: Estado de validación del registro.
    """
    
    class Meta:
        model = RegDocporSeccion
        fields = ['id','dni_docen','apellido_docen','nombres_docen','cueanexo', 'curso', 'division', 'turno', 'operativos','validacion']


    def clean_cueanexo(self):
        """
        Valida que el campo 'cueanexo' sea un número de 9 dígitos que comience con '22'.
        
        Raises:
            ValidationError: Si el 'cueanexo' no cumple con el formato requerido.
        """
        
        cueanexo = self.cleaned_data.get('cueanexo')
        if not re.match(r'^22\d{7}$', cueanexo):
            raise forms.ValidationError("Cueanexo debe ser un número de 9 dígitos que comience con '22'.")
        return cueanexo
    

class RegDocporSeccionEdicionForm(forms.ModelForm):
    """
    Formulario para editar documentos por sección.

    Fields son los mismos que RegDocporSeccionForm, excluyendo 'id'.
    """
    
    class Meta:
        model = RegDocporSeccion
        fields = ['dni_docen','apellido_docen','nombres_docen','cueanexo', 'curso', 'division', 'turno', 'operativos', 'validacion']


    def clean_cueanexo(self):
        """
        Valida que el campo 'cueanexo' sea un número de 9 dígitos que comience con '22'.

        Raises:
            ValidationError: Si el 'cueanexo' no cumple con el formato requerido.
        """
        
        cueanexo = self.cleaned_data.get('cueanexo')
        if not re.match(r'^22\d{7}$', cueanexo):
            raise forms.ValidationError("Cueanexo debe ser un número de 9 dígitos que comience con '22'.")
        return cueanexo
    
#formulario para cargar evaluacion el aplicador
class RegEvaluacionFluidezLectoraForm(ModelForm):
    """
    Formulario para cargar evaluaciones de fluidez lectora.

    Fields:
        - cueanexo: Código único de anexos (oculto).
        - region: Región del estudiante (oculta).
        - grado: Grado del estudiante (oculto).
        - seccion: Sección del estudiante (oculta).
        - apellido_alumno: Apellido del alumno (oculto).
        - nombres_alumno: Nombres del alumno (oculto).
        - dni_alumno: DNI del alumno (oculto).
        - cal_vel: Calificación de velocidad (oculta).
        - cal_pres: Calificación de precisión (oculta).
        - cal_pros: Calificación de prosodia (oculta).
        - cal_comp: Calificación de comprensión (oculta).
        - asistencia: Indicador de asistencia (checkbox).
    """
    
    class Meta:
        model = RegEvaluacionFluidezLectora
        fields = '__all__'
        widgets = {
            'cueanexo': forms.HiddenInput(),
            'region': forms.HiddenInput(),
            'grado': forms.HiddenInput(),
            'seccion':forms.HiddenInput(),
            'apellido_alumno':forms.HiddenInput(),
            'nombres_alumno':forms.HiddenInput(),
            'dni_alumno':forms.HiddenInput(),            
            'cal_vel': forms.HiddenInput(),
            'cal_pres': forms.HiddenInput(),
            'cal_pros': forms.HiddenInput(),
            'cal_comp': forms.HiddenInput(),
            'asistencia': forms.CheckboxInput(),            
        }

    def __init__(self, *args, **kwargs):
        """
        Inicializa el formulario, configurando campos opcionales.

        Args:
            *args: Argumentos posicionales.
            **kwargs: Argumentos de palabra clave, incluyendo 'user' para obtener datos específicos.
        """
        
        super().__init__(*args, **kwargs)
        self.fields['asistencia'].required=False
        self.fields['cueanexo'].required = False
        self.fields['region'].required = False
        self.fields['cal_vel'].required = False
        self.fields['cal_pres'].required = False
        self.fields['cal_pros'].required = False
        self.fields['cal_comp'].required = False

    # Deshabilitar todos los campos excepto los especificados
        """ for field in self.fields:
            if field not in ['asistencia', 'tramo', 'velocidad', 'precision', 'prosodia', 'comprension']:
                self.fields[field].widget.attrs['disabled'] = 'disabled' """
    
    def clean(self):
        """
        Valida los campos del formulario al enviar.

        Se asegura de que las calificaciones sean mayores a 0 si la asistencia está marcada.

        Raises:
            ValidationError: Si las calificaciones no cumplen con las condiciones.
        """
        
        cleaned_data = super().clean()
        asistencia = cleaned_data.get("asistencia")
        velocidad = cleaned_data.get("velocidad")
        precision = cleaned_data.get("precision")
        prosodia = cleaned_data.get("prosodia")
        comprension = cleaned_data.get("comprension")

        if asistencia:
            if not (velocidad and velocidad > 0):
                self.add_error('velocidad', 'La velocidad debe ser mayor a 0 cuando asistencia está marcada.')
            if not (precision and precision > 0):
                self.add_error('precision', 'La precisión debe ser mayor a 0 cuando asistencia está marcada.')
            if not (prosodia and prosodia > 0):
                self.add_error('prosodia', 'La prosodia debe ser mayor a 0 cuando asistencia está marcada.')
            if not (comprension and comprension >= 0):
                self.add_error('comprension', 'La comprensión debe ser mayor a 0 cuando asistencia está marcada.')

                 
class FiltroEvaluacionForm(forms.Form):
    """
    Formulario de filtro para evaluaciones de fluidez lectora.

    Fields:
        - cueanexo: Selección del cueanexo.
        - grado: Selección del grado.
        - seccion: Selección de la sección.
    """
    
    cueanexo = forms.ChoiceField(required=False, label='Cueanexo')
    grado = forms.ChoiceField(required=False, label='Grado')
    seccion = forms.ChoiceField(required=False, label='Sección')

    def __init__(self, *args, **kwargs):
        """
        Inicializa el formulario, filtrando opciones según el usuario.

        Args:
            *args: Argumentos posicionales.
            **kwargs: Argumentos de palabra clave, incluyendo 'user' para obtener datos específicos.
        """
        
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        if user:
            cueanexos = RegDocporSeccion.objects.filter(dni_docen=user.username).values_list('cueanexo', flat=True).distinct()
            grados = RegDocporSeccion.objects.filter(dni_docen=user.username).values_list('curso__nom_curso', flat=True).distinct()
            secciones = RegDocporSeccion.objects.filter(dni_docen=user.username).values_list('division__nom_division', flat=True).distinct()
            self.fields['cueanexo'].choices = [(cueanexo, cueanexo) for cueanexo in cueanexos]
            self.fields['grado'].choices = [(grado, grado) for grado in grados]
            self.fields['seccion'].choices = [(seccion, seccion) for seccion in secciones]

# formulario cargar alumno para el aplicador
class RegAlumnosFluidezLectoraForm(ModelForm):
    """
    Formulario para cargar alumnos en evaluaciones de fluidez lectora.

    Fields:
        - region: Selección de la región (opcional).
        - grado: Selección del grado (opcional).
        - seccion: Selección de la sección (opcional).
        - cal_vel: Calificación de velocidad (oculta).
        - cal_pres: Calificación de precisión (oculta).
        - cal_pros: Calificación de prosodia (oculta).
        - cal_comp: Calificación de comprensión (oculta).
        - asistencia: Indicador de asistencia (checkbox).
    """
    
    REGIONES_CHOICES = [
        ('R.E. 1', 'R.E. 1'),
        ('R.E. 2', 'R.E. 2'),
        ('R.E. 3', 'R.E. 3'),
        ('R.E. 4-A', 'R.E. 4-A'),
        ('R.E. 4-B', 'R.E. 4-B'),
        ('R.E. 5', 'R.E. 5'),
        ('R.E. 6', 'R.E. 6'),
        ('R.E. 7', 'R.E. 7'),
        ('R.E. 8-A', 'R.E. 8-A'),
        ('R.E. 8-B', 'R.E. 8-B'),
        ('R.E. 9', 'R.E. 9'),
        ('R.E. 10-A', 'R.E. 10-A'),
        ('R.E. 10-B', 'R.E. 10-B'),
        ('R.E. 10-C', 'R.E. 10-C'),
        ('SUB. R.E. 1-A', 'SUB. R.E. 1-A'),
        ('SUB. R.E. 1-B', 'SUB. R.E. 1-B'),
        ('SUB. R.E. 2', 'SUB. R.E. 2'),
        ('SUB. R.E. 3', 'SUB. R.E. 3'),
        ('SUB. R.E. 5', 'SUB. R.E. 5'),
    ]
    
    CURSO_CHOICES = [('PRIMERO', 'PRIMERO'), ('SEGUNDO', 'SECUNDO'), ('TERCERO', 'TERCERO'), 
                     ('CUARTO', 'CUARTO'), ('QUINTO', 'QUINTO'), ('SEXTO', 'SEXTO'), ('SEPTIMO', 'SEPTIMO')]

    SECCION_CHOICES = [(chr(i), chr(i)) for i in range(ord('A'), ord('Z')+1)]
    SECCION_CHOICES.append(('MULTIPLE','MULTIPLE'))
    
    region=forms.ChoiceField(choices=REGIONES_CHOICES, required=False)
    grado = forms.ChoiceField(choices=CURSO_CHOICES, required=False)
    seccion = forms.ChoiceField(choices=SECCION_CHOICES, required=False)
    
    class Meta:
        model = RegEvaluacionFluidezLectora
        fields = '__all__'
        widgets = {                     
                 
            'cal_vel': forms.HiddenInput(),
            'cal_pres': forms.HiddenInput(),
            'cal_pros': forms.HiddenInput(),
            'cal_comp': forms.HiddenInput(),
            'asistencia': forms.CheckboxInput(),
        }

    def __init__(self, *args, **kwargs):
        """
        Valida los campos del formulario al enviar.

        Se asegura de que las calificaciones sean mayores a 0 si la asistencia está marcada.

        Raises:
            ValidationError: Si las calificaciones no cumplen con las condiciones.
        """
        
        super().__init__(*args, **kwargs)
        self.fields['asistencia'].required=False
        self.fields['cueanexo'].required = False
        self.fields['region'].required = False
        self.fields['cal_vel'].required = False
        self.fields['cal_pres'].required = False
        self.fields['cal_pros'].required = False
        self.fields['cal_comp'].required = False
    
    
    def clean_cueanexo(self):
            cueanexo = self.cleaned_data.get('cueanexo')
            if cueanexo:
                if not re.match(r'^22\d{7}$', cueanexo):
                    raise forms.ValidationError("El campo Cueanexo debe comenzar con '22' y contener 9 dígitos en total.")
            return cueanexo
    
    def clean_apellido_alumno(self):
        apellido_alumno = self.cleaned_data.get('apellido_alumno')
        if apellido_alumno:
            # Ajusta la expresión regular para permitir espacios en blanco
            if not re.match(r"^[A-ZÁÉÍÓÚÑ'´ ]+$", apellido_alumno):
                raise forms.ValidationError("El campo Apellido debe estar en mayúsculas y sólo puede contener letras con tildes, apóstrofes y espacios.")
            apellido_alumno = apellido_alumno.upper()
        return apellido_alumno

    def clean_nombres_alumno(self):
        nombres_alumno = self.cleaned_data.get('nombres_alumno')
        if nombres_alumno:
            # La expresión regular ya permite espacios en blanco
            if not re.match(r"^[A-ZÁÉÍÓÚÑ'´ ]+$", nombres_alumno):
                raise forms.ValidationError("El campo Nombres debe estar en mayúsculas y sólo puede contener letras con tildes, apóstrofes y espacios.")
            nombres_alumno = nombres_alumno.upper()
        return nombres_alumno
    
    def clean_dni_alumno(self):
        dni_alumno = self.cleaned_data.get('dni_alumno')
        if dni_alumno:
            if not re.match(r'^\d{7,}$', dni_alumno):
                raise forms.ValidationError("El campo DNI debe contener sólo números y tener al menos 7 dígitos.")
        return dni_alumno

# formulario para el director
class RegEvaluacionFluidezLectoraDirectoresForm(ModelForm):
    CURSO_CHOICES = [('PRIMERO', 'PRIMERO'), ('SEGUNDO', 'SECUNDO'), ('TERCERO', 'TERCERO'), 
                     ('CUARTO', 'CUARTO'), ('QUINTO', 'QUINTO'), ('SEXTO', 'SEXTO'), ('SEPTIMO', 'SEPTIMO')]

    SECCION_CHOICES = [(chr(i), chr(i)) for i in range(ord('A'), ord('Z')+1)]
    SECCION_CHOICES.append(('MULTIPLE','MULTIPLE'))
    
    grado = forms.ChoiceField(choices=CURSO_CHOICES, required=True)
    seccion = forms.ChoiceField(choices=SECCION_CHOICES, required=True)
    
    apellido_alumno = forms.CharField(
        max_length=100,
        validators=[
            RegexValidator(
                regex=r'^[A-ZÁÉÍÓÚÑ\s\']+$',
                message="El apellido solo puede contener letras mayúsculas, espacios, tildes y apóstrofes."
            )
        ]
    )
    
    nombres_alumno = forms.CharField(
        max_length=100,
        validators=[
            RegexValidator(
                regex=r'^[A-ZÁÉÍÓÚÑ\s\']+$',
                message="El nombre solo puede contener letras mayúsculas, espacios, tildes y apóstrofes."
            )
        ]
    )
    
    dni_alumno = forms.CharField(
        max_length=8,
        validators=[
            RegexValidator(
                regex=r'^\d{7,8}$',
                message="El DNI debe contener solo números y tener entre 7 y 8 dígitos."
            )
        ]
    )

    class Meta:
        model = RegEvaluacionFluidezLectora
        fields = '__all__'
        widgets = {
            'cueanexo': forms.HiddenInput(),
            'region': forms.HiddenInput(), 
            'velocidad':forms.HiddenInput(),
            'precision':forms.HiddenInput(),  
            'prosodia':forms.HiddenInput(),  
            'comprension':forms.HiddenInput(),                    
            'cal_vel': forms.HiddenInput(),
            'cal_pres': forms.HiddenInput(),
            'cal_pros': forms.HiddenInput(),
            'cal_comp': forms.HiddenInput(),
            'asistencia': forms.HiddenInput(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['asistencia'].required = False
        self.fields['cueanexo'].required = False
        self.fields['region'].required = False
        self.fields['cal_vel'].required = False
        self.fields['cal_pres'].required = False
        self.fields['cal_pros'].required = False
        self.fields['cal_comp'].required = False

    def clean_apellido_alumno(self):
        data = self.cleaned_data['apellido_alumno']
        return data.upper()

    def clean_nombres_alumno(self):
        data = self.cleaned_data['nombres_alumno']
        return data.upper()


# formulario cargar alumno para el director
class RegAlumnosFluidezLectoraDirectorForm(ModelForm):
    REGIONES_CHOICES = [
        ('R.E. 1', 'R.E. 1'),
        ('R.E. 2', 'R.E. 2'),
        ('R.E. 3', 'R.E. 3'),
        ('R.E. 4-A', 'R.E. 4-A'),
        ('R.E. 4-B', 'R.E. 4-B'),
        ('R.E. 5', 'R.E. 5'),
        ('R.E. 6', 'R.E. 6'),
        ('R.E. 7', 'R.E. 7'),
        ('R.E. 8-A', 'R.E. 8-A'),
        ('R.E. 8-B', 'R.E. 8-B'),
        ('R.E. 9', 'R.E. 9'),
        ('R.E. 10-A', 'R.E. 10-A'),
        ('R.E. 10-B', 'R.E. 10-B'),
        ('R.E. 10-C', 'R.E. 10-C'),
        ('SUB. R.E. 1-A', 'SUB. R.E. 1-A'),
        ('SUB. R.E. 1-B', 'SUB. R.E. 1-B'),
        ('SUB. R.E. 2', 'SUB. R.E. 2'),
        ('SUB. R.E. 3', 'SUB. R.E. 3'),
        ('SUB. R.E. 5', 'SUB. R.E. 5'),
    ]
    
    CURSO_CHOICES = [('PRIMERO', 'PRIMERO'), ('SEGUNDO', 'SECUNDO'), ('TERCERO', 'TERCERO'), 
                     ('CUARTO', 'CUARTO'), ('QUINTO', 'QUINTO'), ('SEXTO', 'SEXTO'), ('SEPTIMO', 'SEPTIMO')]

    SECCION_CHOICES = [(chr(i), chr(i)) for i in range(ord('A'), ord('Z')+1)]
    SECCION_CHOICES.append(('MULTIPLE','MULTIPLE'))
    
    region=forms.ChoiceField(choices=REGIONES_CHOICES, required=False)
    grado = forms.ChoiceField(choices=CURSO_CHOICES, required=False)
    seccion = forms.ChoiceField(choices=SECCION_CHOICES, required=False)
    
    class Meta:
        model = RegEvaluacionFluidezLectora
        fields = '__all__'
        widgets = {                     
            'velocidad':forms.HiddenInput(),
            'precision':forms.HiddenInput(),     
            'prosodia':forms.HiddenInput(),
            'comprension':forms.HiddenInput(),
            'cal_vel': forms.HiddenInput(),
            'cal_pres': forms.HiddenInput(),
            'cal_pros': forms.HiddenInput(),
            'cal_comp': forms.HiddenInput(),
            'asistencia': forms.HiddenInput(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['asistencia'].required=False
        self.fields['cueanexo'].required = False
        self.fields['region'].required = False
        self.fields['cal_vel'].required = False
        self.fields['cal_pres'].required = False
        self.fields['cal_pros'].required = False
        self.fields['cal_comp'].required = False
        
        # Asignar valores predeterminados
        self.fields['velocidad'].initial = 0
        self.fields['precision'].initial = 0
        self.fields['prosodia'].initial = 1
        self.fields['comprension'].initial = 1
        self.fields['cal_vel'].initial = "Debajo del Básico"
        self.fields['cal_pres'].initial = "Debajo del Básico"
        self.fields['cal_pros'].initial = "Debajo del Básico"
        self.fields['cal_comp'].initial = "Debajo del Básico"
    
    
    def clean_cueanexo(self):
            cueanexo = self.cleaned_data.get('cueanexo')
            if cueanexo:
                if not re.match(r'^22\d{7}$', cueanexo):
                    raise forms.ValidationError("El campo Cueanexo debe comenzar con '22' y contener 9 dígitos en total.")
            return cueanexo
    
    def clean_apellido_alumno(self):
        apellido_alumno = self.cleaned_data.get('apellido_alumno')
        if apellido_alumno:
            # Ajusta la expresión regular para permitir espacios en blanco
            if not re.match(r"^[A-ZÁÉÍÓÚÑ'´ ]+$", apellido_alumno):
                raise forms.ValidationError("El campo Apellido debe estar en mayúsculas y sólo puede contener letras con tildes, apóstrofes y espacios.")
            apellido_alumno = apellido_alumno.upper()
        return apellido_alumno

    def clean_nombres_alumno(self):
        nombres_alumno = self.cleaned_data.get('nombres_alumno')
        if nombres_alumno:
            # La expresión regular ya permite espacios en blanco
            if not re.match(r"^[A-ZÁÉÍÓÚÑ'´ ]+$", nombres_alumno):
                raise forms.ValidationError("El campo Nombres debe estar en mayúsculas y sólo puede contener letras con tildes, apóstrofes y espacios.")
            nombres_alumno = nombres_alumno.upper()
        return nombres_alumno
    
    def clean_dni_alumno(self):
        dni_alumno = self.cleaned_data.get('dni_alumno')
        if dni_alumno:
            if not re.match(r'^\d{7,}$', dni_alumno):
                raise forms.ValidationError("El campo DNI debe contener sólo números y tener al menos 7 dígitos.")
        return dni_alumno
