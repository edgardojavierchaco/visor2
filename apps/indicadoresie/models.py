from tabnanny import verbose
from django.db import models
from django.forms import model_to_dict
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator

class SIESegimiento(models.Model):    
    agente=models.CharField(max_length=100, verbose_name='Agente')
    escuela=models.CharField(max_length=100, verbose_name='Escuela')
    cueanexo=models.CharField(max_length=9, verbose_name='Cueanexo')
    region=models.CharField(max_length=50, verbose_name='Regional')
    nivel=models.CharField(max_length=50, verbose_name='Nivel')
    sieant=models.IntegerField(verbose_name='Sie_anterior')
    sieact=models.IntegerField(verbose_name='Sie_actual')
    dni_agente=models.CharField(max_length=8, verbose_name='DNI')
    id = models.AutoField(primary_key=True)
    
    class Meta:
        managed=False
        verbose_name='sie_seguimiento'
        verbose_name_plural='sies_seguimientos'
        db_table='sie_seguimiento'
    
    def __str__(self):
        return f'{self.agente} - {self.cueanexo}{self.escuela}'
    
    def toJSON(self):
        item=model_to_dict(self)
        item['agente']=self.agente
        item['escuela']=self.escuela
        item['cueanexo']=self.cueanexo
        item['region']=self.region
        item['nivel']=self.nivel
        item['sieant']=self.sieant
        item['sieact']=self.sieact
        item['dni_agente']=self.dni_agente
        item['id']=self.id
        return item
    
    
class SeguimientoSIE2025(models.Model):    
    nivel = models.CharField(max_length=50, verbose_name='Nivel')
    region = models.CharField(max_length=50, verbose_name='Regional')
    agente = models.CharField(max_length=100, verbose_name='agente')
    localidad = models.CharField(max_length=100, verbose_name='localidad')
    cue = models.CharField(max_length=20, verbose_name='Cue')
    anexo = models.CharField(max_length=10, verbose_name='Anexo')
    grado = models.CharField(max_length=30, verbose_name='Grado')
    seccion = models.CharField(max_length=30, verbose_name='Sección')
    turno_nombre = models.CharField(max_length=50, verbose_name='Turno')
    ciclo_lectivo = models.CharField(max_length=10, verbose_name='Ciclo')
    estado_inscripcion = models.CharField(max_length=50, verbose_name='Estado')
    nro_documento = models.CharField(max_length=20, verbose_name='DNI')
    apellidos = models.CharField(max_length=100, verbose_name='Apellidos')
    nombres = models.CharField(max_length=50, verbose_name='Nombres')
    discapacidad = models.CharField(max_length=100, blank=True, null=True, verbose_name='Discapacidad')
    comunidad_aborigen = models.CharField(max_length=50, blank=True, null=True, verbose_name='Comunidad')
    id = models.AutoField(primary_key=True)
    
    class Meta:
        db_table = 'seguimiento_sie_2025'
        managed = False  
        verbose_name='seguimiento_sie'
        verbose_name_plural='seguimientos_sies'

    def __str__(self):
        return f"{self.apellidos}, {self.nombres} ({self.nro_documento})"   
    
    def toJSON(self):
        item=model_to_dict(self)
        item['nivel']=self.nivel
        item['region']=self.region
        item['agente']=self.agente
        item['localidad']=self.localidad
        item['cue']=self.cue
        item['anexo']=self.anexo
        item['grado']=self.grado
        item['seccion']=self.seccion
        item['turno_nombre']=self.turno_nombre
        item['ciclo_lectivo']=self.ciclo_lectivo
        item['estado_inscripcion']=self.estado_inscripcion
        item['nro_documento']=self.nro_documento
        item['apellidos']=self.apellidos
        item['nombres']=self.nombres
        item['discapacidad']=self.discapacidad
        item['comunidad_aborigen']=self.comunidad_aborigen
        item['id']=self.id 
        return item
        
    
    

