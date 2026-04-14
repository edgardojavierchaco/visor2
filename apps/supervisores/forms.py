from django import forms
from .models import DirectoresRegionales, Supervisor, EscuelaSupervisor
import re

class SupervisorForm(forms.ModelForm):
    """
    Formulario para crear o editar un objeto Supervisor.

    Attributes:
        region (ChoiceField): Campo para seleccionar la región del supervisor.

    Meta:
        model (Supervisor): El modelo asociado a este formulario.
        fields (list): Todos los campos del modelo Supervisor.
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
    
    region = forms.ChoiceField(choices=REGIONES_CHOICES, required=True)
    
    class Meta:
        model = Supervisor
        fields = '__all__'
        
    
    def clean_apellido(self):
        """
        Valida el campo 'apellido'.

        Asegura que el apellido contenga solo letras en mayúsculas, con
        tildes, apóstrofes y espacios.

        Returns:
            str: El apellido validado en mayúsculas.

        Raises:
            ValidationError: Si el apellido no cumple con los criterios.
        """
        
        apellido = self.cleaned_data.get('apellido')
        if apellido:
            # Ajusta la expresión regular para permitir espacios en blanco
            if not re.match(r"^[A-ZÁÉÍÓÚÑ'´ ]+$", apellido):
                raise forms.ValidationError("El campo Apellido debe estar en mayúsculas y sólo puede contener letras con tildes, apóstrofes y/o espacios.")
            apellido = apellido.upper()
        return apellido

    def clean_nombres(self):
        """
        Valida el campo 'nombres'.

        Asegura que los nombres contengan solo letras en mayúsculas, con
        tildes, apóstrofes y espacios.

        Returns:
            str: Los nombres validados en mayúsculas.

        Raises:
            ValidationError: Si los nombres no cumplen con los criterios.
        """
        
        nombres = self.cleaned_data.get('nombres')
        if nombres:
            # La expresión regular ya permite espacios en blanco
            if not re.match(r"^[A-ZÁÉÍÓÚÑ'´ ]+$", nombres):
                raise forms.ValidationError("El campo Nombres debe estar en mayúsculas y sólo puede contener letras con tildes, apóstrofes y/o espacios.")
            nombres = nombres.upper()
        return nombres
        
    def clean_dni(self):
        """
        Valida el campo 'dni'.

        Asegura que el DNI contenga solo números y tenga al menos 7 dígitos.

        Returns:
            str: El DNI validado.

        Raises:
            ValidationError: Si el DNI no cumple con los criterios.
        """
        
        dni = self.cleaned_data.get('dni')
        if dni:
            if not re.match(r'^\d{7,}$', dni):
                raise forms.ValidationError("El campo DNI debe contener sólo números y tener al menos 7 dígitos.")
        return dni

class EscuelaForm(forms.ModelForm):
    """
    Formulario para crear o editar un objeto EscuelaSupervisor.

    Attributes:
        region_esc (ChoiceField): Campo para seleccionar la región de la escuela.
        oferta (ChoiceField): Campo para seleccionar la oferta educativa.
        modalidad (ChoiceField): Campo para seleccionar la modalidad educativa.

    Meta:
        model (EscuelaSupervisor): El modelo asociado a este formulario.
        fields (list): Todos los campos del modelo EscuelaSupervisor.
    """
    
    OFERTAS_CHOICES=[
        ('INICIAL', 'INICIAL'),
        ('PRIMARIO', 'PRIMARIO'),
        ('SECUNDARIO', 'SECUNDARIO'),
        ('SUPERIOR', 'SUPERIOR'),
        ('SERVICIOS EDUCATIVOS', 'SERVICIOS EDUCATIVOS'),
    ]
    
    MODALIDADES_CHOICES =[
        ('COMÚN', 'COMÚN'),
        ('TÉCNICO PROFESIONAL', 'TÉCNICO PROFESIONAL'),
        ('ESPECIAL', 'ESPECIAL'),
        ('JÓVENES Y ADULTOS', 'JÓVENES Y ADULTOS'),
        ('ARTÍSTICA', 'ARTÍSTICA'),
        ('RURAL', 'RURAL'),
        ('BILINGÜE INTERCULTURAL', 'BILINGÜE INTERCULTURAL'),
        ('CONTEXTO DE ENCIERRO', 'CONTEXTO DE ENCIERRO'),
        ('HOSPITALARIA - DOMICILIARIA', 'HOSPITALARIA - DOMICILIARIA'),
        ('EDUCACIÓN FÍSICA', 'EDUCACIÓN FÍSICA'),
    ]
    
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
    
    region_esc = forms.ChoiceField(choices=REGIONES_CHOICES, required=True) 
    oferta = forms.ChoiceField(choices=OFERTAS_CHOICES, required=True)
    modalidad = forms.ChoiceField(choices=MODALIDADES_CHOICES, required=True)
    
    class Meta:
        model = EscuelaSupervisor
        fields = '__all__'
        
    def clean_cueanexo(self):
        """
        Valida el campo 'cueanexo'.

        Asegura que el Cueanexo comience con '22' y contenga 9 dígitos en total.

        Returns:
            str: El cueanexo validado.

        Raises:
            ValidationError: Si el cueanexo no cumple con los criterios.
        """
        
        cueanexo = self.cleaned_data.get('cueanexo')
        if cueanexo:
            if not re.match(r'^22\d{7}$', cueanexo):
                raise forms.ValidationError("El campo Cueanexo debe comenzar con '22' y contener 9 dígitos en total.")
        return cueanexo  


class FiltroRegionalForm(forms.Form):
    """
    Formulario para filtrar resultados por región.

    Attributes:
        region (ChoiceField): Campo opcional para seleccionar la región.
    """
    
    region = forms.ChoiceField(required=False, label='Regional')    

    def __init__(self, *args, **kwargs):
        """
        Inicializa el formulario y asigna las opciones de regiones basadas en el usuario.

        Args:
            *args: Argumentos posicionales.
            **kwargs: Argumentos keyword, incluyendo el usuario.
        """
        
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        if user:
            Regional = DirectoresRegionales.objects.filter(dni_reg=user.username).values_list('region_reg', flat=True).distinct()
            
            # Asigna las opciones solo si hay valores de 'Regional'
            if Regional.exists():
                self.fields['region'].choices = [(regional, regional) for regional in Regional]
            else:
                self.fields['region'].choices = [('', '----')]  # Opción predeterminada si no hay regiones disponibles.
        