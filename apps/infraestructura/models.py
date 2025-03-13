import os
import json
from django.db import models
from django.conf import settings
from django.forms import model_to_dict
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from numpy import blackman
from apps.cenpe.models import provincia_tipo
from django.contrib.gis.db import models as gis_models


MESES_CHOICES = [    
    ('ABRIL', 'ABRIL'),    
    ('JULIO', 'JULIO'),    
    ('NOVIEMBRE', 'NOVIEMBRE'),    
    ('DICIEMBRE', 'DICIEMBRE'),
]

DOMINIO_CHOICES=[
    ('PROPIO', 'PROPIO'),    
    ('LOCACION', 'LOCACION'),    
    ('COMODATO', 'COMODATO'),    
    ('CESION', 'CESION'),
    ('OTRO', 'OTRO'),
]

ESTADO_EDIFICIO=[
    ('BUENO','BUENO'),
    ('REGULAR','REGULAR'),
    ('MALO', 'MALO'),
]

# Datos Institucionales
class DatosEscuela(models.Model):
    cueanexo=models.CharField(max_length=9, verbose_name='Cueanexo')
    nom_est=models.CharField(max_length=255, verbose_name='Nom_Est')
    calle=models.CharField(max_length=255, verbose_name='Calle')
    nro=models.IntegerField(verbose_name='Nro')
    circ=models.CharField(max_length=5, verbose_name='Circ')
    mz=models.CharField(max_length=5, verbose_name='Mz')
    pc=models.CharField(max_length=5, verbose_name='Mz')
    departamentos=models.CharField(max_length=255, verbose_name='Departamento')
    localidades=models.CharField(max_length=255, verbose_name='Localidad')
    anio_edif=models.IntegerField(verbose_name='Inauguracion')
    patrimonio=models.BooleanField(default=False, verbose_name='Patrimonio')
    antiguedad=models.IntegerField(verbose_name='Antigüedad')
    dist_munic=models.DecimalField(max_digits=6,decimal_places=2, verbose_name='Distancia_Municipio')
    dist_tierra=models.DecimalField(max_digits=6,decimal_places=2, verbose_name='Distancia_Tierra')
    dist_pavim=models.DecimalField(max_digits=6,decimal_places=2, verbose_name='Distancia_Pavimento')
    
    class Meta:
        verbose_name='Dato_Escuela'
        verbose_name_plural='Datos_Escuelas'
        db_table='dato_escuela'
    
    def __str__(self):
        return f'{self.cueanexo} - {self.nom_est}'
    
    def toJSON(self):
        item = model_to_dict
        item=self.cueanexo
        item=self.nom_est
        item=self.calle
        item=self.nro
        item=self.circ
        item=self.mz
        item=self.pc
        item=self.departamentos
        item=self.localidades
        item=self.anio_edif
        item=self.patrimonio
        item=self.antiguedad
        item=self.dist_munic
        item=self.dist_tierra
        item=self.dist_pavim
        return item
    

# Datos Dominio Edificio Escolar
class DominioEscuela(models.Model):
    cueanexo=models.CharField(max_length=9, verbose_name='Cueanexo')
    mes=models.CharField(max_length=25, choices=MESES_CHOICES, verbose_name='Mes')
    anio=models.IntegerField(validators=[MinValueValidator(2025)], verbose_name='Año')
    dominio=models.CharField(max_length=50, choices=DOMINIO_CHOICES, verbose_name='Dominio')
    plan_const=models.CharField(max_length=255, verbose_name='Plan')
    ampliacion=models.IntegerField(verbose_name='Ampliación')
    plan_ampl=models.CharField(max_length=255, verbose_name='Plan_Ampliación')
    sup_terreno=models.DecimalField(max_digits=6,decimal_places=2, verbose_name='Sup_Terreno')
    sup_cub=models.DecimalField(max_digits=6,decimal_places=2, verbose_name='Sup_Cubierta')
    
    
    class Meta:
        verbose_name='Dominio_Escuela'
        verbose_name_plural='Dominios_Escuelas'
        db_table='dominio_escuela'
    
    def __str__(self):
        return f'{self.cueanexo} - {self.mes} {self.anio}'
    
    def toJSON(self):
        item = model_to_dict
        item=self.cueanexo
        item=self.mes
        item=self.anio
        item=self.dominio
        item=self.plan_const
        item=self.ampliacion
        item=self.plan_ampl
        item=self.sup_terreno
        item=self.sup_cub
        return item


# Espacios Pedagógicos
class EspaciosPedagogicos(models.Model):
    cueanexo=models.CharField(max_length=9, verbose_name='Cueanexo')
    mes=models.CharField(max_length=25, choices=MESES_CHOICES, verbose_name='Mes')
    anio=models.IntegerField(validators=[MinValueValidator(2025)], verbose_name='Año')
    aulas_comunes=models.IntegerField(verbose_name='Aulas_Comunes')
    aulas_aire=models.IntegerField(verbose_name='Aulas_Aire')
    sum=models.IntegerField(verbose_name='SUM')
    laboratorio=models.IntegerField(verbose_name='Laboratorio')
    playon_depo=models.IntegerField(verbose_name='Playon_Deportivo')

    class Meta:
        verbose_name='Espacio_Pedagogico'
        verbose_name_plural='Espacios_Pedagogicos'
        db_table='espacio_pedagogico'
    
    def __str__(self):
        return f'{self.cueanexo} - {self.mes} {self.anio}'
    
    def toJSON(self):
        item = model_to_dict
        item=self.cueanexo
        item=self.mes
        item=self.anio
        item=self.aulas_comunes
        item=self.aulas_aire
        item=self.sum
        item=self.laboratorio
        item=self.playon_depo        
        return item


# Sanitarios
class Sanitarios(models.Model):
    cueanexo=models.CharField(max_length=9, verbose_name='Cueanexo')
    mes=models.CharField(max_length=25, choices=MESES_CHOICES, verbose_name='Mes')
    anio=models.IntegerField(validators=[MinValueValidator(2025)], verbose_name='Año')
    bebederos=models.IntegerField(verbose_name='Bebederos')
    inodoros=models.IntegerField(verbose_name='Inodoros')
    lavatorios=models.IntegerField(verbose_name='Lavatorios')
    mingitorios=models.IntegerField(verbose_name='Mingitorios')
    bidet=models.IntegerField(verbose_name='Bidet')
    letrinas=models.IntegerField(verbose_name='Letrinas')

    class Meta:
        verbose_name='Sanitario'
        verbose_name_plural='Sanitarios'
        db_table='sanitarios'
    
    def __str__(self):
        return f'{self.cueanexo} - {self.mes} {self.anio}'
    
    def toJSON(self):
        item = model_to_dict
        item=self.cueanexo
        item=self.mes
        item=self.anio
        item=self.bebederos
        item=self.inodoros
        item=self.lavatorios
        item=self.mingitorios
        item=self.bidet
        item=self.letrinas        
        return item


# Accesibilidad
class Accesibilidad(models.Model):
    cueanexo=models.CharField(max_length=9, verbose_name='Cueanexo')
    mes=models.CharField(max_length=25, choices=MESES_CHOICES, verbose_name='Mes')
    anio=models.IntegerField(validators=[MinValueValidator(2025)], verbose_name='Año')
    sanitarios=models.IntegerField(verbose_name='Sanitarios')
    asensores=models.IntegerField(verbose_name='Asensores')
    montacargas=models.IntegerField(verbose_name='Montacargas')
    escaleras=models.IntegerField(verbose_name='Escaleras')
    rampas=models.IntegerField(verbose_name='Rampas')    

    class Meta:
        verbose_name='Accesibilidad'
        verbose_name_plural='Accesibilidades'
        db_table='accesibilidad'
    
    def __str__(self):
        return f'{self.cueanexo} - {self.mes} {self.anio}'
    
    def toJSON(self):
        item = model_to_dict
        item=self.cueanexo
        item=self.mes
        item=self.anio
        item=self.sanitarios
        item=self.asensores
        item=self.montacargas
        item=self.escaleras
        item=self.rampas    
        return item


# Seguridad
class Seguridad(models.Model):
    cueanexo=models.CharField(max_length=9, verbose_name='Cueanexo')
    mes=models.CharField(max_length=25, choices=MESES_CHOICES, verbose_name='Mes')
    anio=models.IntegerField(validators=[MinValueValidator(2025)], verbose_name='Año')
    alarma=models.BooleanField(default=False,verbose_name='Alarma')
    contraincendio=models.BooleanField(default=False,verbose_name='Contraincendio')
    rejas=models.BooleanField(default=False,verbose_name='Rejas')
    cerco=models.BooleanField(default=False,verbose_name='Escaleras')
    estado=models.CharField(max_length=25, choices=ESTADO_EDIFICIO, verbose_name='Rampas')    

    class Meta:
        verbose_name='Seguridad'
        verbose_name_plural='Seguridades'
        db_table='seguridad'
    
    def __str__(self):
        return f'{self.cueanexo} - {self.mes} {self.anio}'
    
    def toJSON(self):
        item = model_to_dict
        item=self.cueanexo
        item=self.mes
        item=self.anio
        item=self.alarma
        item=self.contraincendio
        item=self.rejas
        item=self.cerco
        item=self.estado    
        return item
    
    
# Departamentos del Chaco
class Departamento(models.Model):
    c_departamento = models.AutoField(primary_key=True)
    descripcion_dpto = models.CharField(max_length=255)
    
    class Meta:
        verbose_name='Departamento'
        verbose_name_plural='Departamentos'
        db_table='departamentos_chaco'
        
    
    def __str__(self):
        return self.descripcion_dpto
    
    def toJSON(self):
        item=model_to_dict
        item=self.c_departamento
        item=self.descripcion_dpto
        return item


class Localidad(models.Model):
    c_localidad = models.AutoField(primary_key=True)
    descripcion_loc = models.CharField(max_length=255)
    c_departamento = models.ForeignKey(Departamento, on_delete=models.CASCADE)
    c_provincia = models.ForeignKey(provincia_tipo, db_column='c_provincia', on_delete=models.CASCADE)
    
    class Meta:
        verbose_name='Localidad'
        verbose_name_plural='Localidades'
        db_table='localidades'
    
    def __str__(self):
        return f'{self.c_localidad} {self.descripcion_loc}'
    
    def toJSON(self):
        item=model_to_dict
        item=self.c_localidad
        item=self.descripcion_loc
        return item


class VCapaUnicaOfertasCuiCuof(models.Model):
    cueanexo = models.CharField(max_length=9, primary_key=True)
    geom = gis_models.GeometryField()
    long = models.FloatField()
    lat = models.FloatField()
    nom_est = models.CharField(max_length=255, null=True, blank=True)
    padron_cueanexo = models.CharField(max_length=9, null=True, blank=True)
    acronimo = models.TextField(null=True, blank=True)
    oferta = models.TextField(null=True, blank=True)
    etiqueta = models.TextField(null=True, blank=True)
    nro_est = models.IntegerField(null=True, blank=True)
    ambito = models.CharField(max_length=100, null=True, blank=True)
    sector = models.CharField(max_length=100, null=True, blank=True)
    region_loc = models.CharField(max_length=100, null=True, blank=True)
    ref_loc = models.CharField(max_length=100, null=True, blank=True)
    calle = models.CharField(max_length=255, null=True, blank=True)
    numero = models.CharField(max_length=50, null=True, blank=True)
    localidad = models.CharField(max_length=255, null=True, blank=True)
    departamento = models.CharField(max_length=255, null=True, blank=True)
    estado_loc = models.TextField(null=True, blank=True)
    est_oferta = models.TextField(null=True, blank=True)
    estado_est = models.TextField(null=True, blank=True)
    cui_loc = models.CharField(max_length=50, null=True, blank=True)
    cuof_loc = models.CharField(max_length=50, null=True, blank=True)

    class Meta:
        managed = False  # Evita que Django intente crear o modificar la vista
        db_table = 'v_capa_unica_ofertas_cui_cuof'