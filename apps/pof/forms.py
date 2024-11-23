import email
from django.forms import *
from .models import UnidadServicio, AsignacionPof, CargosHoras, Departamento, DepartamentoLocalidad

class UnidadServicioForm(ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Enfocar en el campo 'cue' al cargar el formulario
        self.fields['cue'].widget.attrs['autofocus'] = True
        
        # Si se ha seleccionado un departamento, carga las localidades correspondientes
        if 'departamento' in self.data:
            try:
                departamento_id = int(self.data.get('departamento'))
                self.fields['localidad'].queryset = DepartamentoLocalidad.objects.filter(departamento_id=departamento_id).order_by('denom_localidad')
            except (ValueError, TypeError):
                pass  # Manejo de errores si `departamento` no es válido
        else:
            self.fields['localidad'].queryset = DepartamentoLocalidad.objects.none()

        
    class Meta:
        model = UnidadServicio
        fields = '__all__'
        widgets = {
            'cue': TextInput(
                attrs={
                    'placeholder': 'Ingrese un Cue',
                }
            ),
            'anexo': TextInput(
                attrs={
                    'placeholder': 'Ingrese el anexo',
                }
            ),
            'cueanexo': TextInput(
                attrs={
                    'placeholder': 'Cueanexo',
                    'readonly': True, 
                }
            ),
            'nom_est': TextInput(
                attrs={
                    'placeholder': 'Ingrese el nombre de la escuela',
                }
            ),
            'ubicacion': TextInput(
                attrs={
                    'placeholder': 'Ingrese la ubicación',
                }
            ),
            'cui': TextInput(
                attrs={
                    'placeholder': 'Ingrese el CUI',
                }
            ),
            'nro': TextInput(
                attrs={
                    'placeholder': 'Número',
                }
            ),
            'cuof': TextInput(
                attrs={
                    'placeholder': 'Ingrese el CUOF',
                }
            ),
            'cuof_anexo': TextInput(
                attrs={
                    'placeholder': 'Ingrese el CUOF Anexo',
                }
            ),
            # Campos tipo ForeignKey con Select
            'nivel': Select(attrs={'class': 'form-control'}),
            'modalidad': Select(attrs={'class': 'form-control'}),
            'sector': Select(attrs={'class': 'form-control'}),
            'ambito': Select(attrs={'class': 'form-control'}),
            'zona': Select(attrs={'class': 'form-control'}),
            'categoria': Select(attrs={'class': 'form-control'}),
            'jornada': Select(attrs={'class': 'form-control'}),
            'region': Select(attrs={'class': 'form-control'}),
            'departamento': Select(attrs={'class': 'form-control'}),
            'localidad': Select(attrs={'class': 'form-control'}),
        }

    def save(self, commit=True):
        data = {}
        form = super()
        try:
            if self.is_valid():
                form.save()
            else:
                data['error'] = form.errors
        except Exception as e:
            data['error'] = str(e)
        return data


class CargosHorasForm(ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['nivel'].widget.attrs['autofocus'] = True  # Enfocar en el campo nivel

    class Meta:
        model = CargosHoras
        fields = '__all__'
        widgets = {
            'nivel': Select(
                attrs={
                    'class': 'form-control'
                }
            ),
            'ceic': NumberInput(
                attrs={
                    'placeholder': 'Ingrese el valor de CEIC',
                    'class': 'form-control'
                }
            ),
            'denom_cargoshoras': TextInput(
                attrs={
                    'placeholder': 'Ingrese la denominación de cargo/hora',
                    'class': 'form-control'
                }
            ),
            'estado': CheckboxInput(
                attrs={
                    'class': 'form-check-input'
                }
            ),
            'puntos': NumberInput(
                attrs={
                    'placeholder': 'Ingrese el valor de puntos',
                    'class': 'form-control'
                }
            ),
        }

    def save(self, commit=True):
        instance = super(CargosHorasForm, self).save(commit=False)
        if commit:
            instance.save()
        return instance


class AsignacionPofForm(ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        

    class Meta:
        model = AsignacionPof
        fields = '__all__'
        widgets = {
            'unidad': Select(attrs={
                'class': 'form-control select2',
                'style': 'width: 100%',
                'autofocus': True
            }),            
            'cant_cargos': TextInput(attrs={
                'readonly': True,
                'class': 'form-control',
            }),
            'cant_horas': TextInput(attrs={
                'readonly': True,
                'class': 'form-control',
            }),
        }