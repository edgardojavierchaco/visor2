from django.db import models
from django.forms import model_to_dict
from django.db.models import Sum

# Definir las áreas (Lengua, Matemáticas)
class Area(models.Model):
    nombre = models.CharField(max_length=100)
    
    class Meta:
        verbose_name='Area'
        verbose_name_plural='Areas'
        db_table='Areas'

    def __str__(self):
        return self.nombre
    
    def toJSON(self):
        item = model_to_dict(self)
        item['nombre'] = self.nombre
        return item


# Definir las categorías dentro de cada área (Genérico, Contenido, Puntuación, Tildación, Ortrografía, Mayúsculas)
class Categoria(models.Model):
    nombre = models.CharField(max_length=100)
    area = models.ForeignKey(Area, related_name='categorias', on_delete=models.CASCADE)
    
    class Meta:
        verbose_name='Categoria'
        verbose_name_plural='Categorias'
        db_table='Categorias'

    def __str__(self):
        return f'{self.nombre} ({self.area.nombre})'
    
    def toJSON(self):
        item = model_to_dict(self)
        item['nombre'] = self.nombre
        item['area'] = self.area
        return item

# Definir las preguntas, asociadas a una categoría y un área
class Pregunta(models.Model):
    texto = models.CharField(max_length=500)
    categorias = models.ManyToManyField(Categoria, related_name='preguntas')  
    area = models.ForeignKey(Area, related_name='preguntas', on_delete=models.CASCADE)
    
    class Meta:
        verbose_name='Pregunta'
        verbose_name_plural='Preguntas'
        db_table='Preguntas'

    def __str__(self):
        return self.texto
    
    def toJSON(self):
        item = model_to_dict(self, exclude=['categorias'])  # Excluye categorías porque es M2M
        item['nombre'] = self.texto
        item['categoria'] = [c.nombre for c in self.categorias.all()]  # Lista de nombres de categorías
        item['area'] = self.area.nombre  
        return item

# Definir los tipos de opción (Opción Única y Opción Múltiple)
class TipoOpcion(models.Model):
    nombre = models.CharField(max_length=50, choices=[('UNICA', 'Opción Única'), ('MULTIPLE', 'Opción Múltiple')])

    class Meta:
        verbose_name='Tipo Opcion'
        verbose_name_plural='Tipos Opciones'
        db_table='Tipo_Opcion'

    def __str__(self):
        return self.nombre


# Definir las opciones de las preguntas
class Opcion(models.Model):
    texto = models.CharField(max_length=200)
    pregunta = models.ForeignKey(Pregunta, related_name='opciones', on_delete=models.CASCADE)
    categoria = models.ForeignKey(Categoria, related_name='opciones', on_delete=models.CASCADE)  
    es_correcta = models.BooleanField(default=False)
    tipo = models.ForeignKey(TipoOpcion, related_name='opciones', on_delete=models.CASCADE)
    puntaje = models.DecimalField(max_digits=4, decimal_places=2, verbose_name='Puntaje')

    class Meta:
        verbose_name = 'Opción'
        verbose_name_plural = 'Opciones'
        db_table = 'Opcion'
        
    def __str__(self):
        return f"{self.texto} (Categoría: {self.categoria.nombre})"

    def toJSON(self):
        item = model_to_dict(self, exclude=['pregunta'])  
        item['categoria'] = self.categoria.nombre  
        item['tipo'] = self.tipo.nombre
        item['puntaje'] = str(self.puntaje) 
        return item

class AlumnosSecundaria(models.Model):
    dni = models.CharField(max_length=8, verbose_name='DNI')  
    apellidos = models.CharField(max_length=255, verbose_name='Apellidos')
    nombres = models.CharField(max_length=255, verbose_name='Nombres')
    cueanexo = models.CharField(max_length=9, verbose_name='Cueanexo') 
    
    class Meta:
        verbose_name = "Alumno_Secundaria"
        verbose_name_plural = "Alumnos_Secundaria"
        db_table = "Alumno_Secundaria"

    def __str__(self):
        return f'{self.dni} {self.apellidos} {self.nombres}'

# ExamenSecundaria para almacenar los exámenes
class ExamenSecundaria(models.Model):
    dni_alumno = models.CharField(max_length=8, verbose_name='DNI')  
    apellido = models.CharField(max_length=255, verbose_name='Apellidos')
    nombres = models.CharField(max_length=255, verbose_name='Nombres')
    cueanexo = models.CharField(max_length=9, verbose_name='Cueanexo') 
    area = models.ForeignKey(Area, related_name='examenes', on_delete=models.CASCADE, verbose_name='Area')
    puntaje_total = models.DecimalField(max_digits=6, decimal_places=2, default=0, verbose_name='Puntaje Total')

    class Meta:
        verbose_name = "Examen_secundaria"
        verbose_name_plural = "Examenes_secundaria"
        db_table = "Examen_secundaria"

    def __str__(self):
        return f"Examen de {self.dni_alumno} - {self.area.nombre}: Total = {self.puntaje_total}"

    def calcular_puntaje_total(self):
        total = self.respuestas.aggregate(Sum('puntaje'))['puntaje__sum'] or 0
        self.puntaje_total = total
        self.save()

# Respuesta de los exámenes
class Respuesta(models.Model):
    examen = models.ForeignKey(ExamenSecundaria, related_name='respuestas', on_delete=models.CASCADE)
    pregunta = models.ForeignKey(Pregunta, related_name='respuestas', on_delete=models.CASCADE)
    opciones = models.ManyToManyField(Opcion, related_name='respuestas')  
    puntaje = models.DecimalField(max_digits=6, decimal_places=2, default=0)

    class Meta:
        verbose_name = "Respuesta"
        verbose_name_plural = "Respuestas"
        db_table = "Respuesta"

    def __str__(self):
        return f"Respuesta a: {self.pregunta.texto}"

    def calcular_puntaje(self):
        """Calcula el puntaje de la respuesta según el tipo de pregunta."""
        opciones_seleccionadas = self.opciones.all()
        
        if not opciones_seleccionadas.exists():
            self.puntaje = 0
        else:
            # Obtener el tipo de la pregunta a partir de las opciones seleccionadas
            tipo_pregunta = opciones_seleccionadas.first().tipo.nombre  # 'UNICA' o 'MULTIPLE'

            if tipo_pregunta == 'Opción Única':  # Radio button - opción única
                # Si es opción única, tomamos el puntaje de la única opción seleccionada
                self.puntaje = opciones_seleccionadas.first().puntaje
            elif tipo_pregunta == 'Opción Múltiple':  # Checkbox - opción múltiple
                # Si es opción múltiple, sumamos el puntaje de todas las opciones seleccionadas
                self.puntaje = sum(op.puntaje for op in opciones_seleccionadas)
            else:
                self.puntaje = 0

        self.save()
        self.examen.calcular_puntaje_total()  # Calcula el puntaje total del examen después de cada respuesta


class CategoriasEvaluacion(models.Model):
    cod_categ=models.IntegerField(verbose_name='Codigo')
    descripcion=models.CharField(verbose_name='Descripción')
    puntaje=models.DecimalField(max_digits=4, decimal_places=2, verbose_name='Puntaje')
    
    class Meta:
        verbose_name='Categoria_Evaluacion'
        verbose_name_plural='Categorias Evaluacion'
        db_table='Categoria_Evaluacion'
        
    def __str__(self):
        return self.descripcion
    

class ExamenAlumnoCueanexoL(models.Model):
    dni_alumno=models.CharField(max_length=8, verbose_name='DNI')
    apellidos=models.CharField(max_length=255, verbose_name='Apellidos')
    nombres=models.CharField(max_length=255, verbose_name='Nombres')
    cueanexo=models.CharField(max_length=9, verbose_name='Cueanexo')
    preg_1=models.CharField(max_length=50, verbose_name='Preg_1')
    v_1=models.DecimalField(max_digits=4, decimal_places=2, default=0.00, verbose_name='V_1')
    preg_2=models.CharField(max_length=50, verbose_name='Preg_2')
    v_2=models.DecimalField(max_digits=4, decimal_places=2, default=0.00, verbose_name='V_2') 
    preg_3=models.CharField(max_length=50, verbose_name='Preg_3')
    v_3=models.DecimalField(max_digits=4, decimal_places=2, default=0.00, verbose_name='V_3')
    preg_4=models.CharField(max_length=50, verbose_name='Preg_4')
    v_4=models.DecimalField(max_digits=4, decimal_places=2, default=0.00, verbose_name='V_4')
    preg_5=models.CharField(max_length=50, verbose_name='Preg_5')
    v_5=models.DecimalField(max_digits=4, decimal_places=2, default=0.00, verbose_name='V_5')
    
    class Meta:
        verbose_name='Examen_Alumno_Cueanexo'
        verbose_name_plural='Examenes_Alumnos_Cueanexo'
        db_table='Examen_Alumno_Cueanexo'
        
    def __str__(self):
        return f'{self.dni_alumno} - {self.cueanexo}'
    
    