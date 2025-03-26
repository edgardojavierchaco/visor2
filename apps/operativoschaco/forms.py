from django import forms
from .models import Respuesta, Opcion, Categoria, Subcategoria, Alumno
from django.db.models import Q

class RespuestaForm(forms.ModelForm):
    class Meta:
        model = Respuesta
        fields = ['dni_alumno', 'alumno_apellido', 'alumno_nombre', 'pregunta', 'opcion', 'categoria', 'subcategorias', 'puntaje_opcion', 'puntaje_agrupada']
        widgets = {
            'subcategorias': forms.CheckboxSelectMultiple(),  # Para permitir seleccionar varias subcategorías
            'puntaje_opcion': forms.HiddenInput(),  # Ocultar el campo de puntaje de opción
            'puntaje_agrupada': forms.HiddenInput(),  # Ocultar el campo de puntaje agrupado
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Opciones para el campo 'opcion' pueden ser filtradas si es necesario (por ejemplo, si están relacionadas con la pregunta)
        self.fields['opcion'].queryset = Opcion.objects.all()

    # Lógica para autocompletar 'dni_alumno', 'alumno_apellido' y 'alumno_nombre' mediante AJAX
    def clean_dni_alumno(self):
        dni = self.cleaned_data.get('dni_alumno')
        if dni:
            # Obtener el username del usuario logueado
            username = self.initial.get('username', None)
            if username:
                # Filtrar alumnos por cueanexo igual al username del usuario logueado
                try:
                    alumno = Alumno.objects.get(dni=dni, cueanexo=username)
                    self.cleaned_data['alumno_apellido'] = alumno.apellido
                    self.cleaned_data['alumno_nombre'] = alumno.nombre
                except Alumno.DoesNotExist:
                    raise forms.ValidationError("El alumno con ese DNI no existe o no pertenece a su grupo.")
        return dni
