from django import forms
from apps.evaluaciones_educativas.models import *



class GradoViewForm(forms.Form):
	grado= forms.ChoiceField(label='SELECCIONE UN GRADO', required=False)

class SeccionViewForm(forms.Form):
	seccion= forms.ChoiceField(label='secciones', required=False)

	
# class TurnoViewForm(forms.Form):
# 	turno= forms.ChoiceField(label='Turnos', required=False)

class AlumnoForm(forms.ModelForm):

	class Meta:
		model = Alumno
		fields = ['dni','nombre','apellido','comunidad_indigena' ,'discapacidad']
		#widget  para cambiar tipo de campo
		widgets = {
            'dni': forms.TextInput(attrs={
                'required': 'true',         
                'minlength': '8',
				'maxlength':'8',
                'placeholder': 'INGRESA EL DNI DEL ALUMNO',
				'pattern': '[0-9]*'
            }),
			'nombre': forms.TextInput(attrs={
                'required': 'true', 
                'placeholder': 'NOMBRE DEL ALUMNO EN MAYUSCULA',
				'pattern': '[A-ZÑÁÉÍÓÚ ]*'
			}),
			'apellido': forms.TextInput(attrs={
                'required': 'true', 
                'placeholder': 'APELLIDO DEL ALUMNO EN MAYUSCULA',
				'pattern': '[A-ZÑÁÉÍÓÚ ]*'
			})
			}
		#label para cambiar nombre de campo

class AsistenciaForm(forms.Form):
	asistencia= forms.BooleanField(label='ASISTENCIA', required=False,
        widget=forms.RadioSelect(
            choices=[
                (True,'✅ ASISTIO'), 
                (False, '❌ NO ASISTIO ')
            ]
        )
    )

class EvaluacionFluidezForm(forms.ModelForm):
	class Meta:
		model= EvaluacionFluidezLectora
		fields=['cantidad_palabras_leidas','pregunta_1','pregunta_2','pregunta_3','pregunta_4' ,'pregunta_5','pregunta_6']
		widgets = {
			'cantidad_palabras_leidas': forms.NumberInput(attrs={
			'min':'0',
			'placeholder':'INGRESA LA CANTIDAD DE PALABRAS LEIDAS'
			})}
		
	def __init__(self, *args, max_cantidad_palabra=None, **kwargs):
		super().__init__(*args, **kwargs)
		if max_cantidad_palabra is not None:
			# Establece el tope de validación en el nivel del formulario
			self.fields['cantidad_palabras_leidas'].max_value = max_cantidad_palabra 
			
			# **Importante:** Establece el atributo HTML 'max' para el frontend
			self.fields['cantidad_palabras_leidas'].widget.attrs['max'] = max_cantidad_palabra
			self.fields['cantidad_palabras_leidas'].widget.attrs['placeholder'] = f'Máx. {max_cantidad_palabra}'

class GradoForm(forms.ModelForm):
	class Meta:
		model = Grado
		fields=['nombre_grado','cueanexo']
		#ocultamos cueanexo
		widgets = {
			'cueanexo': forms.NumberInput(
				attrs={
					'readonly':'readonly'
				}
			),
			'nombre_grado': forms.TextInput(
				attrs={
					'readonly':'readonly'
				}
			),
			}
	#solucion para evitar no seleccionar un unique desde el form	


class SeccionForm(forms.ModelForm):
	class Meta:
		model = Seccion
		fields=['seccion','turno']
		
	
class BorrarRegistroAlumnoForm(forms.Form):
		borrar= forms.BooleanField(label='borrar',required=False,
        widget=forms.RadioSelect(
            choices=[
                (True,'Eliminar registro'), 
                (False, 'NO eliminar registro ')
            ]
        )
    )