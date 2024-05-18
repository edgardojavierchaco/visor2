from django.db import models

class ArchNoramtiva(models.Model):
    asunto=models.CharField(max_length=100, blank=False, name='asunto')
    tnorma=models.CharField(max_length=100, blank=False, name='tipo_norma')
    nro=models.CharField(max_length=50, blank=False, name='nro')
    anio=models.IntegerField(blank=False,name='año')
    archivo = models.FileField(upload_to='normativa/')
    ruta = models.CharField(max_length=255, null=True, blank=True)
    
    def __str__(self):
        return self.asunto
