from django.db import models

class AsuntoRegister(models.Model):
    asunto = models.CharField(max_length=150, blank=False, name='asunto')

    def __str__(self):
        return self.asunto
    
class ArchRegister(models.Model):
    cueanexo = models.CharField(max_length=10, blank=False, name='cueanexo')
    asunto = models.ForeignKey(AsuntoRegister, on_delete=models.CASCADE)
    nro_normativa = models.CharField(max_length=100, blank=False, name='nro_normativa')
    descripcion = models.TextField(name='descripcion')
    archivo = models.FileField(upload_to='archivo_normativa/')
    ruta = models.CharField(max_length=255, null=True, blank=True)

    def __str__(self):
        return f"{self.cueanexo} - {self.asunto}"
    
    @property
    def nombre_asunto(self):
        return self.asunto.asunto if self.asunto else ""