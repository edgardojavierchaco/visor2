import os
from django.db import models
from django.conf import settings
from django.forms import model_to_dict
from django.core.exceptions import ValidationError

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
    
    
    