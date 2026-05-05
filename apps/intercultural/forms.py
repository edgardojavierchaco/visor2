# forms.py
from django import forms
from .models import Alumnos_Bilingue, Nivel_curso


class Alumno_BilingueForm(forms.ModelForm):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # filtro cursos dinámico
        if 'nivel' in self.data:
            nivel = self.data.get('nivel')
            self.fields['curso'].queryset = Nivel_curso.objects.filter(nivel=nivel)

        elif self.instance and self.instance.nivel:
            self.fields['curso'].queryset = Nivel_curso.objects.filter(
                nivel=self.instance.nivel
            )

        self.fields['cueanexo'].widget.attrs['readonly'] = True

    class Meta:
        model = Alumnos_Bilingue
        fields = '__all__'
        widgets = {
            'cueanexo': forms.TextInput(attrs={
                'class': 'form-control',
                'readonly': True,
            }),
            'nivel': forms.Select(attrs={'class': 'form-control select2'}),
            'curso': forms.Select(attrs={'class': 'form-control select2'}),
            'seccion': forms.Select(attrs={'class': 'form-control select2'}),
            'lengua': forms.Select(attrs={'class': 'form-control select2'}),
            'varones': forms.NumberInput(attrs={
                'class': 'form-control',
                'style': 'width:100px;text-align:center;'
            }),
            'mujeres': forms.NumberInput(attrs={
                'class': 'form-control',
                'style': 'width:100px;text-align:center;'
            }),
        }
    
    

class Vista_Alumno_BilingueForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)        
        
    class Meta:
        model = Alumnos_Bilingue
        fields = '__all__'
        widgets = {
            'cueanexo': forms.TextInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'Ingrese Cueanexo',
                }
            ),            
            'nom_est': forms.TextInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'Seleccione Nivel',
                }
            ),
            'lengua': forms.TextInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'Seleccione Curso',
                }
            ),
            'varones': forms.TextInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'Seleccione Sección',
                }
            ),
            'mujeres': forms.TextInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'Seleccione Lengua',
                }
            ),
            'region_loc': forms.TextInput(                
                attrs={
                    'class': 'form-control',
                    'placeholder': 'Ingrese cantidad de varones',                                     
                }
            ),
            'localidad': forms.TextInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'Ingrese cantidad de mujeres',                    
                }
            ),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['cueanexo'].widget.attrs['readonly'] = True

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
