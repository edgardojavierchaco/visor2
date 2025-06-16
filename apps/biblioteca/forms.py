from pyexpat import model
from django import forms
from django.core.validators import MinValueValidator
from django.core.exceptions import ValidationError
from shapely import length
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
                'cueanexo': forms.TextInput(attrs={'class': 'form-control','max_length':'9', 
                        'style': 'width: 100px; text-align: center;', 'readonly':'readonly'}),
                'mes': forms.TextInput(attrs={'class': 'form-control', 'readonly':'readonly'}),
                'anio': forms.NumberInput(attrs={'class': 'form-control', 'max_length':'4', 
                        'style': 'width: 100px; text-align: center;', 'readonly':'readonly'}),
                'servicio': forms.Select(attrs={'class': 'form-control'}),
                'turnos': forms.Select(attrs={'class': 'form-control'}),
                't_material': forms.Select(attrs={'class': 'form-control',
                        'style': 'width: 100px; text-align: center;' }),
                'cantidad': forms.NumberInput(attrs={'class': 'form-control', 'max_length':'3',
                        'style': 'width: 100px; text-align: center;' }),
                }
    
        def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self.fields['servicio'].queryset = ServiciosMatBiblio.objects.filter(cod_servicio__range=(110,113))
                
                self.fields['cantidad'].required = True
        

# Formulario para ServicioReferencia
class ServicioReferenciaForm(forms.ModelForm):
    class Meta:
        model = ServicioReferencia
        fields = '__all__'
        widgets = {
            'cueanexo': forms.TextInput(attrs={'class': 'form-control', 
                    'style': 'width: 100px; text-align: center;', 'readonly': 'readonly'}),
            'mes': forms.TextInput(attrs={'class': 'form-control', 
                    'style': 'width: 100px; text-align: center;', 'readonly': 'readonly'}),
            'anio': forms.NumberInput(attrs={'class': 'form-control', 
                    'style': 'width: 100px; text-align: center;', 'readonly': 'readonly'}),
            'servicio': forms.Select(attrs={'class': 'form-control'}),
            'turnos': forms.Select(attrs={'class': 'form-control'}),
            'varones': forms.NumberInput(attrs={'class': 'form-control',
                    'style': 'width: 100px; text-align: center;'}),
            'total': forms.NumberInput(attrs={'class': 'form-control',
                    'style': 'width: 100px; text-align: center;'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if 'instance' in kwargs:  
            self.fields['servicio'].queryset = ServiciosMatBiblio.objects.filter(cod_servicio__range=(210, 213))

        # Hacer que los campos sean obligatorios
        self.fields['varones'].required = True
        self.fields['total'].required = True

    def clean(self):
        cleaned_data = super().clean()
        varones = cleaned_data.get('varones')
        total = cleaned_data.get('total')

        # Validar que el total no sea menor que varones
        if varones is not None and total is not None and total < varones:
            self.add_error('total', 'El Total no puede ser menor que Varones.')
            raise ValidationError("Corrige los errores antes de continuar.")  # Evita que el formulario se guarde

        return cleaned_data
        
        
# Formulario para ServicioReferenciaVirtual
class ServicioReferenciaVirtualForm(forms.ModelForm):
        class Meta:
                model = ServicioReferenciaVirtual
                fields = '__all__'
                widgets = {
                'cueanexo': forms.TextInput(attrs={'class': 'form-control', 
                        'style': 'width: 100px; text-align: center;', 'readonly': 'readonly'}),
                'mes': forms.TextInput(attrs={'class': 'form-control', 
                        'style': 'width: 100px; text-align: center;', 'readonly': 'readonly'}),
                'anio': forms.NumberInput(attrs={'class': 'form-control', 
                        'style': 'width: 100px; text-align: center;', 'readonly': 'readonly'}),
                'servicio': forms.Select(attrs={'class': 'form-control'}),
                'turnos': forms.Select(attrs={'class': 'form-control'}),
                'varones': forms.NumberInput(attrs={'class': 'form-control', 
                        'style': 'width: 100px; text-align: center;'}),
                'total': forms.NumberInput(attrs={'class': 'form-control', 
                        'style': 'width: 100px; text-align: center;'}),
                }

        def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self.fields['servicio'].queryset = ServiciosMatBiblio.objects.filter(cod_servicio__range=(310, 313))

                # Hacer que los campos varones y total sean obligatorios
                self.fields['varones'].required = True
                self.fields['total'].required = True

        def clean(self):
                cleaned_data = super().clean()

                # Obtener los valores de 'varones' y 'total' para validar
                varones = cleaned_data.get('varones')
                total = cleaned_data.get('total')

                # Validar que el total no sea menor que varones
                if varones is not None and total is not None and total < varones:
                        self.add_error('total', 'El Total no puede ser menor que Varones.')

                return cleaned_data

# Formulario para ServicioPrestamo
class ServicioPrestamoForm(forms.ModelForm):
        class Meta:
                model = ServicioPrestamo
                fields = '__all__'
                widgets = {
                'cueanexo': forms.TextInput(attrs={'class': 'form-control','max_length':'9', 
                        'style': 'width: 100px; text-align: center;', 'readonly':'readonly'}),
                'mes': forms.TextInput(attrs={'class': 'form-control',
                        'style': 'width: 100px; text-align: center;', 'readonly':'readonly'}),
                'anio': forms.NumberInput(attrs={'class': 'form-control','max_length':'4', 
                        'style': 'width: 100px; text-align: center;', 'readonly':'readonly'}),
                'servicio': forms.Select(attrs={'class': 'form-control'}),
                'turnos': forms.Select(attrs={'class': 'form-control'}),
                'instalacion': forms.Select(attrs={'class': 'form-control'}),
                'total': forms.NumberInput(attrs={'class': 'form-control','max_length':'3',
                        'style': 'width: 100px; text-align: center;' }),
                }
        
        def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self.fields['servicio'].queryset = ServiciosMatBiblio.objects.filter(cod_servicio__range=(410,415))

                self.fields['total'].required = True
        

# Formulario para InformePedagogico
class InformePedagogicoForm(forms.ModelForm):
        class Meta:
                model = InformePedagogico
                fields = '__all__'
                widgets = {
                'cueanexo': forms.TextInput(attrs={'class': 'form-control', 
                        'style': 'width: 100px; text-align: center;', 'readonly': 'readonly'}),
                'mes': forms.TextInput(attrs={'class': 'form-control', 
                        'style': 'width: 100px; text-align: center;', 'readonly': 'readonly'}),
                'anio': forms.NumberInput(attrs={'class': 'form-control', 
                        'style': 'width: 100px; text-align: center;', 'readonly': 'readonly'}),
                'servicio': forms.Select(attrs={'class': 'form-control'}),
                'varones': forms.NumberInput(attrs={'class': 'form-control', 
                        'style': 'width: 100px; text-align: center;'}),
                'total': forms.NumberInput(attrs={'class': 'form-control', 
                        'style': 'width: 100px; text-align: center;'}),
                }
        
        def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self.fields['servicio'].queryset = ServiciosMatBiblio.objects.filter(cod_servicio__range=(510, 528))

                # Hacer que los campos varones y total sean obligatorios
                self.fields['varones'].required = True
                self.fields['total'].required = True

        def clean(self):
                cleaned_data = super().clean()

                # Obtener los valores de 'varones' y 'total' para validar
                varones = cleaned_data.get('varones')
                total = cleaned_data.get('total')

                # Validar que el total no sea menor que varones
                if varones is not None and total is not None and total < varones:
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
                'varones': forms.NumberInput(attrs={'class': 'form-control',
                        'style': 'width: 100px; text-align: center;'}),
                'total': forms.NumberInput(attrs={'class': 'form-control',
                        'style': 'width: 100px; text-align: center;'}),
                }

        def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)

                # Hacer que los campos varones y total sean obligatorios
                self.fields['varones'].required = True
                self.fields['total'].required = True

        def clean(self):
                cleaned_data = super().clean()

                # Obtener los valores de 'varones' y 'total' para validar
                varones = cleaned_data.get('varones')
                total = cleaned_data.get('total')

                # Validar que el total no sea menor que varones
                if varones is not None and total is not None and total < varones:
                        self.add_error('total', 'El Total no puede ser menor que Varones.')

                return cleaned_data

# Formulario para InstitucionesPrestaServicios
class InstitucionesPrestaServiciosForm(forms.ModelForm):
        class Meta:
                model = InstitucionesPrestaServicios
                fields = '__all__'
                widgets = {
                'cueanexo': forms.TextInput(attrs={'class': 'form-control', 
                        'style': 'width: 100px; text-align: center;', 'readonly': 'readonly'}),
                'mes': forms.TextInput(attrs={'class': 'form-control', 
                        'style': 'width: 100px; text-align: center;', 'readonly': 'readonly'}),
                'anio': forms.NumberInput(attrs={'class': 'form-control', 
                        'style': 'width: 100px; text-align: center;', 'readonly': 'readonly'}),
                'escuela': forms.TextInput(attrs={'class': 'form-control'}),
                'matricula': forms.NumberInput(attrs={'class': 'form-control', 
                        'style': 'width: 100px; text-align: center;'}),
                'docentes': forms.NumberInput(attrs={'class': 'form-control', 
                        'style': 'width: 100px; text-align: center;'}),
                'matricdisc': forms.NumberInput(attrs={'class': 'form-control', 
                        'style': 'width: 100px; text-align: center;'}),
                'etnia': forms.NumberInput(attrs={'class': 'form-control', 
                        'style': 'width: 100px; text-align: center;'}),
                }

        def clean(self):
                cleaned_data = super().clean()

                # Obtener los valores de matrícula, matricdisc y etnia
                matricula = cleaned_data.get('matricula')
                matricdisc = cleaned_data.get('matricdisc')
                etnia = cleaned_data.get('etnia')

                # Validar que los valores no sean mayores que matrícula
                if matricula is not None:
                        if matricdisc is not None and matricdisc > matricula:
                                self.add_error('matricdisc', 'La matrícula de discapacidad no puede ser mayor que la matrícula total.')
                
                if etnia is not None and etnia > matricula:
                        self.add_error('etnia', 'La matrícula de etnia no puede ser mayor que la matrícula total.')

                if matricdisc is not None and etnia is not None and (matricdisc + etnia > matricula):
                        self.add_error('matricdisc', 'La suma de discapacidad y etnia no puede superar la matrícula total.')
                        self.add_error('etnia', 'La suma de discapacidad y etnia no puede superar la matrícula total.')

                return cleaned_data


# Formulario para ProcesosTecnicos
class ProcesosTecnicosForm(forms.ModelForm):
        class Meta:
                model = ProcesosTecnicos
                fields = '__all__'
                widgets = {
                'cueanexo': forms.TextInput(attrs={'class': 'form-control','max_length':'9', 
                        'style': 'width: 100px; text-align: center;', 'readonly':'readonly'}),
                'mes': forms.TextInput(attrs={'class': 'form-control',
                        'style': 'width: 100px; text-align: center;', 'readonly':'readonly'}),
                'anio': forms.NumberInput(attrs={'class': 'form-control','max_length':'4', 
                        'style': 'width: 100px; text-align: center;', 'readonly':'readonly'}),
                'material': forms.Select(attrs={'class': 'form-control'}),
                'procesos': forms.Select(attrs={'class': 'form-control'}),
                'total': forms.NumberInput(attrs={'class': 'form-control','max_length':'3',
                        'style': 'width: 100px; text-align: center;' }),
                }
        
        def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                             
                self.fields['total'].required = True


# Formulario para Aguapey
class AguapeyForm(forms.ModelForm):
        class Meta:
                model = Aguapey
                fields = '__all__'
                widgets = {
                'cueanexo': forms.TextInput(attrs={'class': 'form-control', 
                        'style': 'width: 100px; text-align: center;', 'readonly': 'readonly'}),
                'mes': forms.TextInput(attrs={'class': 'form-control', 
                        'style': 'width: 100px; text-align: center;', 'readonly': 'readonly'}),
                'anio': forms.NumberInput(attrs={'class': 'form-control', 
                        'style': 'width: 100px; text-align: center;', 'readonly': 'readonly'}),
                'total_mes': forms.NumberInput(attrs={'class': 'form-control', 
                        'style': 'width: 100px; text-align: center;'}),
                'total_base': forms.NumberInput(attrs={'class': 'form-control', 
                        'style': 'width: 100px; text-align: center;'}),
                'total_usuarios': forms.NumberInput(attrs={'class': 'form-control',
                        'style': 'width: 100px; text-align: center;'}),
                'observaciones': forms.Textarea(attrs={'class': 'form-control',
                        'style': 'width: 100%; height: 100px;'}),
                }

        def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)

                # Hacer que los campos total_mes y total_base sean obligatorios
                self.fields['total_mes'].required = True
                self.fields['total_base'].required = True
                
                
        def clean(self):
                cleaned_data = super().clean()

                # Obtener los valores de total_mes y total_base
                total_mes = cleaned_data.get('total_mes')
                total_base = cleaned_data.get('total_base')

                # Validar que total_mes no sea mayor que total_base
                if total_mes is not None and total_base is not None and total_mes > total_base:
                        self.add_error('total_mes', 'El total del mes no puede ser mayor que el total base.')

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
                'cueanexo': forms.TextInput(attrs={'class': 'form-control','max_length':'9', 
                        'style': 'width: 100px; text-align: center;', 'readonly':'readonly'}),
                'mes': forms.TextInput(attrs={'class': 'form-control', 'readonly':'readonly'}),
                'anio': forms.NumberInput(attrs={'class': 'form-control', 'max_length':'4', 
                        'style': 'width: 100px; text-align: center;', 'readonly':'readonly'}),
                'destino': forms.Select(attrs={'class': 'form-control'}),
                'descripcion': forms.Textarea(attrs={'class': 'form-control', 'style': 'width: 100%; height: 100px;'}),
                }
                

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
            'f_nac': forms.DateInput(attrs={'type': 'date'}),
            'f_ingreso': forms.DateInput(attrs={'type': 'date'}),
            'f_hasta': forms.DateInput(attrs={'type': 'date'}),
            'f_desde_lic': forms.DateInput(attrs={'type': 'date'}),
            'f_hasta_lic': forms.DateInput(attrs={'type': 'date'}),
        }

    def clean_n_doc(self):
        n_doc = self.cleaned_data.get('n_doc', '')
        if not n_doc.isdigit():
            raise forms.ValidationError("Debe contener solo números.")
        if len(n_doc) < 7:
            raise forms.ValidationError("Debe tener al menos 7 dígitos.")
        return n_doc

    def clean_apellidos(self):
        apellidos = self.cleaned_data.get('apellidos', '')
        return apellidos.upper()

    def clean_nombres(self):
        nombres = self.cleaned_data.get('nombres', '')
        return nombres.upper()

    def clean(self):
        cleaned_data = super().clean()
        licencia = cleaned_data.get('licencia_permiso')
        f_desde = cleaned_data.get('f_desde_lic')
        f_hasta = cleaned_data.get('f_hasta_lic')

        if licencia:
            if not f_desde:
                self.add_error('f_desde_lic', "Debe completar esta fecha.")
            if not f_hasta:
                self.add_error('f_hasta_lic', "Debe completar esta fecha.")
            if f_desde and f_hasta and f_desde > f_hasta:
                self.add_error('f_desde_lic', "La fecha desde no puede ser mayor que la fecha hasta.")
                self.add_error('f_hasta_lic', "La fecha hasta no puede ser menor que la fecha desde.")
        elif f_desde or f_hasta:
            self.add_error('licencia_permiso', "Debe seleccionar un tipo de licencia si indica fechas.")

        return cleaned_data
