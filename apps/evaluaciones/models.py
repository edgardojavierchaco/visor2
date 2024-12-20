from django.db import models
from django.core.exceptions import ValidationError

# Modelo Alumno
class Alumno(models.Model):
    apellido = models.CharField(max_length=255)
    nombre = models.CharField(max_length=255)
    dni = models.CharField(max_length=9)
    
    def __str__(self):
        return f"{self.nombre} {self.apellido} - {self.dni}"

# Modelo Evaluacion
class Evaluacion(models.Model):
    materia_choices = [
        ('Lengua', 'Lengua'),
        ('Matematicas', 'Matematicas'),
    ]
    materia = models.CharField(max_length=20, choices=materia_choices)
    
    def __str__(self):
        return f"Evaluación de {self.materia}"

# Modelo Pregunta
class Pregunta(models.Model):
    OPCION_UNICA = 'unica'
    OPCION_MULTIPLE = 'multiple'
    TEXTO_CLASIFICAR = 'texto_clasificar'
    
    TIPO_PREGUNTA = [
        (OPCION_UNICA, 'Opción Única'),
        (OPCION_MULTIPLE, 'Opción Múltiple'),
        (TEXTO_CLASIFICAR, 'Texto Clasificar'),
        
    ]
    evaluacion = models.ForeignKey(Evaluacion, on_delete=models.CASCADE, related_name='preguntas')
    texto = models.TextField()
    puntaje = models.PositiveIntegerField()
    tipo = models.CharField(max_length=20, choices=TIPO_PREGUNTA)
    respuesta_correcta = models.TextField(blank=True, null=True)
    texto_base = models.TextField(blank=True, null=True) 

    def clean(self):
        # Validación personalizada para asegurar que respuesta_correcta no sea obligatorio en opción múltiple
        if self.tipo == self.OPCION_UNICA and not self.respuesta_correcta:
            raise ValidationError("Respuesta correcta es obligatoria para preguntas de opción única.")
        if self.tipo == self.OPCION_MULTIPLE and self.respuesta_correcta:
            raise ValidationError("Las respuestas correctas deben definirse en las opciones de respuesta para preguntas de opción múltiple.")
        if self.tipo == self.TEXTO_CLASIFICAR and not self.texto_base:
            raise ValidationError("El texto base es obligatorio para preguntas de tipo Texto Clasificar.")

    def __str__(self):
        return self.texto

# Modelo OpcionRespuesta
class OpcionRespuesta(models.Model):
    pregunta = models.ForeignKey(Pregunta, on_delete=models.CASCADE, related_name='opciones')
    opcion_texto = models.CharField(max_length=255)
    correcta = models.BooleanField(default=False)
    
    def __str__(self):
        return self.opcion_texto

# Modelo EvaluacionAlumno
class EvaluacionAlumno(models.Model):
    alumno = models.ForeignKey(Alumno, on_delete=models.CASCADE, related_name='evaluaciones')
    evaluacion = models.ForeignKey('Evaluacion', on_delete=models.CASCADE)
    puntaje_lengua = models.IntegerField(default=0)
    puntaje_matematica = models.IntegerField(default=0)
    puntaje_total = models.IntegerField(default=0)

    def calcular_puntaje(self):
        """Método para calcular el puntaje total y puntajes por materia"""
        if self.evaluacion.materia == 'Lengua':
            self.puntaje_lengua = self.puntaje_total
        elif self.evaluacion.materia == 'Matematicas':
            self.puntaje_matematica = self.puntaje_total

        self.puntaje_total = self.puntaje_lengua + self.puntaje_matematica
        self.save()

    def __str__(self):
        return f"Evaluación de {self.alumno.nombre} para {self.evaluacion.materia}"
