from django.db import models

class ArchMapas(models.Model):
    titulo=models.CharField(max_length=100,blank=False)
    archivo = models.FileField(upload_to='mapoteca/')
    ruta = models.CharField(max_length=255, null=True, blank=True)
    
    def __str__(self):
        return self.titulo
    
