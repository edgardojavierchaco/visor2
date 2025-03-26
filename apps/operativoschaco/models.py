from django.db import models
from django.forms import model_to_dict

GRADO_CHOICES = [
    (1, '1'),
    (2, '2'),
    (3, '3'),
    (4, '4'),
    (5, '5'),
    (6, '6'),
]

DIVISION_CHOICES = [(str(i), str(i)) for i in range(1, 22)]

TURNOS_CHOICES=[
    ('MAÑANA','MAÑANA'),
    ('TARDE','TARDE'),
    ('VESPERTINO','VESPERTINO'),
]

# Modelo para el alumno
class Alumno(models.Model):
    dni = models.CharField(max_length=8, unique=True)
    apellido = models.CharField(max_length=255, verbose_name='Apellidos')
    nombre = models.CharField(max_length=255, verbose_name='Nombres')
    grado=models.IntegerField(default=1, choices=GRADO_CHOICES, verbose_name='Año')
    division=models.CharField(max_length=2, choices=DIVISION_CHOICES, verbose_name='División')
    turno=models.CharField(max_length=25, choices=TURNOS_CHOICES, verbose_name='Turno')
    cueanexo = models.CharField(max_length=9, verbose_name='Cueanexo')
    
    class Meta:
        verbose_name='Alumno'
        verbose_name_plural='Alumnos'
        db_table='Alumnos'
        
    def __str__(self):
        return f"{self.dni} {self.apellido}, {self.nombre}"
    
    def toJSON(self):
        item=model_to_dict(self)
        item['dni']=self.dni
        item['apellido']=self.apellido
        item['nombre']=self.nombre
        item['grado']=self.grado
        item['division']=self.division
        item['turno']=self.turno
        item['cueanexo']=self.cueanexo
        return item


# Modelo para las categorías (contenido y normativa)
class Categoria(models.Model):
    nombre = models.CharField(max_length=255, verbose_name='Nombre')
    puntaje = models.DecimalField(max_digits=4, decimal_places=2, verbose_name='Puntaje')
    
    class Meta:
        verbose_name='Categoria'
        verbose_name_plural='Categorías'
        db_table='Categorias'

    def __str__(self):
        return self.nombre
    
    def toJSON(self):
        item=model_to_dict(self)
        item['nombre']=self.nombre
        item['puntaje']=self.puntaje
        return item


# Modelo para las subcategorías dentro de normativa y contenido
class Subcategoria(models.Model):
    categoria = models.ForeignKey(Categoria, related_name='subcategorias', on_delete=models.CASCADE, verbose_name='Categoria')
    nombre = models.CharField(max_length=255, verbose_name='Nombre')
    puntaje = models.DecimalField(max_digits=4, decimal_places=2, verbose_name='Puntaje')

    class Meta:
        verbose_name='Subcategoria'
        verbose_name_plural='Subcategorias'
        db_table='Subcategorias'
        
    def __str__(self):
        return self.nombre
    
    def toJSON(self):
        item=model_to_dict(self)
        item['categoria']=self.categoria
        item['nombre']=self.nombre
        item['puntaje']=self.puntaje
        return item


# Modelo para las preguntas del examen
class Pregunta(models.Model):
    texto = models.TextField(verbose_name='texto')
    tipo = models.CharField(max_length=20, choices=[('opcion_unica', 'Opción Única'), ('agrupada', 'Agrupada')], verbose_name='Tipo')
    categorias = models.ManyToManyField(Categoria, blank=True, verbose_name='Categorias')  # Para las preguntas agrupadas

    class Meta:
        verbose_name='Pregunta'
        verbose_name_plural='Preguntas'
        db_table='Preguntas'
        
    def __str__(self):
        return self.texto
    
    def toJSON(self):
        item=model_to_dict(self)
        item['texto']=self.texto
        item['tipo']=self.tipo
        item['categorias']=self.categorias
        return item
    
    
# Modelo para las opciones de las preguntas de opción única
class Opcion(models.Model):
    pregunta = models.ForeignKey(Pregunta, related_name='opciones', on_delete=models.CASCADE, verbose_name='Pregunta')
    texto = models.CharField(max_length=255, verbose_name='Texto')
    puntaje = models.DecimalField(max_digits=4, decimal_places=2, verbose_name='Puntaje')

    class Meta:
        verbose_name='Opcion'
        verbose_name_plural='Opciones'
        db_table='Opcion'
        
    def __str__(self):
        return self.texto
    
    def toJSON(self):
        item=model_to_dict(self)
        item['pregunta']=self.pregunta
        item['texto']=self.texto
        item['puntaje']=self.puntaje
        return item


# Modelo para las respuestas de los alumnos
class Respuesta(models.Model):
    dni_alumno=models.CharField(max_length=8, verbose_name='DNI')    
    alumno_apellido = models.CharField(max_length=255, verbose_name='Apellidos')
    alumno_nombre=models.CharField(max_length=255, verbose_name='Nombres')
    pregunta = models.ForeignKey(Pregunta, on_delete=models.CASCADE, verbose_name='Pregunta')
    opcion = models.ForeignKey(Opcion, null=True, blank=True, on_delete=models.CASCADE, verbose_name='Opciones')  # Solo para preguntas de opción única
    categoria = models.ForeignKey(Categoria, null=True, blank=True, on_delete=models.CASCADE, verbose_name='Categorías')  # Solo para preguntas agrupadas
    subcategorias = models.ManyToManyField(Subcategoria, blank=True, verbose_name='Subcategorías')  # Campo para seleccionar múltiples subcategorías
    puntaje_opcion = models.DecimalField(max_digits=4, decimal_places=2, verbose_name='Puntaje Opción Única', default=0)  # Puntaje para opción única
    puntaje_agrupada = models.DecimalField(max_digits=4, decimal_places=2, verbose_name='Puntaje Agrupada', default=0)  # Puntaje para agrupada
    
    class Meta:
        verbose_name='Respuesta'
        verbose_name_plural='Respuestas'
        db_table='Respuestas'

    def __str__(self):
        return f"Respuesta de {self.alumno_apellido}, {self.alumno_nombre} en {self.pregunta}"
    
    def toJSON(self):
        item=model_to_dict(self)
        item['dni_alumno']=self.dni_alumno
        item['alumno_apellido']=self.alumno_apellido
        item['alumno_nombre']=self.alumno_nombre
        item['pregunta']=self.pregunta
        item['opcion']=self.opcion
        item['categoria']=self.categoria
        item['subcategorias'] = [subcategoria.nombre for subcategoria in self.subcategorias.all()]  # Lista de nombres de subcategorías
        item['puntaje_opcion']=self.puntaje_opcion
        item['puntaje_agrupada']=self.puntaje_agrupada
        return item


# Modelo para el examen (puede ser para un examen específico o una instancia)
class Examen(models.Model):
    fecha = models.DateTimeField(auto_now_add=True)
    escuela = models.CharField(max_length=9, verbose_name='Cueanexo')

    class Meta:
        verbose_name='Examen'
        verbose_name_plural='Examenes'
        db_table='Examenes'
        
    def __str__(self):
        return f"Examen para {self.escuela} en {self.fecha}"
    
    def toJSON(self):
        item=model_to_dict(self)
        item['fecha']=self.fecha
        item['escuela']=self.escuela
        return item
    

class PreguntasporArea(models.Model):
    cod_area=models.IntegerField(verbose_name='Código Área')
    cod_pregunta=models.IntegerField(verbose_name='Código Pregunta')
    texto_pregunta = models.CharField(max_length=255, verbose_name='Texto de la Pregunta')
    
    class Meta:
        verbose_name='Pregunta_Area'
        verbose_name_plural='Preguntas_Areas'
        db_table='Preguntas_areas'

    def __str__(self):
        return self.texto_pregunta
    
    def toJSON(self):
        item=model_to_dict(self)
        item['cod_area']=self.cod_area
        item['cod_pregunta']=self.cod_pregunta
        item['texto_pregunta']=self.texto_pregunta
        return item

class OpcionesRespuestasAreas(models.Model):
    cod_arearesp=models.IntegerField(verbose_name='Código Área')
    cod_pregunta_resp=models.IntegerField(verbose_name='Código Pregunta')
    opciones=models.CharField(max_length=255, verbose_name='Opciones')
    puntaje=models.DecimalField(max_digits=4,decimal_places=2, verbose_name='Puntaje')
    tipo_opcion=models.CharField(max_length=50, default='unico',verbose_name='Tipo Opción')
    
    class Meta:
        verbose_name='Opcion_Respuesta'
        verbose_name_plural='Opciones_Respuestas'
        db_table='Opciones_Respuestas'
    
    def __str__(self):
        return f'{self.cod_arearesp} {self.cod_pregunta_resp} {self.opciones}'        
    
    def toJSON(self):
        item=model_to_dict(self)
        item['cod_area']=self.cod_arearesp
        item['cod_pregunta']=self.cod_pregunta_resp
        item['opciones']=self.opciones
        item['puntaje']=self.puntaje
        return item