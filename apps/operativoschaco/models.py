from django.db import models
from decimal import Decimal

class AlumnosSecundaria(models.Model):
    dni = models.CharField(max_length=8, verbose_name='DNI')  
    apellidos = models.CharField(max_length=255, verbose_name='Apellidos')
    nombres = models.CharField(max_length=255, verbose_name='Nombres')
    cueanexo = models.CharField(max_length=9, verbose_name='Cueanexo') 
    anio=models.CharField(max_length=25, verbose_name='Año')
    division=models.CharField(max_length=5, verbose_name='División')
    region=models.CharField(max_length=25, verbose_name='Regional')

    class Meta:
        verbose_name = "Alumno Secundaria"
        verbose_name_plural = "Alumnos Secundaria"
        db_table = "Alumno_Secundaria"

    def __str__(self):
        return f'{self.dni} {self.apellidos} {self.nombres}'   

    

class Categoria(models.Model):
    nombre = models.CharField(max_length=255, verbose_name='Nombre de la Categoría')
    
    class Meta:
        verbose_name = "Categoría"
        verbose_name_plural = "Categorías"
        db_table = "Categoria"

    def __str__(self):
        return self.nombre
    
    
class Opcion(models.Model):
    descripcion = models.CharField(max_length=255, verbose_name='Descripción')
    puntaje = models.DecimalField(max_digits=4, decimal_places=2, verbose_name='Puntaje')
    categoria = models.ForeignKey(Categoria, on_delete=models.CASCADE, null=True, blank=True, related_name='opciones')

    class Meta:
        verbose_name = "Opción"
        verbose_name_plural = "Opciones"
        db_table = "Opcion"

    def __str__(self):
        return f'{self.descripcion} - {self.puntaje} puntos'
    


class Pregunta(models.Model):
    descripcion = models.CharField(max_length=255, verbose_name='Descripción')
    puntaje_maximo = models.DecimalField(max_digits=4, decimal_places=2, verbose_name='Puntaje Máximo')
    categorias = models.ManyToManyField(Categoria, blank=True, related_name='preguntas')  # Relación opcional

    # Relación con las opciones
    opciones = models.ManyToManyField(Opcion, related_name='preguntas', verbose_name='Opciones')

    class Meta:
        verbose_name = "Pregunta"
        verbose_name_plural = "Preguntas"
        db_table = "Pregunta"

    def __str__(self):
        return self.descripcion


class ExamenAlumnoCueanexoL(models.Model):
    alumno = models.ForeignKey(AlumnosSecundaria, on_delete=models.CASCADE)
    fecha_examen = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Examen Alumno"
        verbose_name_plural = "Exámenes Alumnos"
        db_table = "Examen_Alumno_Cueanexo"

    def __str__(self):
        return f'{self.alumno} - {self.fecha_examen}'


class Respuesta(models.Model):
    examen = models.ForeignKey(ExamenAlumnoCueanexoL, on_delete=models.CASCADE)
    pregunta = models.ForeignKey(Pregunta, on_delete=models.CASCADE)
    
    # Guardamos las respuestas como un conjunto de opciones seleccionadas
    opciones_seleccionadas = models.JSONField(default=list, verbose_name='Opciones Seleccionadas')

    class Meta:
        verbose_name = "Respuesta"
        verbose_name_plural = "Respuestas"
        db_table = "Respuesta"

    def __str__(self):
        return f'{self.examen} - {self.pregunta}'
    
    def obtener_puntajes(self):
        return [opcion['puntaje'] for opcion in self.opciones_seleccionadas]


class PreguntaM(models.Model):
    descripcion = models.CharField(max_length=255, verbose_name='Descripción')
    puntaje_maximo = models.DecimalField(max_digits=4, decimal_places=2, verbose_name='Puntaje Máximo')
    categorias = models.ManyToManyField(Categoria, blank=True, related_name='preguntasM')  # Relación opcional

    # Relación con las opciones
    opciones = models.ManyToManyField(Opcion, related_name='preguntasM', verbose_name='Opciones')

    class Meta:
        verbose_name = "Pregunta_Matematica"
        verbose_name_plural = "Preguntas_Matematicas"
        db_table = "Pregunta_Matematica"

    def __str__(self):
        return self.descripcion


class ExamenAlumnoCueanexoM(models.Model):
    alumno = models.ForeignKey(AlumnosSecundaria, on_delete=models.CASCADE)
    fecha_examen = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Examen Alumno Matematica"
        verbose_name_plural = "Exámenes Alumnos Matematicas"
        db_table = "Examen_Alumno_Cueanexo_M"

    def __str__(self):
        return f'{self.alumno} - {self.fecha_examen}'
    

class RespuestaM(models.Model):
    examen = models.ForeignKey(ExamenAlumnoCueanexoM, on_delete=models.CASCADE)
    pregunta = models.ForeignKey(PreguntaM, on_delete=models.CASCADE)
    
    # Guardamos las respuestas como un conjunto de opciones seleccionadas
    opciones_seleccionadas = models.JSONField(default=list, verbose_name='Opciones Seleccionadas')

    class Meta:
        verbose_name = "Respuesta Matematica"
        verbose_name_plural = "Respuestas Matematicas"
        db_table = "Respuesta_Matematica"

    def __str__(self):
        return f'{self.examen} - {self.pregunta}'
    
    def obtener_puntajes(self):
        return [opcion['puntaje'] for opcion in self.opciones_seleccionadas]
    
    
class CierreCargaL(models.Model):
    usuario = models.CharField(max_length=9)
    fecha_cierre = models.DateTimeField(auto_now_add=True)
    total_registros = models.PositiveIntegerField()

    def __str__(self):
        return f'Cierre de {self.usuario.username} - {self.fecha_cierre.date()}'


class CierreCargaM(models.Model):
    usuario = models.CharField(max_length=9)
    fecha_cierre = models.DateTimeField(auto_now_add=True)
    total_registros = models.PositiveIntegerField()

    def __str__(self):
        return f'Cierre de {self.usuario.username} - {self.fecha_cierre.date()}'