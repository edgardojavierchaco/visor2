from django import forms
from apps.evaluaciones_educativas.models import *



class GradoViewForm(forms.Form):
	grado= forms.ChoiceField(label='SELECCIONE UN GRADO', required=False, widget=forms.RadioSelect(
        ))

class SeccionViewForm(forms.Form):
	seccion= forms.ChoiceField(label='secciones', required=False)


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
			}),
			'comunidad_indigena': forms.Select(
				attrs={'required': 'true'}),
			'discapacidad': forms.Select(
				attrs={'required': 'true'})
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
			}),
			'pregunta_1': forms.Select(
				attrs={'required': 'true'}),
			'pregunta_2': forms.Select(
				attrs={'required': 'true'})
				,'pregunta_3': forms.Select(
				attrs={'required': 'true'}),
			'pregunta_4': forms.Select(
				attrs={'required': 'true'})
				,'pregunta_5': forms.Select(
				attrs={'required': 'true'}),
			'pregunta_6': forms.Select(
				attrs={'required': 'true'})
			}
		
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
		widgets = {
			'seccion': forms.Select(
				attrs={'required': 'true'}),
				'turno': forms.Select(
				attrs={'required': 'true'})
				}
	
	
class BorrarRegistroAlumnoForm(forms.Form):
		borrar= forms.BooleanField(label='borrar',required=False,
        widget=forms.RadioSelect(
            choices=[
                (True,'Eliminar registro'), 
                (False, 'NO eliminar registro ')
            ]
        )
    )
#----------------------VISUALIZACION---------------------
class DirectorForm(forms.Form):
		SECTORES = [
        ('estatal', 'Estatal'),
		('Gestión social/cooperativa','Gestión social/cooperativa'),
        ('privado', 'Privado'),
    	]
		AMBITOS = [
        ('Rural Aglomerado', 'Rural Aglomerado'),
        ('Rural Disperso', 'Rural Disperso'),
        ('Urbano', 'Urbano'),
    	]
    
		sector = forms.ChoiceField(
			choices=SECTORES, 
			label="Sector de Gestión",
			widget=forms.Select(attrs={'class': 'form-select'}) # Para estilos de CSS
		)
		ambito= forms.ChoiceField(
			choices=AMBITOS, 
			label="Ámbito",
			widget=forms.Select(attrs={'class': 'form-select'}) # Para estilos de CSS
		)

class DirectorNivelForm(DirectorForm):
		REGIONES = [
		('R.E. 7', 'R.E. 7'),
		('R.E. 5', 'R.E. 5'),
		('SUB. R.E. 3', 'SUB. R.E. 3'),
		('SUB. R.E. 5', 'SUB. R.E. 5'),
		('SUB. R.E. 1-A', 'SUB. R.E. 1-A'),
		('R.E. 8-B', 'R.E. 8-B'),
		('R.E. 2', 'R.E. 2'),
		('R.E. 3', 'R.E. 3'),
		('R.E. 10-B', 'R.E. 10-B'),
		('R.E. 10-C', 'R.E. 10-C'),
		('R.E. 9', 'R.E. 9'),
		('R.E. 1', 'R.E. 1'),
		('R.E. 4-A', 'R.E. 4-A'),
		('SUB. R.E. 1-B', 'SUB. R.E. 1-B'),
		('SUB. R.E. 2', 'SUB. R.E. 2'),
		('R.E. 8-A', 'R.E. 8-A'),
		('R.E. 6', 'R.E. 6'),
		('R.E. 10-A', 'R.E. 10-A'),
		('R.E. 4-B', 'R.E. 4-B'),
		]
		
		region = forms.ChoiceField(
			choices=REGIONES, 
			label="Región",
			widget=forms.Select(attrs={'class': 'form-select'}) # Para estilos de CSS
		)
	
class DirectorRegionalForm(DirectorForm):
	NIVELES_EDUCATIVOS = [
			('Rural Aglomerado', 'Rural Aglomerado'),
			('Rural Disperso', 'Rural Disperso'),
			('Urbano', 'Urbano'),
		]
	nivel_educativo= forms.ChoiceField(
			choices=NIVELES_EDUCATIVOS, 
			label="Nivel Educativo",
			widget=forms.Select(attrs={'class': 'form-select'}) # Para estilos de CSS
		)
class DirectorGeneralForm(DirectorNivelForm,DirectorRegionalForm):
	pass


class Grado_select_Form(forms.Form):
    GRADOS_CHOICES = [
        ('', '--- Seleccionar Grado ---'),  # Valor vacío para la opción neutra
        ('2do Año/Grado', '2do Año/Grado'),
        ('3er Año/Grado', '3er Año/Grado'),
    ]
    
    grado_seleccion = forms.ChoiceField(
        choices=GRADOS_CHOICES,
        label="Seleccione un Grado",
        required=True,
        widget=forms.Select()
    )
class SeccionTurnoForm(forms.Form):
    # Definimos el campo vacío inicialmente
    seleccion = forms.ModelChoiceField(
        queryset=Seccion.objects.none(), 
        label="Seleccione para procesar",
        required=True
    )

    def __init__(self, *args, **kwargs):
        # 1. Extraemos 'grados' de los argumentos (y lo quitamos para no romper el super)
        grados = kwargs.pop('grados', None)
        super().__init__(*args, **kwargs)
        
        # 2. Si recibimos grados, actualizamos el queryset del campo
        if grados:
            #print(grados)
            qs = Seccion.objects.filter(grado_id=grados).only('id', 'seccion', 'turno')
            self.fields['seleccion'].queryset = qs
            # Sobreescribimos la función de visualización sobre la marcha
            self.fields['seleccion'].label_from_instance = lambda obj: f"Sección: {obj.seccion} - Turno: {obj.turno}"
			# --- AQUÍ AGREGAMOS LA OPCIÓN EXTRA ---
			# Convertimos el queryset a una lista de opciones y le sumamos la nuestra
            choices = [('TODOS', '--- Todas las Secciones ---')] 

			# Sumamos las opciones que vienen de la base de datos
            choices.extend([
				(obj.id, self.fields['seleccion'].label_from_instance(obj)) 
				for obj in qs
			])

			# Le decimos al campo que use esta nueva lista mixta
            self.fields['seleccion'].choices = choices