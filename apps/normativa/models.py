from django.db import models
from django.core.files import File

class ArchNoramtiva(models.Model):
    asunto=models.CharField(max_length=100, blank=False, name='asunto')
    tnorma=models.CharField(max_length=100, blank=False, name='tipo_norma')
    nro=models.CharField(max_length=50, blank=False, name='nro')
    anio=models.IntegerField(blank=False,name='año')
    archivo = models.FileField(upload_to='normativa/')
    ruta = models.CharField(max_length=255, null=True, blank=True)
    
    def __str__(self):
        return self.asunto

    def save(self, *args, **kwargs):
        # Abrir el archivo en modo binario
        if self.archivo:
            with self.archivo.open('rb') as f:
                self.archivo.save(self.archivo.name, f, save=False)
        super().save(*args, **kwargs)