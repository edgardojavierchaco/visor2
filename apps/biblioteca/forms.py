import re
from pyexpat import model
from django import forms
from django.core.validators import MinValueValidator
from django.core.exceptions import ValidationError
from shapely import length
from datetime import date
from .models import (
    ServiciosMatBiblio, MaterialBibliografico, ServicioReferencia,
    ServicioReferenciaVirtual, ServicioPrestamo, InformePedagogico,
    AsistenciaUsuarios, InstitucionesPrestaServicios, ProcesosTecnicos, Aguapey,
    GenerarInforme, PlanillasAnexas, DestinoFondos, RegistroDestinoFondos,
        DocentePonMensual, NoDocentesMensual, BibliotecariosCue,
)


# Formulario para MaterialBibliografico
class MaterialBibliograficoForm(forms.ModelForm):            

    class Meta:
        model = MaterialBibliografico
        fields = '__all__'
        widgets = {
            'cueanexo': forms.TextInput(attrs={
                'class': 'form-control',
                'max_length': '9',
                'style': 'width: 100px; text-align: center;',
                'readonly': 'readonly'
            }),
            'mes': forms.TextInput(attrs={
                'class': 'form-control',
                'readonly': 'readonly'
            }),
            'anio': forms.NumberInput(attrs={
                'class': 'form-control',
                'max_length': '4',
                'style': 'width: 100px; text-align: center;',
                'readonly': 'readonly'
            }),
            'servicio': forms.Select(attrs={'class': 'form-control'}),
            'turnos': forms.Select(attrs={'class': 'form-control'}),
            't_material': forms.Select(attrs={
                'class': 'form-control',
                'style': 'width: 100px; text-align: center;'
            }),
            'cantidad': forms.NumberInput(attrs={
                'class': 'form-control',
                'max_length': '3',
                'style': 'width: 100px; text-align: center;',
                'min': '0'  # 🔥 FRONTEND
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields['servicio'].queryset = ServiciosMatBiblio.objects.filter(
            cod_servicio__range=(110, 113)
        )

        self.fields['cantidad'].required = True

    # 🔒 NO NEGATIVOS
    def clean_cantidad(self):
        cantidad = self.cleaned_data.get('cantidad')

        if cantidad is None:
            raise forms.ValidationError('Este campo es obligatorio.')

        if cantidad < 0:
            raise forms.ValidationError('No se permiten valores negativos.')

        # 🔥 OPCIONAL: límite lógico
        if cantidad > 999999999:
            raise forms.ValidationError('Valor demasiado alto.')

        return cantidad

# Formulario para ServicioReferencia
class ServicioReferenciaForm(forms.ModelForm):

    class Meta:
        model = ServicioReferencia
        fields = '__all__'
        widgets = {
            'cueanexo': forms.TextInput(attrs={
                'class': 'form-control',
                'style': 'width: 100px; text-align: center;',
                'readonly': 'readonly'
            }),
            'mes': forms.TextInput(attrs={
                'class': 'form-control',
                'style': 'width: 100px; text-align: center;',
                'readonly': 'readonly'
            }),
            'anio': forms.NumberInput(attrs={
                'class': 'form-control',
                'style': 'width: 100px; text-align: center;',
                'readonly': 'readonly'
            }),
            'servicio': forms.Select(attrs={
                'class': 'form-control'
            }),
            'turnos': forms.Select(attrs={
                'class': 'form-control'
            }),
            'varones': forms.NumberInput(attrs={
                'class': 'form-control',
                'style': 'width: 100px; text-align: center;'
            }),
            'total': forms.NumberInput(attrs={
                'class': 'form-control',
                'style': 'width: 100px; text-align: center;'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Filtrado de servicios SIEMPRE (no depende de instance)
        self.fields['servicio'].queryset = ServiciosMatBiblio.objects.filter(
            cod_servicio__range=(210, 213)
        )

        # Campos obligatorios
        self.fields['varones'].required = True
        self.fields['total'].required = True

    def clean_varones(self):
        varones = self.cleaned_data.get('varones')
        if varones is not None and varones < 0:
            raise ValidationError("Varones no puede ser negativo.")
        return varones

    def clean_total(self):
        total = self.cleaned_data.get('total')
        if total is not None and total < 0:
            raise ValidationError("El total no puede ser negativo.")
        return total

    def clean(self):
        cleaned_data = super().clean()

        varones = cleaned_data.get('varones')
        total = cleaned_data.get('total')

        # Validación cruzada
        if varones is not None and total is not None:
            if total < varones:
                self.add_error('total', 'El Total no puede ser menor que Varones.')

        return cleaned_data

        
# Formulario para ServicioReferenciaVirtual
class ServicioReferenciaVirtualForm(forms.ModelForm):

    class Meta:
        model = ServicioReferenciaVirtual
        fields = '__all__'
        widgets = {
            'cueanexo': forms.TextInput(attrs={
                'class': 'form-control',
                'style': 'width: 100px; text-align: center;',
                'readonly': 'readonly'
            }),
            'mes': forms.TextInput(attrs={
                'class': 'form-control',
                'style': 'width: 100px; text-align: center;',
                'readonly': 'readonly'
            }),
            'anio': forms.NumberInput(attrs={
                'class': 'form-control',
                'style': 'width: 100px; text-align: center;',
                'readonly': 'readonly'
            }),
            'servicio': forms.Select(attrs={
                'class': 'form-control'
            }),
            'turnos': forms.Select(attrs={
                'class': 'form-control'
            }),
            'varones': forms.NumberInput(attrs={
                'class': 'form-control',
                'style': 'width: 100px; text-align: center;'
            }),
            'total': forms.NumberInput(attrs={
                'class': 'form-control',
                'style': 'width: 100px; text-align: center;'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Filtrado de servicios virtuales
        self.fields['servicio'].queryset = ServiciosMatBiblio.objects.filter(
            cod_servicio__range=(310, 313)
        )

        # Obligatorios
        self.fields['varones'].required = True
        self.fields['total'].required = True

    def clean_varones(self):
        varones = self.cleaned_data.get('varones')
        if varones is not None and varones < 0:
            raise ValidationError("Varones no puede ser negativo.")
        return varones

    def clean_total(self):
        total = self.cleaned_data.get('total')
        if total is not None and total < 0:
            raise ValidationError("El total no puede ser negativo.")
        return total

    def clean(self):
        cleaned_data = super().clean()

        varones = cleaned_data.get('varones')
        total = cleaned_data.get('total')

        # Validación cruzada
        if varones is not None and total is not None:
            if total < varones:
                self.add_error('total', 'El Total no puede ser menor que Varones.')

        return cleaned_data
        

# Formulario para ServicioPrestamo
class ServicioPrestamoForm(forms.ModelForm):

    class Meta:
        model = ServicioPrestamo
        fields = '__all__'
        widgets = {
            'cueanexo': forms.TextInput(attrs={
                'class': 'form-control',
                'style': 'width: 100px; text-align: center;',
                'readonly': 'readonly'
            }),
            'mes': forms.TextInput(attrs={
                'class': 'form-control',
                'style': 'width: 100px; text-align: center;',
                'readonly': 'readonly'
            }),
            'anio': forms.NumberInput(attrs={
                'class': 'form-control',
                'style': 'width: 100px; text-align: center;',
                'readonly': 'readonly'
            }),
            'servicio': forms.Select(attrs={
                'class': 'form-control'
            }),
            'turnos': forms.Select(attrs={
                'class': 'form-control'
            }),
            'instalacion': forms.Select(attrs={
                'class': 'form-control'
            }),
            'total': forms.NumberInput(attrs={
                'class': 'form-control',
                'style': 'width: 100px; text-align: center;'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Servicios de préstamo
        self.fields['servicio'].queryset = ServiciosMatBiblio.objects.filter(
            cod_servicio__range=(410, 415)
        )

        # Obligatorio
        self.fields['total'].required = True

    def clean_total(self):
        total = self.cleaned_data.get('total')

        if total is not None and total < 0:
            raise ValidationError("El total no puede ser negativo.")

        return total

    def clean(self):
        cleaned_data = super().clean()
        total = cleaned_data.get('total')

        # Validación general extra (por si después agregás más campos)
        if total is None:
            self.add_error('total', 'El total es obligatorio.')

        return cleaned_data
        

# Formulario para InformePedagogico
class InformePedagogicoForm(forms.ModelForm):

    class Meta:
        model = InformePedagogico
        fields = '__all__'
        widgets = {
            'cueanexo': forms.TextInput(attrs={
                'class': 'form-control',
                'style': 'width: 100px; text-align: center;',
                'readonly': 'readonly'
            }),
            'mes': forms.TextInput(attrs={
                'class': 'form-control',
                'style': 'width: 100px; text-align: center;',
                'readonly': 'readonly'
            }),
            'anio': forms.NumberInput(attrs={
                'class': 'form-control',
                'style': 'width: 100px; text-align: center;',
                'readonly': 'readonly'
            }),
            'servicio': forms.Select(attrs={
                'class': 'form-control'
            }),
            'varones': forms.NumberInput(attrs={
                'class': 'form-control',
                'style': 'width: 100px; text-align: center;'
            }),
            'total': forms.NumberInput(attrs={
                'class': 'form-control',
                'style': 'width: 100px; text-align: center;'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Servicios pedagógicos
        self.fields['servicio'].queryset = ServiciosMatBiblio.objects.filter(
            cod_servicio__range=(510, 528)
        )

        # Obligatorios
        self.fields['varones'].required = True
        self.fields['total'].required = True

    def clean_varones(self):
        varones = self.cleaned_data.get('varones')
        if varones is not None and varones < 0:
            raise ValidationError("Varones no puede ser negativo.")
        return varones

    def clean_total(self):
        total = self.cleaned_data.get('total')
        if total is not None and total < 0:
            raise ValidationError("El total no puede ser negativo.")
        return total

    def clean(self):
        cleaned_data = super().clean()

        varones = cleaned_data.get('varones')
        total = cleaned_data.get('total')

        # Validación cruzada
        if varones is not None and total is not None:
            if total < varones:
                self.add_error('total', 'El Total no puede ser menor que Varones.')

        return cleaned_data

# Formulario para AsistenciaUsuarios
class AsistenciaUsuariosForm(forms.ModelForm):
        class Meta:
                model = AsistenciaUsuarios
                fields = '__all__'
                widgets = {
                        'cueanexo': forms.TextInput(attrs={'class': 'form-control', 
                                'style': 'width: 100px; text-align: center;', 'readonly': 'readonly'}),
                        'mes': forms.TextInput(attrs={'class': 'form-control', 
                                'style': 'width: 100px; text-align: center;', 'readonly': 'readonly'}),
                        'anio': forms.NumberInput(attrs={'class': 'form-control', 
                                'style': 'width: 100px; text-align: center;', 'readonly': 'readonly'}),
                        'nivel': forms.Select(attrs={'class': 'form-control'}),
                        'usuario': forms.Select(attrs={'class': 'form-control'}),
                        'varones': forms.NumberInput(attrs={
                                'class': 'form-control',
                                'style': 'width: 100px; text-align: center;',
                                'min': '0'  
                        }),
                        'total': forms.NumberInput(attrs={
                                'class': 'form-control',
                                'style': 'width: 100px; text-align: center;',
                                'min': '0'  
                        }),
                }

        def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self.fields['varones'].required = True
                self.fields['total'].required = True

        # 🔒 NO NEGATIVOS
        def clean_varones(self):
                varones = self.cleaned_data.get('varones')
                if varones is not None and varones < 0:
                        raise forms.ValidationError('No se permiten valores negativos.')
                return varones

        def clean_total(self):
                total = self.cleaned_data.get('total')
                if total is not None and total < 0:
                        raise forms.ValidationError('No se permiten valores negativos.')
                return total

        # 🔗 RELACIÓN ENTRE CAMPOS
        def clean(self):
                cleaned_data = super().clean()

                varones = cleaned_data.get('varones')
                total = cleaned_data.get('total')

                if varones is not None and total is not None:
                        if total < varones:
                                self.add_error('total', 'El Total no puede ser menor que Varones.')

                return cleaned_data

# Formulario para InstitucionesPrestaServicios
class InstitucionesPrestaServiciosForm(forms.ModelForm):

    class Meta:
        model = InstitucionesPrestaServicios
        fields = '__all__'
        widgets = {
            'cueanexo': forms.TextInput(attrs={
                'class': 'form-control',
                'style': 'width: 100px; text-align: center;',
                'readonly': 'readonly'
            }),
            'mes': forms.TextInput(attrs={
                'class': 'form-control',
                'style': 'width: 100px; text-align: center;',
                'readonly': 'readonly'
            }),
            'anio': forms.NumberInput(attrs={
                'class': 'form-control',
                'style': 'width: 100px; text-align: center;',
                'readonly': 'readonly'
            }),
            'escuela': forms.TextInput(attrs={
                'class': 'form-control'
            }),
            'matricula': forms.NumberInput(attrs={
                'class': 'form-control',
                'style': 'width: 100px; text-align: center;'
            }),
            'docentes': forms.NumberInput(attrs={
                'class': 'form-control',
                'style': 'width: 100px; text-align: center;'
            }),
            'matricdisc': forms.NumberInput(attrs={
                'class': 'form-control',
                'style': 'width: 100px; text-align: center;'
            }),
            'etnia': forms.NumberInput(attrs={
                'class': 'form-control',
                'style': 'width: 100px; text-align: center;'
            }),
        }

    def clean(self):
        cleaned_data = super().clean()

        matricula = cleaned_data.get('matricula')
        matricdisc = cleaned_data.get('matricdisc')
        etnia = cleaned_data.get('etnia')

        # Si no hay matrícula no tiene sentido validar el resto
        if matricula is None:
            return cleaned_data

        # Validaciones individuales
        if matricdisc is not None and matricdisc < 0:
            self.add_error('matricdisc', 'No puede ser negativa.')

        if etnia is not None and etnia < 0:
            self.add_error('etnia', 'No puede ser negativa.')

        # No pueden superar matrícula individualmente
        if matricdisc is not None and matricdisc > matricula:
            self.add_error('matricdisc', 'No puede ser mayor que la matrícula total.')

        if etnia is not None and etnia > matricula:
            self.add_error('etnia', 'No puede ser mayor que la matrícula total.')

        # Validación combinada
        if matricdisc is not None and etnia is not None:
            if matricdisc + etnia > matricula:
                msg = 'La suma de discapacidad y etnia no puede superar la matrícula total.'
                self.add_error('matricdisc', msg)
                self.add_error('etnia', msg)

        return cleaned_data


# Formulario para ProcesosTecnicos
class ProcesosTecnicosForm(forms.ModelForm):

    class Meta:
        model = ProcesosTecnicos
        fields = '__all__'
        widgets = {
            'cueanexo': forms.TextInput(attrs={
                'class': 'form-control',
                'style': 'width: 100px; text-align: center;',
                'readonly': 'readonly'
            }),
            'mes': forms.TextInput(attrs={
                'class': 'form-control',
                'style': 'width: 100px; text-align: center;',
                'readonly': 'readonly'
            }),
            'anio': forms.NumberInput(attrs={
                'class': 'form-control',
                'style': 'width: 100px; text-align: center;',
                'readonly': 'readonly'
            }),
            'material': forms.Select(attrs={
                'class': 'form-control'
            }),
            'procesos': forms.Select(attrs={
                'class': 'form-control'
            }),
            'total': forms.NumberInput(attrs={
                'class': 'form-control',
                'style': 'width: 100px; text-align: center;'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields['total'].required = True

    def clean_total(self):
        total = self.cleaned_data.get('total')

        if total is not None and total < 0:
            raise ValidationError("El total no puede ser negativo.")

        return total

    def clean(self):
        cleaned_data = super().clean()

        total = cleaned_data.get('total')

        if total is None:
            self.add_error('total', 'El total es obligatorio.')

        return cleaned_data


# Formulario para Aguapey
class AguapeyForm(forms.ModelForm):

    class Meta:
        model = Aguapey
        fields = '__all__'
        widgets = {
            'cueanexo': forms.TextInput(attrs={
                'class': 'form-control',
                'style': 'width: 100px; text-align: center;',
                'readonly': 'readonly'
            }),
            'mes': forms.TextInput(attrs={
                'class': 'form-control',
                'style': 'width: 100px; text-align: center;',
                'readonly': 'readonly'
            }),
            'anio': forms.NumberInput(attrs={
                'class': 'form-control',
                'style': 'width: 100px; text-align: center;',
                'readonly': 'readonly'
            }),
            'total_mes': forms.NumberInput(attrs={
                'class': 'form-control',
                'style': 'width: 100px; text-align: center;'
            }),
            'total_base': forms.NumberInput(attrs={
                'class': 'form-control',
                'style': 'width: 100px; text-align: center;'
            }),
            'total_usuarios': forms.NumberInput(attrs={
                'class': 'form-control',
                'style': 'width: 100px; text-align: center;'
            }),
            'observaciones': forms.Textarea(attrs={
                'class': 'form-control',
                'style': 'width: 100%; height: 100px;'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Obligatorios
        self.fields['total_mes'].required = True
        self.fields['total_base'].required = True

    def clean_total_mes(self):
        total_mes = self.cleaned_data.get('total_mes')

        if total_mes is not None and total_mes < 0:
            raise ValidationError("El total del mes no puede ser negativo.")

        return total_mes

    def clean_total_base(self):
        total_base = self.cleaned_data.get('total_base')

        if total_base is not None and total_base < 0:
            raise ValidationError("El total base no puede ser negativo.")

        return total_base

    def clean_total_usuarios(self):
        total_usuarios = self.cleaned_data.get('total_usuarios')

        if total_usuarios is not None and total_usuarios < 0:
            raise ValidationError("El total de usuarios no puede ser negativo.")

        return total_usuarios

    def clean(self):
        cleaned_data = super().clean()

        total_mes = cleaned_data.get('total_mes')
        total_base = cleaned_data.get('total_base')
        total_usuarios = cleaned_data.get('total_usuarios')

        # Validación principal: coherencia mes vs base
        if total_mes is not None and total_base is not None:
            if total_mes > total_base:
                self.add_error(
                    'total_mes',
                    'El total del mes no puede ser mayor que el total base.'
                )

        # Validación lógica adicional (muy útil en sistemas reales)
        if total_usuarios is not None and total_base is not None:
            if total_usuarios > total_base:
                self.add_error(
                    'total_usuarios',
                    'El total de usuarios no puede superar el total base.'
                )

        return cleaned_data
        

#Formulario para GenerarInforme
class GenerarInformeForm(forms.ModelForm):
        class Meta:
                model = GenerarInforme
                fields = ['meses', 'annos']  # Excluir cueanexo y estado, ya que se asignan en la vista
                widgets = {
                'meses': forms.Select(attrs={'class': 'form-control'}),
                'annos': forms.NumberInput(attrs={'class': 'form-control', 'max_length': '4'}),
                }

        cueanexo = forms.CharField(
                widget=forms.TextInput(attrs={'class': 'form-control', 'readonly': 'readonly'}),
                required=False  # Para evitar errores en el formulario
        )

        estado = forms.CharField(
                widget=forms.TextInput(attrs={'class': 'form-control', 'readonly': 'readonly'}),
                required=False  # Se asigna en la vista
        )


# Formulario para Planillas Anexas
class PlanillasAnexasForm(forms.ModelForm):    
        
        class Meta:
                model = PlanillasAnexas
                fields = '__all__'
                widgets = {
                'cueanexo': forms.TextInput(attrs={'class': 'form-control','max_length':'9', 
                        'style': 'width: 100px; text-align: center;', 'readonly':'readonly'}),
                'mes': forms.TextInput(attrs={'class': 'form-control', 'readonly':'readonly'}),
                'anio': forms.NumberInput(attrs={'class': 'form-control', 'max_length':'4', 
                        'style': 'width: 100px; text-align: center;', 'readonly':'readonly'}),
                'servicio': forms.Select(attrs={'class': 'form-control'}),            
                'cantidad': forms.NumberInput(attrs={'class': 'form-control', 'max_length':'3',
                        'style': 'width: 100px; text-align: center;' }),
                }
        
        def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self.fields['servicio'].queryset = ServiciosMatBiblio.objects.filter(cod_servicio__gt=710)

                self.fields['cantidad'].required = True



class RegistroDestinoFondosForm(forms.ModelForm):

        class Meta:
                model = RegistroDestinoFondos
                fields = '__all__'
                widgets = {
                'cueanexo': forms.TextInput(attrs={
                        'class': 'form-control',
                        'style': 'width: 100px; text-align: center;',
                        'readonly': 'readonly'
                }),
                'mes': forms.TextInput(attrs={
                        'class': 'form-control',
                        'readonly': 'readonly'
                }),
                'anio': forms.NumberInput(attrs={
                        'class': 'form-control',
                        'style': 'width: 100px; text-align: center;',
                        'readonly': 'readonly'
                }),
                'destino': forms.Select(attrs={'class': 'form-control'}),
                'descripcion': forms.TextInput(attrs={'class': 'form-control'}),
                'cantidad': forms.NumberInput(attrs={'class': 'form-control'}),
                }

        def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self.fields['destino'].queryset = DestinoFondos.objects.all()

                self.fields['cantidad'].required = True



                

class NoDocentesMensualForm(forms.ModelForm):
    class Meta:
        model = NoDocentesMensual
        fields = '__all__'  # Incluir todos los campos del modelo
        widgets = {
                'id': forms.TextInput(attrs={'class': 'form-control', 'readonly': 'readonly'}),
                'cueanexo': forms.TextInput(attrs={'class': 'form-control'}),
                'cuof': forms.TextInput(attrs={'class': 'form-control'}),
                'cuof_anexo': forms.TextInput(attrs={'class': 'form-control'}),
                'ptaid': forms.TextInput(attrs={'class': 'form-control'}),
                'apellidos': forms.TextInput(attrs={'class': 'form-control'}),
                'nombres': forms.TextInput(attrs={'class': 'form-control'}),
                'ndoc': forms.TextInput(attrs={'class': 'form-control'}),
                'cuil': forms.TextInput(attrs={'class': 'form-control'}),        
                'f_nac': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
                'denom_cargo': forms.TextInput(attrs={'class': 'form-control'}),
                'categ': forms.Select(attrs={'class': 'form-control'}),
                'gpo': forms.Select(attrs={'class': 'form-control'}),
                'apart': forms.Select(attrs={'class': 'form-control'}),
                'f_desde': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
                'f_hasta': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
                'regional': forms.Select(attrs={'class': 'form-control'}),
                'localidad': forms.Select(attrs={'class': 'form-control'}),
        }

  
class DocentePonMensualForm(forms.ModelForm):
    class Meta:
        model = DocentePonMensual
        fields = '__all__' 
        widgets = {
                'id': forms.TextInput(attrs={'class': 'form-control', 'readonly': 'readonly'}),
                'cueanexo': forms.TextInput(attrs={'class': 'form-control'}),
                'cuof': forms.TextInput(attrs={'class': 'form-control'}),
                'cuof_anexo': forms.TextInput(attrs={'class': 'form-control'}),
                'ptaid': forms.TextInput(attrs={'class': 'form-control'}),
                'apellidos': forms.TextInput(attrs={'class': 'form-control'}),
                'nombres': forms.TextInput(attrs={'class': 'form-control'}),
                'n_doc': forms.TextInput(attrs={'class': 'form-control'}),
                'cuil': forms.TextInput(attrs={'class': 'form-control'}),
                'f_nac': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
                'sit_rev': forms.Select(attrs={'class': 'form-control'}),
                'nivel': forms.Select(attrs={'class': 'form-control'}),
                'ceic': forms.TextInput(attrs={'class': 'form-control'}),
                'denom_cargo': forms.TextInput(attrs={'class': 'form-control'}),
                'f_desde': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
                'f_hasta': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
                'regional': forms.Select(attrs={'class': 'form-control'}),
                'localidad': forms.Select(attrs={'class': 'form-control'}), 
                'carga_horaria': forms.NumberInput(attrs={'class': 'form-control'}),
        }

class BibliotecariosCueForm(forms.ModelForm):
    class Meta:
        model = BibliotecariosCue
        exclude = ['cueanexo']
        widgets = {
            'f_nac': forms.DateInput(format='%Y-%m-%d', attrs={'type': 'date'}),
            'f_ingreso': forms.DateInput(format='%Y-%m-%d', attrs={'type': 'date'}),
            'f_hasta': forms.DateInput(format='%Y-%m-%d', attrs={'type': 'date'}),
            'f_desde_lic': forms.DateInput(format='%Y-%m-%d', attrs={'type': 'date'}),
            'f_hasta_lic': forms.DateInput(format='%Y-%m-%d', attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for field in ['f_nac', 'f_ingreso', 'f_hasta', 'f_desde_lic', 'f_hasta_lic']:
            self.fields[field].input_formats = ['%Y-%m-%d']
            
    def clean_n_doc(self):
        n_doc = self.cleaned_data.get('n_doc', '')
        if not n_doc.isdigit():
            raise forms.ValidationError("Debe contener solo números.")
        if len(n_doc) < 7:
            raise forms.ValidationError("Debe tener al menos 7 dígitos.")
        return n_doc

    def clean_apellidos(self):
        apellidos = self.cleaned_data.get('apellidos', '').upper()

        if not re.match(r'^[A-ZÁÉÍÓÚÑ\s]+$', apellidos):
                raise forms.ValidationError("El apellido solo puede contener letras.")

        return apellidos


    def clean_nombres(self):
        nombres = self.cleaned_data.get('nombres', '').upper()

        if not re.match(r'^[A-ZÁÉÍÓÚÑ\s]+$', nombres):
                raise forms.ValidationError("El nombre solo puede contener letras.")

        return nombres

    def clean(self):
        cleaned_data = super().clean()
        
        f_nac = cleaned_data.get('f_nac')
        f_ingreso = cleaned_data.get('f_ingreso')
        f_hasta = cleaned_data.get('f_hasta')
        f_desde_lic = cleaned_data.get('f_desde_lic')
        f_hasta_lic = cleaned_data.get('f_hasta_lic')
        licencia = cleaned_data.get('licencia_permiso')

        hoy = date.today()

        # =========================
        # 🔹 Fecha de nacimiento no futura
        # =========================
        if f_nac and f_nac > hoy:
                self.add_error('f_nac', 'La fecha de nacimiento no puede ser futura.')

        # =========================
        # 🔹 Fecha de ingreso no futura
        # =========================
        if f_ingreso and f_ingreso > hoy:
                self.add_error('f_ingreso', 'La fecha de ingreso no puede ser futura.')

        # =========================
        # 1️⃣ Edad mínima 18 años al ingreso
        # =========================
        if f_nac and f_ingreso:
                edad = f_ingreso.year - f_nac.year - (
                        (f_ingreso.month, f_ingreso.day) < (f_nac.month, f_nac.day)
                )
                if edad < 18:
                        self.add_error('f_ingreso', 'Debe tener al menos 18 años al momento del ingreso.')

        # =========================
        # 2️⃣ f_hasta >= f_ingreso
        # =========================
        if f_ingreso and f_hasta:
                if f_hasta < f_ingreso:
                        self.add_error('f_hasta', 'La fecha hasta no puede ser menor que la fecha de ingreso.')

        # =========================
        # 3️⃣ Validaciones de licencia
        # =========================
        if licencia:
                if not f_desde_lic:
                        self.add_error('f_desde_lic', "Debe completar esta fecha.")
                if not f_hasta_lic:
                        self.add_error('f_hasta_lic', "Debe completar esta fecha.")

                if f_desde_lic and f_hasta_lic:
                        if f_hasta_lic < f_desde_lic:
                                self.add_error('f_hasta_lic', "La fecha hasta no puede ser menor que la fecha desde.")

        elif f_desde_lic or f_hasta_lic:
                self.add_error('licencia_permiso', "Debe seleccionar un tipo de licencia si indica fechas.")

        return cleaned_data