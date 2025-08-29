from django.core.validators import RegexValidator
from django.db import models
from django.utils import timezone

REGIONAL_CHOICES = [
    ('R.E. 1', 'R.E. 1'),
    ('R.E. 2', 'R.E. 2'),
    ('R.E. 3', 'R.E. 3'),
    ('R.E. 4-A', 'R.E. 4-A'),
    ('R.E. 4-B', 'R.E. 4-B'),
    ('R.E. 5', 'R.E. 5'),
    ('R.E. 6', 'R.E. 6'),
    ('R.E. 7', 'R.E. 7'),
    ('R.E. 8-A', 'R.E. 8-A'),
    ('R.E. 8-B', 'R.E. 8-B'),
    ('R.E. 9', 'R.E. 9'),
    ('R.E. 10-A', 'R.E. 10-A'),
    ('R.E. 10-B', 'R.E. 10-B'),
    ('R.E. 10-C', 'R.E. 10-C'),
    ('SUB. R.E. 1-A', 'SUB. R.E. 1-A'),
    ('SUB. R.E. 1-B', 'SUB. R.E. 1-B'),
    ('SUB. R.E. 2', 'SUB. R.E. 2'),
    ('SUB. R.E. 3', 'SUB. R.E. 3'),
    ('SUB. R.E. 5', 'SUB. R.E. 5'),
]

NIVEL_CHOICES = [
    ('Inicial', 'Inicial'),
    ('Primario', 'Primario'),
    ('Secundario', 'Secundario'),
    ('Adultos - Primario', 'Adultos - Primario'),
    ('Adultos - Secundario', 'Adultos - Secundario'),
    ('Especial', 'Especial'),
]

SGE_CHOICES = [
    ('USUARIOS', 'USUARIOS'),
    ('TITULACIONES', 'TITULACIONES'),
    ('SECCIONES', 'SECCIONES'),
    ('ASISTENCIA', 'ASISTENCIA'),
    ('CALIFICACIONES', 'CALIFICACIONES'),
]

SGE_ROLES = [
    ('DIRECTOR', 'DIRECTOR'),
    ('SECRETARIO', 'SECRETARIO'),
    ('MAESTRO/PROFESOR', 'MAESTRO/PROFESOR'),
    ('AUXILIAR DOCENTE', 'AUXILIAR DOCENTE'),
]

class Consulta(models.Model):
    cueanexo = models.CharField(
        max_length=9,
        validators=[
            RegexValidator(
                regex=r'^22\d{7}$',
                message='El CUEANEXO debe comenzar con 22 y tener 9 dígitos sin puntos ni guiones.',
                code='invalid_cueanexo'
            )
        ]
    )
    regional = models.CharField(max_length=25, choices=REGIONAL_CHOICES)
    nivel_modalidad = models.CharField(max_length=50, choices=NIVEL_CHOICES)
    sge_modulo = models.CharField(max_length=30, choices=SGE_CHOICES)
    sge_rol = models.CharField(max_length=20, choices=SGE_ROLES)
    apellido_nombre = models.CharField(
        max_length=100,
        validators=[
            RegexValidator(
                regex=r'^[A-Z\s]+$',
                message='Solo se permiten letras y espacios, sin puntos, comas ni otros caracteres.'
            )
        ]
    )
    email = models.EmailField()
    mensaje = models.TextField()
    fecha = models.DateTimeField(auto_now_add=True)
    estado=models.CharField(max_length=20, default='Pendiente')
    estado_usuario = models.CharField(max_length=150, null=True, blank=True)
    estado_fecha = models.DateTimeField(default=timezone.now, blank=True)
    

    def __str__(self):
        return f"{self.cueanexo}-{self.apellido_nombre} - {self.fecha.strftime('%d/%m/%Y %H:%M')}"

    class Meta:
        verbose_name = 'ConsultaSGE'
        verbose_name_plural = 'ConsultasSGE'
        db_table = 'consultas_sge'
