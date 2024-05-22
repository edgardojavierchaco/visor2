from tabnanny import verbose
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator, MaxLengthValidator, RegexValidator
from django.forms import ValidationError

# Validador personalizado para el campo cueanexo y dni
def validate_digits(value):
    if not value.isdigit():
        raise ValidationError('Éste campo solo puede contener dígitos.')
    
# Validador personalizado para el campo seccion
def validate_seccion(value):
    if not value.isupper():
        raise ValidationError('El campo sección sólo puede contener letras mayúsculas.')
    if any(char in value for char in '.,_?¿¡!'):
        raise ValidationError('El campo sección no puede contener puntos, comas o guiones bajos...')
    
class RegNivelDesmp(models.Model):
    tnivel=models.CharField(max_length=100, blank=False, name='tnivel')
    
    def __str__(self):
        return self.tnivel
    
class RegVelocidad(models.Model):
    escala_vel=models.CharField(max_length=15, blank=False, name='escala_vel')
    nivel_vel=models.ForeignKey(RegNivelDesmp, on_delete=models.CASCADE, name='nivel_vel')
    
    def __str__(self):
        return f"{self.escala_vel}-{self.nivel_vel}"
    
class RegPrecision(models.Model):
    escala_prec=models.CharField(max_length=15, blank=False, name='escala_prec')
    nivel_prec=models.ForeignKey(RegNivelDesmp, on_delete=models.CASCADE, name='nivel_prec')
    
    def __str__(self):
        return f"{self.escala_prec}-{self.nivel_prec}"
    
class RegProsodia(models.Model):
    escala_pros=models.CharField(max_length=15, blank=False, name='escala_pros')
    nivel_pros=models.ForeignKey(RegNivelDesmp, on_delete=models.CASCADE, name='nivel_pros')

    def __str__(self):
        return f"{self.escala_pros}-{self.nivel_pros}"
    
class RegComprension(models.Model):
    escala_comp=models.CharField(max_length=15, blank=False, name='escala_comp')
    nivel_comp=models.ForeignKey(RegNivelDesmp, on_delete=models.CASCADE, name='nivel_comp')
    
    def __str__(self):
        return f"{self.escala_comp}-{self.nivel_comp}"

class RegOpLectura(models.Model):
    asistencia=models.BooleanField(default=True, name='asistencia')
    cueanexo=models.CharField(max_length=9, blank=False, name='cueanexo')
    grado=models.CharField(max_length=25, blank=False, name='grado')
    seccion=models.CharField(max_length=15, blank=False, name='seccion')
    dni=models.CharField(max_length=8, blank=False, name='dni')
    nombres=models.CharField(max_length=150, blank=False, name='nombres')
    apellidos=models.CharField(max_length=150, blank=False, name='apellidos')
    velocidad=models.DecimalField(max_digits=5, decimal_places=2, validators=[MinValueValidator(0.00), MaxValueValidator(100.00)], name='velocidad')
    precision=models.DecimalField(max_digits=5, decimal_places=2, validators=[MinValueValidator(0.00), MaxValueValidator(100.00)], name='precision')
    prosodia=models.DecimalField(max_digits=5, decimal_places=2, validators=[MinValueValidator(0.00), MaxValueValidator(100.00)], name='prosodia')
    comprension=models.DecimalField(max_digits=5, decimal_places=2, validators=[MinValueValidator(0.00), MaxValueValidator(100.00)], name='comprension')
    promedio=models.DecimalField(max_digits=5, decimal_places=2, validators=[MinValueValidator(0.00), MaxValueValidator(100.00)], name='promedio')
    ndesempeno=models.CharField(max_length=18, blank=False, name='desempeño')
    anio=models.IntegerField(max_length=4, blank=False, name='año')
    mes=models.CharField(max_length=10, blank=False, name='mes')
    dni_docente=models.CharField(max_length=8, blank=False, name='dni_docente')
    
        
    class Meta:
        verbose_name='Registro_Op_Lectura'
        verbose_name_plural='Registros_Op_Lecturas'
        ordering=['cueanexo','dni']
    
    def __str__(self):
        return f"{self.cueanexo} - {self.dni} : {self.apellidos}, {self.nombres}"


class grado(models.Model):
    nomgrado=models.CharField(max_length=50, blank=False)
    
    def __str__(self):
        return self.nomgrado

class sit_rev(models.Model):
    situarev=models.CharField(max_length=50, blank=False)
    
    def __str__(self):
        return self.situarev


class DocenteGradoSeccion(models.Model):
    cueanexo=models.CharField(max_length=9, blank=False, validators=[MaxLengthValidator(9), RegexValidator(r'^\d+$', message='Este campo solo puede contener dígitos.')])
    nombre=models.CharField(max_length=255, blank=False)
    dni=models.CharField(max_length=8, blank=False, validators=[MaxLengthValidator(8), RegexValidator(r'^\d+$', message='Este campo solo puede contener dígitos.')])
    ngrado=models.ForeignKey(grado, on_delete=models.CASCADE)
    seccion=models.CharField(max_length=50, blank=False, validators=[validate_seccion])
    sitrev=models.ForeignKey(sit_rev, on_delete=models.CASCADE)
    activo=models.BooleanField(default=True)
    
    def __str__(self):
        return f"{self.nombre}-{self.dni}: {self.ngrado}-{self.seccion}"
    
    def clean(self):
        super().clean()
        # Convertir el campo sección a mayúsculas
        self.seccion = self.seccion.upper()

    
    
        
                    

