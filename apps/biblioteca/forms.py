from django import forms
from django.core.validators import MinValueValidator
from .models import (
    ServiciosMatBiblio, MaterialBibliografico, ServicioReferencia,
    ServicioReferenciaVirtual, ServicioPrestamo, InformePedagogico,
    AsistenciaUsuarios, InstitucionesPrestaServicios, ProcesosTecnicos, Aguapey
)

# Formulario para MaterialBibliografico
class MaterialBibliograficoForm(forms.ModelForm):    
        
    class Meta:
        model = MaterialBibliografico
        fields = '__all__'
        widgets = {
            'cueanexo': forms.TextInput(attrs={'class': 'form-control'}),
            'mes': forms.Select(attrs={'class': 'form-control'}),
            'anio': forms.NumberInput(attrs={'class': 'form-control'}),
            'servicio': forms.Select(attrs={'class': 'form-control'}),
            'turnos': forms.Select(attrs={'class': 'form-control'}),
            't_material': forms.Select(attrs={'class': 'form-control'}),
            'cantidad': forms.NumberInput(attrs={'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['servicio'].queryset = ServiciosMatBiblio.objects.filter(cod_servicio__lt=210)

# Formulario para ServicioReferencia
class ServicioReferenciaForm(forms.ModelForm):
    class Meta:
        model = ServicioReferencia
        fields = '__all__'
        widgets = {
            'cueanexo': forms.TextInput(attrs={'class': 'form-control'}),
            'mes': forms.Select(attrs={'class': 'form-control'}),
            'anio': forms.NumberInput(attrs={'class': 'form-control'}),
            'servicio': forms.Select(attrs={'class': 'form-control'}),
            'turnos': forms.Select(attrs={'class': 'form-control'}),
            'varones': forms.NumberInput(attrs={'class': 'form-control'}),
            'total': forms.NumberInput(attrs={'class': 'form-control'}),
        }
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['servicio'].queryset = ServiciosMatBiblio.objects.filter(cod_servicio=2)
        

# Formulario para ServicioReferenciaVirtual
class ServicioReferenciaVirtualForm(forms.ModelForm):
    class Meta:
        model = ServicioReferenciaVirtual
        fields = '__all__'
        widgets = {
            'cueanexo': forms.TextInput(attrs={'class': 'form-control'}),
            'mes': forms.Select(attrs={'class': 'form-control'}),
            'anio': forms.NumberInput(attrs={'class': 'form-control'}),
            'servicio': forms.Select(attrs={'class': 'form-control'}),
            'turnos': forms.Select(attrs={'class': 'form-control'}),
            'varones': forms.NumberInput(attrs={'class': 'form-control'}),
            'total': forms.NumberInput(attrs={'class': 'form-control'}),
        }
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['servicio'].queryset = ServiciosMatBiblio.objects.filter(cod_servicio=3)


# Formulario para ServicioPrestamo
class ServicioPrestamoForm(forms.ModelForm):
    class Meta:
        model = ServicioPrestamo
        fields = '__all__'
        widgets = {
            'cueanexo': forms.TextInput(attrs={'class': 'form-control'}),
            'mes': forms.Select(attrs={'class': 'form-control'}),
            'anio': forms.NumberInput(attrs={'class': 'form-control'}),
            'servicio': forms.Select(attrs={'class': 'form-control'}),
            'turnos': forms.Select(attrs={'class': 'form-control'}),
            'instalacion': forms.Select(attrs={'class': 'form-control'}),
            'total': forms.NumberInput(attrs={'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['servicio'].queryset = ServiciosMatBiblio.objects.filter(cod_servicio=4)


# Formulario para InformePedagogico
class InformePedagogicoForm(forms.ModelForm):
    class Meta:
        model = InformePedagogico
        fields = '__all__'
        widgets = {
            'cueanexo': forms.TextInput(attrs={'class': 'form-control'}),
            'mes': forms.Select(attrs={'class': 'form-control'}),
            'anio': forms.NumberInput(attrs={'class': 'form-control'}),
            'servicio': forms.Select(attrs={'class': 'form-control'}),
            'varones': forms.NumberInput(attrs={'class': 'form-control'}),
            'total': forms.NumberInput(attrs={'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['servicio'].queryset = ServiciosMatBiblio.objects.filter(cod_servicio=5)


# Formulario para AsistenciaUsuarios
class AsistenciaUsuariosForm(forms.ModelForm):
    class Meta:
        model = AsistenciaUsuarios
        fields = '__all__'
        widgets = {
            'cueanexo': forms.TextInput(attrs={'class': 'form-control'}),
            'mes': forms.Select(attrs={'class': 'form-control'}),
            'anio': forms.NumberInput(attrs={'class': 'form-control'}),
            'nivel': forms.Select(attrs={'class': 'form-control'}),
            'usuario': forms.Select(attrs={'class': 'form-control'}),
            'varones': forms.NumberInput(attrs={'class': 'form-control'}),
            'total': forms.NumberInput(attrs={'class': 'form-control'}),
        }

# Formulario para InstitucionesPrestaServicios
class InstitucionesPrestaServiciosForm(forms.ModelForm):
    class Meta:
        model = InstitucionesPrestaServicios
        fields = '__all__'
        widgets = {
            'cueanexo': forms.TextInput(attrs={'class': 'form-control'}),
            'mes': forms.Select(attrs={'class': 'form-control'}),
            'anio': forms.NumberInput(attrs={'class': 'form-control'}),
            'escuela': forms.TextInput(attrs={'class': 'form-control'}),
            'matricula': forms.NumberInput(attrs={'class': 'form-control'}),
            'docentes': forms.NumberInput(attrs={'class': 'form-control'}),
            'matricdisc': forms.NumberInput(attrs={'class': 'form-control'}),
            'etnia': forms.NumberInput(attrs={'class': 'form-control'}),
        }

# Formulario para ProcesosTecnicos
class ProcesosTecnicosForm(forms.ModelForm):
    class Meta:
        model = ProcesosTecnicos
        fields = '__all__'
        widgets = {
            'cueanexo': forms.TextInput(attrs={'class': 'form-control'}),
            'mes': forms.Select(attrs={'class': 'form-control'}),
            'anio': forms.NumberInput(attrs={'class': 'form-control'}),
            'material': forms.Select(attrs={'class': 'form-control'}),
            'procesos': forms.Select(attrs={'class': 'form-control'}),
            'total': forms.NumberInput(attrs={'class': 'form-control'}),
        }


# Formulario para Aguapey
class AguapeyForm(forms.ModelForm):
    class Meta:
        model = Aguapey
        fields = '__all__'
        widgets = {
            'cueanexo': forms.TextInput(attrs={'class': 'form-control'}),
            'mes': forms.Select(attrs={'class': 'form-control'}),
            'anio': forms.NumberInput(attrs={'class': 'form-control'}),
            'total_mes': forms.NumberInput(attrs={'class': 'form-control'}),
            'total_base': forms.NumberInput(attrs={'class': 'form-control'}),
        }

