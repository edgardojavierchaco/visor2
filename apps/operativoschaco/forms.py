from django import forms
from .models import ExamenAlumnoCueanexoL, Pregunta, Respuesta, PreguntaM, RespuestaM

class ExamenForm(forms.Form):
    # Campos del alumno
    dni_alumno = forms.CharField(max_length=8, required=True, label='DNI Alumno')
    apellidos = forms.CharField(max_length=255, required=True, label='Apellidos')
    nombres = forms.CharField(max_length=255, required=True, label='Nombres')
    cueanexo = forms.CharField(max_length=9, required=True, label='Cueanexo')
    anio=forms.CharField(max_length=25, required=True, label='Año')
    division=forms.CharField(max_length=5, required=True, label='División')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.preguntas = Pregunta.objects.all()
        
        for pregunta in self.preguntas:
            opciones = pregunta.opciones.all()

            # Verificar si las opciones tienen categorías
            categorias_presentes = set(op.categoria for op in opciones if op.categoria)
            
            if categorias_presentes:
                # Crear desplegables separados para cada categoría
                for categoria in categorias_presentes:
                    opciones_categoria = opciones.filter(categoria=categoria)
                    
                    self.fields[f'preg_{pregunta.id}_cat_{categoria.id}'] = forms.ChoiceField(
                        choices=[(opcion.id, opcion.descripcion) for opcion in opciones_categoria],
                        widget=forms.Select,
                        label=f"{pregunta.descripcion} - {categoria.nombre}"
                    )
            else:
                # Si no hay categorías, un único desplegable para todas las opciones
                self.fields[f'preg_{pregunta.id}'] = forms.ChoiceField(
                    choices=[(opcion.id, opcion.descripcion) for opcion in opciones],
                    widget=forms.Select,
                    label=pregunta.descripcion
                )

    # Validación del formulario
    def clean(self):
        cleaned_data = super().clean()
        dni_alumno = cleaned_data.get("dni_alumno")
        apellidos = cleaned_data.get("apellidos")
        nombres = cleaned_data.get("nombres")
        cueanexo = cleaned_data.get("cueanexo")

        if not dni_alumno or not apellidos or not nombres or not cueanexo:
            raise forms.ValidationError("Todos los campos del alumno son requeridos")

        return cleaned_data


class ExamenMatematicaForm(forms.Form):
    # Campos del alumno
    dni_alumno = forms.CharField(max_length=8, required=True, label='DNI Alumno')
    apellidos = forms.CharField(max_length=255, required=True, label='Apellidos')
    nombres = forms.CharField(max_length=255, required=True, label='Nombres')
    cueanexo = forms.CharField(max_length=9, required=True, label='Cueanexo')
    anio=forms.CharField(max_length=25, required=True, label='Año')
    division=forms.CharField(max_length=5, required=True, label='División')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.preguntas = PreguntaM.objects.all()
        
        for pregunta in self.preguntas:
            opciones = pregunta.opciones.all()

            # Verificar si las opciones tienen categorías
            categorias_presentes = set(op.categoria for op in opciones if op.categoria)
            
            if categorias_presentes:
                # Crear desplegables separados para cada categoría
                for categoria in categorias_presentes:
                    opciones_categoria = opciones.filter(categoria=categoria)
                    
                    self.fields[f'preg_{pregunta.id}_cat_{categoria.id}'] = forms.ChoiceField(
                        choices=[(opcion.id, opcion.descripcion) for opcion in opciones_categoria],
                        widget=forms.Select,
                        label=f"{pregunta.descripcion} - {categoria.nombre}"
                    )
            else:
                # Si no hay categorías, un único desplegable para todas las opciones
                self.fields[f'preg_{pregunta.id}'] = forms.ChoiceField(
                    choices=[(opcion.id, opcion.descripcion) for opcion in opciones],
                    widget=forms.Select,
                    label=pregunta.descripcion
                )

    # Validación del formulario
    def clean(self):
        cleaned_data = super().clean()
        dni_alumno = cleaned_data.get("dni_alumno")
        apellidos = cleaned_data.get("apellidos")
        nombres = cleaned_data.get("nombres")
        cueanexo = cleaned_data.get("cueanexo")

        if not dni_alumno or not apellidos or not nombres or not cueanexo:
            raise forms.ValidationError("Todos los campos del alumno son requeridos")

        return cleaned_data