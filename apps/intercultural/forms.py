from django import forms
from .models import Alumnos_Bilingue, Nivel_curso

class Alumno_BilingueForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Filtrar cursos por nivel seleccionado
        if 'nivel' in self.data:
            nivel_seleccionado = self.data.get('nivel')
            self.fields['curso'].queryset = Nivel_curso.objects.filter(nivel=nivel_seleccionado)
        elif self.instance and self.instance.nivel:  # Si ya hay una instancia (edición)
            nivel_seleccionado = self.instance.nivel
            self.fields['curso'].queryset = Nivel_curso.objects.filter(nivel=nivel_seleccionado)
        
        self.fields['cueanexo'].widget.attrs['autofocus'] = True
        
    class Meta:
        model = Alumnos_Bilingue
        fields = '__all__'
        widgets = {
            'cueanexo': forms.TextInput(
                attrs={
                    'class': 'form-control select2',
                    'placeholder': 'Ingrese Cueanexo',
                }
            ),            
            'nivel': forms.Select(
                attrs={
                    'class': 'form-control select2',
                    'placeholder': 'Seleccione Nivel',
                }
            ),
            'curso': forms.Select(
                attrs={
                    'class': 'form-control select2',
                    'placeholder': 'Seleccione Curso',
                }
            ),
            'seccion': forms.Select(
                attrs={
                    'class': 'form-control select2',
                    'placeholder': 'Seleccione Sección',
                }
            ),
            'lengua': forms.Select(
                attrs={
                    'class': 'form-control select2',
                    'placeholder': 'Seleccione Lengua',
                }
            ),
            'varones': forms.NumberInput(                
                attrs={
                    'class': 'form-control',
                    'placeholder': 'Ingrese cantidad de varones',
                    'max_length':'4',
                    'style': 'width: 100px; text-align: center;'                    
                }
            ),
            'mujeres': forms.NumberInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'Ingrese cantidad de mujeres',
                    'max_length':'3',
                    'style': 'width: 100px; text-align: center;' 
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
