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
    escala_vel=models.CharField(max_length=150, blank=False, name='escala_vel')
    puntaje_vel=models.DecimalField(max_digits=5, decimal_places=2, validators=[MinValueValidator(0.00), MaxValueValidator(100.00)], name='puntaje_vel')
    nivel_vel=models.ForeignKey(RegNivelDesmp, on_delete=models.CASCADE, name='nivel_vel')
    
    def __str__(self):
        return f"{self.escala_vel}"
    
class RegPrecision(models.Model):
    escala_prec=models.CharField(max_length=150, blank=False, name='escala_prec')
    puntaje_prec=models.DecimalField(max_digits=5, decimal_places=2, validators=[MinValueValidator(0.00), MaxValueValidator(100.00)], name='puntaje_prec')
    nivel_prec=models.ForeignKey(RegNivelDesmp, on_delete=models.CASCADE, name='nivel_prec')
    
    def __str__(self):
        return f"{self.escala_prec}"
    
class RegProsodia(models.Model):
    escala_pros=models.CharField(max_length=150, blank=False, name='escala_pros')
    puntaje_pros=models.DecimalField(max_digits=5, decimal_places=2, validators=[MinValueValidator(0.00), MaxValueValidator(100.00)], name='puntaje_pros')
    nivel_pros=models.ForeignKey(RegNivelDesmp, on_delete=models.CASCADE, name='nivel_pros')

    def __str__(self):
        return f"{self.escala_pros}"
    
class RegComprension(models.Model):
    escala_comp=models.CharField(max_length=150, blank=False, name='escala_comp')
    puntaje_comp=models.DecimalField(max_digits=5, decimal_places=2, validators=[MinValueValidator(0.00), MaxValueValidator(100.00)], name='puntaje_comp')
    nivel_comp=models.ForeignKey(RegNivelDesmp, on_delete=models.CASCADE, name='nivel_comp')
    
    def __str__(self):
        return f"{self.escala_comp}"

class RegOpLectura(models.Model):
    asistencia=models.BooleanField(default=False, name='asistencia')
    cueanexo=models.CharField(max_length=9, blank=False, null=False, name='cueanexo')
    grado=models.CharField(max_length=25, blank=False, null=False,name='grado')
    seccion=models.CharField(max_length=15, blank=False, null=False,name='seccion')
    dni=models.CharField(max_length=8, blank=False, null=False,name='dni')
    nombres=models.CharField(max_length=150, blank=False, null=False,name='nombres')
    apellidos=models.CharField(max_length=150, blank=False, null=False,name='apellidos')
    velocidad=models.ForeignKey(RegVelocidad, on_delete=models.CASCADE, name='velocidad')    
    puntaje_velocidad=models.DecimalField(max_digits=5, decimal_places=2, validators=[MinValueValidator(0.00), MaxValueValidator(100.00)], blank=True, null=True, name='puntaje_velocidad')
    nivel_velocidad=models.CharField(blank=True, null=True, name='nivel_velocidad')
    precision=models.ForeignKey(RegPrecision, on_delete=models.CASCADE, name='precision')    
    puntaje_precision=models.DecimalField(max_digits=5, decimal_places=2, validators=[MinValueValidator(0.00), MaxValueValidator(100.00)], blank=True, null=True, name='puntaje_precision')
    nivel_precision=models.CharField(blank=True, null=True, name='nivel_precision')
    prosodia=models.ForeignKey(RegProsodia, on_delete=models.CASCADE, name='prosodia')  
    puntaje_prosodia=models.DecimalField(max_digits=5, decimal_places=2, validators=[MinValueValidator(0.00), MaxValueValidator(100.00)], blank=True, null=True, name='puntaje_prosodia')
    nivel_prosodia=models.CharField(blank=True, null=True, name='nivel_prosodia')  
    comprension=models.ForeignKey(RegComprension, on_delete=models.CASCADE, name='comprension')  
    puntaje_comprension=models.DecimalField(max_digits=5, decimal_places=2, validators=[MinValueValidator(0.00), MaxValueValidator(100.00)], blank=True, null=True, name='puntaje_comprension')
    nivel_comprension=models.CharField(blank=True, null=True, name='nivel_comprension')  
    anio=models.IntegerField(max_length=4, default=2024, name='año')
    mes=models.CharField(max_length=10, default='mayo', name='mes')
    dni_docente=models.CharField(max_length=8,name='dni_docente')
    
        
    class Meta:
        verbose_name='Registro_Op_Lectura'
        verbose_name_plural='Registros_Op_Lecturas'
        ordering=['cueanexo','dni']
    
    def __str__(self):
        return f"{self.cueanexo} - {self.dni} : {self.apellidos}, {self.nombres}"
    
    def save(self, *args, **kwargs):
        if self.velocidad:
            self.puntaje_velocidad = self.velocidad.puntaje_vel
            self.nivel_velocidad = self.velocidad.nivel_vel
        
        if self.precision:
            self.puntaje_precision=self.precision.puntaje_prec
            self.nivel_precision=self.precision.nivel_prec
        
        if self.prosodia:
            self.puntaje_prosodia=self.prosodia.puntaje_pros
            self.nivel_prosodia=self.prosodia.nivel_pros
        
        if self.comprension:
            self.puntaje_comprension=self.comprension.puntaje_comp
            self.nivel_comprension=self.comprension.nivel_comp
        super().save(*args, **kwargs)      

    
class sit_rev(models.Model):
    situarev=models.CharField(max_length=50, blank=False)
    
    def __str__(self):
        return self.situarev

class grado(models.Model):
    nomgrado=models.CharField(max_length=50, blank=False)
    
    def __str__(self):
        return self.nomgrado
    
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

class oplecturaabril(models.Model):
    reg = models.CharField(max_length=25, blank=False, null=False, name='reg') 
    cueanexo = models.CharField(max_length=9, blank=False, null=False, name='cueanexo')
    escuela = models.CharField(max_length=255, blank=False, null=False, name='escuela')
    ambito = models.CharField(max_length=100, blank=False, null=False, name='ambito')
    sector = models.CharField(max_length=100, blank=False, null=False, name='sector')
    apellidos = models.CharField(max_length=255, blank=False, null=False, name='apellidos')
    nombres = models.CharField(max_length=255, blank=False, null=False, name='nombres')
    dni=models.CharField(max_length=8, blank=False,null=False, name='dni')
    puntaje=models.DecimalField(max_digits=5, decimal_places=2, name='puntaje')
    desempeno=models.CharField(max_length=100, blank=False, null=False, name='desempeño')
    
    def __str__(self):
        return self.cueanexo
    

    
    
        
                    

