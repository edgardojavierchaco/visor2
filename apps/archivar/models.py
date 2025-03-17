import os
from django.db import models
from django.conf import settings
from django.forms import model_to_dict
from django.core.exceptions import ValidationError
from django.contrib.gis.db import models

class AsuntoRegister(models.Model):
    
    asunto = models.CharField(max_length=150, blank=False, verbose_name='asunto')

    def __str__(self):
        return self.asunto
    
class nivel(models.Model):
    
    niveles=models.CharField(max_length=150, blank=False, verbose_name='niveles')
    
    def __str__(self):
        return self.niveles

class TNormativa(models.Model):
    
    t_norma=models.CharField(max_length=150, blank=False, verbose_name='t_norma')
    
    def __str__(self):
        return self.t_norma
    
    
class ArchRegister(models.Model):    
    cueanexo = models.CharField(max_length=10, blank=False, verbose_name='cueanexo')
    asunto = models.ForeignKey(AsuntoRegister, on_delete=models.CASCADE, verbose_name='asunto')
    nivel=models.ForeignKey(nivel,on_delete=models.CASCADE, verbose_name='nivel')
    t_norma=models.ForeignKey(TNormativa,on_delete=models.CASCADE, verbose_name='t_norma')
    nro_normativa = models.CharField(max_length=100, blank=False, verbose_name='nro_normativa')
    anio=models.IntegerField(blank=False, verbose_name='año')
    descripcion = models.TextField(verbose_name='descripcion')
    archivo = models.FileField(upload_to='archivo_normativa/')
    ruta = models.CharField(max_length=255, null=True, blank=True)

    def __str__(self):
        return f"{self.cueanexo} - {self.asunto}"
    
    @property
    def nombre_asunto(self):
        
        return self.asunto.asunto if self.asunto else ""


    def save(self, *args, **kwargs):     
        
        super().save(*args, **kwargs)        
        
        if self.archivo:
            self.ruta = os.path.join(settings.MEDIA_ROOT, self.archivo.name)
            super().save(update_fields=['ruta']) 
            
    
    def clean(self):
    
        # Verificamos que `cueanexo` exista y sea una cadena de 9 dígitos numéricos
        if self.cueanexo and (not self.cueanexo.isdigit() or len(self.cueanexo) != 9):
            raise ValidationError("El Cueanexo debe contener exactamente 9 dígitos numéricos, sin puntos ni letras.")
          
    
    def toJSON(self):
        item = model_to_dict(self)
        item['cueanexo'] = self.cueanexo
        item['asunto'] = self.asunto.asunto
        item['nivel'] = self.nivel.niveles
        item['t_norma'] = self.t_norma .t_norma
        item['nro_normativa'] = self.nro_normativa
        item['anio'] = self.anio
        item['descripcion'] = self.descripcion
        item['archivo'] = self.archivo.url
        item['ruta'] = self.ruta        
        return item
    
    
class VCapaUnicaOfertasCuiCuof(models.Model):
    cueanexo = models.CharField(max_length=9)
    geom = models.GeometryField()
    long = models.FloatField()
    lat = models.FloatField()
    nom_est = models.CharField(max_length=255, null=True, blank=True)
    padron_cueanexo = models.CharField(max_length=15, null=True, blank=True)
    acronimo = models.TextField(null=True, blank=True)
    oferta = models.TextField(null=True, blank=True)
    etiqueta = models.TextField(null=True, blank=True)
    nro_est = models.IntegerField(null=True, blank=True)
    ambito = models.CharField(max_length=50, null=True, blank=True)
    sector = models.CharField(max_length=50, null=True, blank=True)
    region_loc = models.CharField(max_length=50, null=True, blank=True)
    ref_loc = models.CharField(max_length=255, null=True, blank=True)
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
        managed = False  
        verbose_name='Capa_Unica'
        verbose_name_plural='Capas_Unicas'
        db_table = 'v_capa_unica_ofertas_cui_cuof'  
        
    def __str__(self):
        return f'{self.cueanexo} {self.nom_est}'
    