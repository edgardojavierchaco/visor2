import os
import json
from django.db import models
from django.conf import settings
from django.forms import model_to_dict
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models


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
    departamento=models.CharField(max_length=255, verbose_name='Departamento')
    localidad=models.CharField(max_length=255, verbose_name='Localidad')
    anio_edif=models.IntegerField(verbose_name='Inauguracion')
    patrimonio=models.BooleanField(default=False, verbose_name='Patrimonio')
    antiguedad=models.IntegerField(verbose_name='Antigüedad')
    dist_munic=models.DecimalField(max_digits=6,decimal_places=2, verbose_name='Distancia_Municipio')
    dist_tierra=models.DecimalField(max_digits=6,decimal_places=2, verbose_name='Distancia_Tierra')
    dist_pavim=models.DecimalField(max_digits=6,decimal_places=2, verbose_name='Distancia_Pavimento')
    
    class Meta:
        verbose_name='Dominio_Escuela'
        verbose_name_plural='Dominios_Escuelas'
        db_table='dominio_escuela'
    
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
        item=self.departamento
        item=self.localidad
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
    sup_terrreno=models.DecimalField(max_digits=6,decimal_places=2, verbose_name='Sup_Terreno')
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
        item=self.sup_terrreno
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
    
    

