from django.db import models
from django.forms import model_to_dict
from django.core.exceptions import ValidationError
from django.utils.dateparse import parse_date
from django.core.validators import MinValueValidator, MaxValueValidator
import re

class EscuelasBilingues(models.Model):
    cueanexo=models.CharField(max_length=9,verbose_name='Cueanexo')
    nom_est=models.CharField(max_length=255, verbose_name='Escuela')
    acronimo=models.CharField(max_length=50, verbose_name='Acronimo')
    oferta=models.CharField(max_length=255, verbose_name='Oferta')
    ambito=models.CharField(max_length=255, verbose_name='Ambito')
    sector=models.CharField(max_length=255, verbose_name='Sector')
    region_loc=models.CharField(max_length=50, verbose_name='Region')
    localidad=models.CharField(max_length=255, verbose_name='Localidad')
    departamento=models.CharField(max_length=255, verbose_name='Departamento')
    
    class Meta:
        managed=False
        verbose_name = 'Escuela_Bilingue'
        verbose_name_plural='Escuelas_Builingues'
        db_table= 'v_escuelas_bilingues'    
    
    def __str__(self):
        return f"{self.cueanexo} {self.nom_est} {self.oferta}"

    def toJSON(self):
        item = model_to_dict(self)
        item['cueanexo'] = self.cueanexo
        item['nom_est'] = self.nom_est
        item['acronimo'] = self.acronimo
        item['oferta'] = self.oferta 
        item['ambito'] = self.ambito
        item['sector'] = self.sector
        item['region_loc'] = self.region_loc
        item['localidad'] = self.localidad
        item['departamento'] = self.departamento
        return item
        

class Nivel_curso(models.Model):
    nivel=models.CharField(max_length=255, verbose_name='Nivel')
    curso=models.CharField(max_length=255, verbose_name='Curso')
    
    class Meta:        
        verbose_name = 'Nivel_Curso'
        verbose_name_plural='Niveles_Cursos'
        db_table= 'nivel_curso'    
    
    def __str__(self):
        return self.curso

    def toJSON(self):
        item = model_to_dict(self)
        item['nivel'] = self.nivel
        item['curso'] = self.curso        
        return item

SECCIONES_CHOICES = [(chr(i), chr(i)) for i in range(ord('A'), ord('Z') + 1)]
SECCIONES_CHOICES.insert(0, ('Única', 'Única'))
SECCIONES_CHOICES.insert(1, ('Múltiple', 'Múltiple'))

LENGUAS_CHOICES = [
    ('QOM', 'QOM'),
    ('MOQOIT', 'MOQOIT'),
    ('WICHI', 'WICHI'),
]

NIVELES_CHOICES = [    
    ('INICIAL', 'INICIAL'),    
    ('INICIAL - ESPECIAL', 'INICIAL - ESPECIAL'),
    ('PRIMARIO', 'PRIMARIO'),
    ('PRIMARIO - ADULTO', 'PRIMARIO - ADULTO'),  
    ('PRIMARIO - ESPECIAL', 'PRIMARIO - ESPECIAL'),  
    ('SECUNDARIO', 'SECUNDARIO'),
    ('SECUNDARIO - ADULTO', 'SECUNDARIO - ADULTO'),
    ('SUPERIOR', 'SUPERIOR'),
    ('EDUCACION TEMPRANA - ESPECIAL', 'EDUCACION TEMPRANA - ESPECIAL'),
]

class Alumnos_Bilingue(models.Model):
    cueanexo=models.CharField(max_length=9, verbose_name='Cueanexo')  
    nivel=models.CharField(max_length=50,choices=NIVELES_CHOICES, verbose_name='Nivel')
    curso=models.ForeignKey(Nivel_curso,on_delete=models.CASCADE, verbose_name='Curso',related_name='alumnos_curso')
    seccion=models.CharField(max_length=10, choices=SECCIONES_CHOICES, verbose_name="Sección")
    lengua=models.CharField(max_length=10, choices=LENGUAS_CHOICES, verbose_name="Pueblo Originario")
    varones=models.IntegerField(verbose_name='Varones', validators=[MinValueValidator(0), MaxValueValidator(999)])
    mujeres=models.IntegerField(verbose_name='Mujeres', validators=[MinValueValidator(0), MaxValueValidator(999)])
    
    class Meta:        
        verbose_name = 'Alumno_Bilingue'
        verbose_name_plural='Alumnos_Bilingues'
        db_table= 'alumno_bilingue'
    
    def __str__(self):
        return f"{self.cueanexo} - ({self.nivel} {self.curso} {self.seccion})"
    
    def toJSON(self):
        item = model_to_dict(self)
        item['cueanexo'] = self.cueanexo        
        item['nivel'] = self.nivel
        item['curso'] = self.curso.curso
        item['seccion'] = self.seccion
        item['lengua'] = self.lengua   
        item['varones'] = self.varones
        item['mujeres'] = self.mujeres  
        return item

class VistaAlumnosBilingue(models.Model):
    id = models.AutoField(primary_key=True)
    cueanexo=models.CharField(max_length=9, verbose_name='Cueanexo')
    nom_est=models.CharField(max_length=255, verbose_name='Escuela')
    lengua=models.CharField(max_length=50, verbose_name='Lengua')
    varones=models.IntegerField(verbose_name='Varones')
    mujeres=models.IntegerField(verbose_name='Mujeres')
    region_loc=models.CharField(max_length=50, verbose_name='Regional')
    localidad=models.CharField(max_length=155, verbose_name='Localidad')
    
    class Meta:    
        managed=False    
        verbose_name = 'Vista_Alumno_Bilingue'
        verbose_name_plural='Vistas_Alumnos_Bilingues'
        db_table= 'v_alumnos_bilingue'
    
    def __str__(self):
        return f"{self.cueanexo} - ({self.nom_est})"
    
    def toJSON(self):
        item = model_to_dict(self)
        item['cueanexo'] = self.cueanexo        
        item['nom_est'] = self.nom_est
        item['lengua'] = self.lengua
        item['varones'] = self.varones
        item['mujeres'] = self.mujeres   
        item['region_loc'] = self.region_loc
        item['localidad'] = self.localidad  
        return item


class ExportarAlumnoBilingueConId(models.Model):
    id = models.IntegerField(primary_key=True)
    cueanexo = models.CharField(max_length=15)
    nom_est = models.CharField(max_length=255)
    sector = models.CharField(max_length=100)
    ambito = models.CharField(max_length=100)
    region_loc = models.CharField(max_length=100)
    localidad = models.CharField(max_length=100)
    departamento = models.CharField(max_length=100)
    nivel = models.CharField(max_length=50)
    curso = models.CharField(max_length=50)
    seccion = models.CharField(max_length=10)
    lengua = models.CharField(max_length=100)
    varones = models.IntegerField()
    mujeres = models.IntegerField()

    class Meta:
        managed = False  
        db_table = 'v_alumnos_bilingues_con_id'