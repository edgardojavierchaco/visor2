from django import forms
from .models import (
    ExamenFluidezSegundo,
    ExamenFluidezTercero, 
    ExamenLenguaAlumno, 
    ExamenMatematicaAlumno,
    ExamenMatematicaQuintoGrado,
    )
from decimal import Decimal

class ExamenLenguaAlumnoForm(forms.ModelForm):
    class Meta:
        model = ExamenLenguaAlumno
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)  
        region = kwargs.pop('region', None)
        super().__init__(*args, **kwargs)
        if user:
            self.fields['cueanexo'].initial = user.username
            self.fields['cueanexo'].disabled = True
        if region:
            self.fields['region'].initial = region
            self.fields['region'].disabled = True

    def clean_dni(self):
        dni = self.cleaned_data.get("dni", "").strip()

        # Validar que no tenga puntos, comas, ni espacios
        if any(c in dni for c in ['.', ',', ' ']):
            raise forms.ValidationError("El DNI no debe contener puntos, comas ni espacios.")

        # Validar que tenga exactamente 8 dígitos y solo números
        if not dni.isdigit() or len(dni) != 8:
            raise forms.ValidationError("El DNI debe tener exactamente 8 dígitos numéricos.")

        # Validar duplicado
        if ExamenLenguaAlumno.objects.filter(dni=dni).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("Ya existe un alumno con este DNI.")
        
        return dni

    def clean_apellidos(self):
        apellidos = self.cleaned_data.get("apellidos", "").strip()
        if apellidos != apellidos.upper():
            raise forms.ValidationError("El campo Apellidos debe estar TODO en mayúsculas.")
        return apellidos

    def clean_nombres(self):
        nombres = self.cleaned_data.get("nombres", "").strip()
        if nombres != nombres.upper():
            raise forms.ValidationError("El campo Nombres debe estar TODO en mayúsculas.")
        return nombres

    def clean(self):
        cleaned_data = super().clean()

        # Validación de campos requeridos
        for field_name in ['dni', 'apellidos', 'nombres', 'discapacidad', 'etnia']:
            if not cleaned_data.get(field_name):
                self.add_error(field_name, "Este campo es obligatorio.")

        # Validación de formato decimal: exactamente 2 decimales y punto como separador
        for field_name, value in cleaned_data.copy().items():
            if isinstance(value, Decimal):
                valor_str = str(value)
                if ',' in valor_str:
                    self.add_error(field_name, "Usá punto (.) como separador decimal, no coma (,).")
                partes = valor_str.split('.')
                if len(partes) != 2 or len(partes[1]) != 2:
                    self.add_error(field_name, "Debe tener exactamente dos decimales (por ejemplo: 7.00).")

        return cleaned_data


class ExamenMatematicaAlumnoForm(forms.ModelForm):
    class Meta:
        model = ExamenMatematicaAlumno
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)  
        region = kwargs.pop('region', None)
        super().__init__(*args, **kwargs)
        if user:
            self.fields['cueanexo'].initial = user.username
            self.fields['cueanexo'].disabled = True
        if region:
            self.fields['region'].initial = region
            self.fields['region'].disabled = True

    def clean_dni(self):
        dni = self.cleaned_data.get("dni", "").strip()

        # Validar que no tenga puntos, comas, ni espacios
        if any(c in dni for c in ['.', ',', ' ']):
            raise forms.ValidationError("El DNI no debe contener puntos, comas ni espacios.")

        # Validar que tenga exactamente 8 dígitos y solo números
        if not dni.isdigit() or len(dni) != 8:
            raise forms.ValidationError("El DNI debe tener exactamente 8 dígitos numéricos.")

        # Validar duplicado
        if ExamenMatematicaAlumno.objects.filter(dni=dni).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("Ya existe un alumno con este DNI.")
        
        return dni

    def clean_apellidos(self):
        apellidos = self.cleaned_data.get("apellidos", "").strip()
        if apellidos != apellidos.upper():
            raise forms.ValidationError("El campo Apellidos debe estar TODO en mayúsculas.")
        return apellidos

    def clean_nombres(self):
        nombres = self.cleaned_data.get("nombres", "").strip()
        if nombres != nombres.upper():
            raise forms.ValidationError("El campo Nombres debe estar TODO en mayúsculas.")
        return nombres

    def clean(self):
        cleaned_data = super().clean()

        # Validación de campos requeridos
        for field_name in ['dni', 'apellidos', 'nombres', 'discapacidad','etnia']:
            if not cleaned_data.get(field_name):
                self.add_error(field_name, "Este campo es obligatorio.")

        # Validación de formato decimal: exactamente 2 decimales y punto como separador
        for field_name, value in cleaned_data.copy().items():
            if isinstance(value, Decimal):
                valor_str = str(value)
                if ',' in valor_str:
                    self.add_error(field_name, "Usá punto (.) como separador decimal, no coma (,).")
                partes = valor_str.split('.')
                if len(partes) != 2 or len(partes[1]) != 2:
                    self.add_error(field_name, "Debe tener exactamente dos decimales (por ejemplo: 7.00).")

        return cleaned_data

##################################
#  FLUIDEZ LECTORA 2 Y 3 GRADO   #
##################################

class ExamenFluidezSegundoForm(forms.ModelForm):
    class Meta:
        model = ExamenFluidezSegundo
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)  
        region = kwargs.pop('region', None)
        super().__init__(*args, **kwargs)
        if user:
            self.fields['cueanexo'].initial = user.username
            self.fields['cueanexo'].disabled = True
        if region:
            self.fields['region'].initial = region
            self.fields['region'].disabled = True

    def clean_dni(self):
        dni = self.cleaned_data.get("dni", "").strip()

        # Validar que no tenga puntos, comas, ni espacios
        if any(c in dni for c in ['.', ',', ' ']):
            raise forms.ValidationError("El DNI no debe contener puntos, comas ni espacios.")

        # Validar que tenga exactamente 8 dígitos y solo números
        if not dni.isdigit() or len(dni) != 8:
            raise forms.ValidationError("El DNI debe tener exactamente 8 dígitos numéricos.")

        # Validar duplicado
        if ExamenLenguaAlumno.objects.filter(dni=dni).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("Ya existe un alumno con este DNI.")
        
        return dni

    def clean_apellidos(self):
        apellidos = self.cleaned_data.get("apellidos", "").strip()
        if apellidos != apellidos.upper():
            raise forms.ValidationError("El campo Apellidos debe estar TODO en mayúsculas.")
        return apellidos

    def clean_nombres(self):
        nombres = self.cleaned_data.get("nombres", "").strip()
        if nombres != nombres.upper():
            raise forms.ValidationError("El campo Nombres debe estar TODO en mayúsculas.")
        return nombres

    def clean(self):
        cleaned_data = super().clean()

        # Validación de campos requeridos
        for field_name in ['dni', 'apellidos', 'nombres', 'discapacidad', 'etnia']:
            if not cleaned_data.get(field_name):
                self.add_error(field_name, "Este campo es obligatorio.")

        # Validación de formato decimal: exactamente 2 decimales y punto como separador
        for field_name, value in cleaned_data.copy().items():
            if isinstance(value, Decimal):
                valor_str = str(value)
                if ',' in valor_str:
                    self.add_error(field_name, "Usá punto (.) como separador decimal, no coma (,).")
                partes = valor_str.split('.')
                if len(partes) != 2 or len(partes[1]) != 2:
                    self.add_error(field_name, "Debe tener exactamente dos decimales (por ejemplo: 7.00).")

        return cleaned_data
    
    def clean_grado(self):
        grado = self.cleaned_data.get("grado", "").strip()
        if grado != '2':
            raise forms.ValidationError("El grado debe ser 2")
        return grado

    
######################################

class ExamenFluidezTerceroForm(forms.ModelForm):
    class Meta:
        model = ExamenFluidezTercero
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)  
        region = kwargs.pop('region', None)
        super().__init__(*args, **kwargs)
        if user:
            self.fields['cueanexo'].initial = user.username
            self.fields['cueanexo'].disabled = True
        if region:
            self.fields['region'].initial = region
            self.fields['region'].disabled = True

    def clean_dni(self):
        dni = self.cleaned_data.get("dni", "").strip()

        # Validar que no tenga puntos, comas, ni espacios
        if any(c in dni for c in ['.', ',', ' ']):
            raise forms.ValidationError("El DNI no debe contener puntos, comas ni espacios.")

        # Validar que tenga exactamente 8 dígitos y solo números
        if not dni.isdigit() or len(dni) != 8:
            raise forms.ValidationError("El DNI debe tener exactamente 8 dígitos numéricos.")

        # Validar duplicado
        if ExamenLenguaAlumno.objects.filter(dni=dni).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("Ya existe un alumno con este DNI.")
        
        return dni

    def clean_apellidos(self):
        apellidos = self.cleaned_data.get("apellidos", "").strip()
        if apellidos != apellidos.upper():
            raise forms.ValidationError("El campo Apellidos debe estar TODO en mayúsculas.")
        return apellidos

    def clean_nombres(self):
        nombres = self.cleaned_data.get("nombres", "").strip()
        if nombres != nombres.upper():
            raise forms.ValidationError("El campo Nombres debe estar TODO en mayúsculas.")
        return nombres

    def clean(self):
        cleaned_data = super().clean()

        # Validación de campos requeridos
        for field_name in ['dni', 'apellidos', 'nombres', 'discapacidad', 'etnia']:
            if not cleaned_data.get(field_name):
                self.add_error(field_name, "Este campo es obligatorio.")

        # Validación de formato decimal: exactamente 2 decimales y punto como separador
        for field_name, value in cleaned_data.copy().items():
            if isinstance(value, Decimal):
                valor_str = str(value)
                if ',' in valor_str:
                    self.add_error(field_name, "Usá punto (.) como separador decimal, no coma (,).")
                partes = valor_str.split('.')
                if len(partes) != 2 or len(partes[1]) != 2:
                    self.add_error(field_name, "Debe tener exactamente dos decimales (por ejemplo: 7.00).")

        return cleaned_data
    
    def clean_grado(self):
        grado = self.cleaned_data.get("grado", "").strip()
        if grado != '3':
            raise forms.ValidationError("El grado debe ser 3")
        return grado


################################################################

class ExamenMatematicaQuintoGradoForm(forms.ModelForm): 
    class Meta:
        model = ExamenMatematicaQuintoGrado
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)  
        region = kwargs.pop('region', None)
        super().__init__(*args, **kwargs)
        if user:
            self.fields['cueanexo'].initial = user.username
            self.fields['cueanexo'].disabled = True
        if region:
            self.fields['region'].initial = region
            self.fields['region'].disabled = True
    
    def clean_dni(self):
        dni = self.cleaned_data.get("dni", "").strip()

        # Validar que no tenga puntos, comas, ni espacios
        if any(c in dni for c in ['.', ',', ' ']):
            raise forms.ValidationError("El DNI no debe contener puntos, comas ni espacios.")

        # Validar que tenga exactamente 8 dígitos y solo números
        if not dni.isdigit() or len(dni) != 8:
            raise forms.ValidationError("El DNI debe tener exactamente 8 dígitos numéricos.")

        # Validar duplicado
        if ExamenLenguaAlumno.objects.filter(dni=dni).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("Ya existe un alumno con este DNI.")
        
        return dni

    def clean_apellidos(self):
        apellidos = self.cleaned_data.get("apellidos", "").strip()
        if apellidos != apellidos.upper():
            raise forms.ValidationError("El campo Apellidos debe estar TODO en mayúsculas.")
        return apellidos

    def clean_nombres(self):
        nombres = self.cleaned_data.get("nombres", "").strip()
        if nombres != nombres.upper():
            raise forms.ValidationError("El campo Nombres debe estar TODO en mayúsculas.")
        return nombres

    def clean(self):
        cleaned_data = super().clean()

        # Validación de campos requeridos
        for field_name in ['dni', 'apellidos', 'nombres', 'discapacidad', 'etnia']:
            if not cleaned_data.get(field_name):
                self.add_error(field_name, "Este campo es obligatorio.")

        # Validación de formato decimal: exactamente 2 decimales y punto como separador
        for field_name, value in cleaned_data.copy().items():
            if isinstance(value, Decimal):
                valor_str = str(value)
                if ',' in valor_str:
                    self.add_error(field_name, "Usá punto (.) como separador decimal, no coma (,).")
                partes = valor_str.split('.')
                if len(partes) != 2 or len(partes[1]) != 2:
                    self.add_error(field_name, "Debe tener exactamente dos decimales (por ejemplo: 7.00).")

        return cleaned_data

    def clean_grado(self):
        grado = self.cleaned_data.get("grado", "").strip()
        if grado != '5':
            raise forms.ValidationError("El grado debe ser 5")
        return grado