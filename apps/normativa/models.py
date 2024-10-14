from django.db import models
from django.core.files import File

class ArchNoramtiva(models.Model):
    """
    Modelo que representa un archivo normativo en la base de datos.

    Atributos:
        asunto (str): El asunto del archivo normativo.
        tnorma (str): El tipo de norma asociada al archivo.
        nro (str): El número de la norma.
        anio (int): El año de la norma.
        archivo (FileField): El archivo normativo que se sube.
        ruta (str): La ruta del archivo en el sistema de archivos, si es aplicable.

    Métodos:
        save(*args, **kwargs): Sobrescribe el método de guardado para manejar la apertura
                               y el almacenamiento del archivo de manera adecuada.
    """
    
    asunto=models.CharField(max_length=100, blank=False, name='asunto')
    tnorma=models.CharField(max_length=100, blank=False, name='tipo_norma')
    nro=models.CharField(max_length=50, blank=False, name='nro')
    anio=models.IntegerField(blank=False,name='año')
    archivo = models.FileField(upload_to='normativa/')
    ruta = models.CharField(max_length=255, null=True, blank=True)
    
    def __str__(self):
        return self.asunto

    def save(self, *args, **kwargs):
        """
        Sobrescribe el método de guardado para asegurarse de que el archivo se
        abra correctamente en modo binario antes de guardarlo.

        Args:
            *args: Argumentos posicionales para el método de guardado.
            **kwargs: Argumentos nombrados para el método de guardado.
        """
        
        # Abrir el archivo en modo binario
        if self.archivo:
            with self.archivo.open('rb') as f:
                self.archivo.save(self.archivo.name, f, save=False)
        super().save(*args, **kwargs)