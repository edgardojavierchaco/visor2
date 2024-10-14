import os
from django.db import models
from django.conf import settings

class AsuntoRegister(models.Model):
    """
    Modelo para almacenar asuntos relacionados con registros de archivos.

    Attributes:
        asunto (str): Descripción del asunto, con un máximo de 150 caracteres.
    """
    asunto = models.CharField(max_length=150, blank=False, name='asunto')

    def __str__(self):
        return self.asunto
    
class nivel(models.Model):
    """
    Modelo para almacenar niveles de clasificación.

    Attributes:
        niveles (str): Nombre del nivel, con un máximo de 150 caracteres.
    """
    niveles=models.CharField(max_length=150, blank=False, name='niveles')
    
    def __str__(self):
        return self.niveles

class TNormativa(models.Model):
    """
    Modelo para almacenar tipos de normativa.

    Attributes:
        t_norma (str): Descripción del tipo de normativa, con un máximo de 150 caracteres.
    """
    t_norma=models.CharField(max_length=150, blank=False, name='t_norma')
    
    def __str__(self):
        return self.t_norma
    
    
class ArchRegister(models.Model):
    """
    Modelo para registrar archivos normativos asociados a un anexo.

    Attributes:
        cueanexo (str): Código único del anexo, con un máximo de 10 caracteres.
        asunto (ForeignKey): Relación con el modelo AsuntoRegister, que describe el asunto del registro.
        nivel (ForeignKey): Relación con el modelo Nivel, que indica el nivel de clasificación del registro.
        t_norma (ForeignKey): Relación con el modelo TNormativa, que describe el tipo de normativa.
        nro_normativa (str): Número de la normativa correspondiente, con un máximo de 100 caracteres.
        anio (int): Año asociado con la normativa, debe ser un entero.
        descripcion (str): Descripción del archivo o su contenido.
        archivo (FileField): Archivo a ser subido y asociado al registro, con un directorio de carga especificado.
        ruta (str): Ruta donde se almacena el archivo subido, puede ser nula o vacía.

    Methods:
        nombre_asunto (str): Devuelve el asunto del registro.
        save: Sobrescribe el método save para actualizar la ruta del archivo una vez guardado.
    """
    cueanexo = models.CharField(max_length=10, blank=False, name='cueanexo')
    asunto = models.ForeignKey(AsuntoRegister, on_delete=models.CASCADE, name='asunto')
    nivel=models.ForeignKey(nivel,on_delete=models.CASCADE, name='nivel')
    t_norma=models.ForeignKey(TNormativa,on_delete=models.CASCADE, name='t_norma')
    nro_normativa = models.CharField(max_length=100, blank=False, name='nro_normativa')
    anio=models.IntegerField(blank=False, name='año')
    descripcion = models.TextField(name='descripcion')
    archivo = models.FileField(upload_to='archivo_normativa/')
    ruta = models.CharField(max_length=255, null=True, blank=True)

    def __str__(self):
        return f"{self.cueanexo} - {self.asunto}"
    
    @property
    def nombre_asunto(self):
        """
        Obtiene el nombre del asunto relacionado con el registro.

        Returns:
            str: Nombre del asunto, o una cadena vacía si no hay asunto.
        """
        return self.asunto.asunto if self.asunto else ""


    def save(self, *args, **kwargs):     
        """
        Guarda el registro y actualiza la ruta del archivo subido.

        Llama al método save de la superclase y luego actualiza el campo 'ruta'
        con la ubicación del archivo una vez que ha sido guardado en el sistema.

        Args:
            *args: Argumentos adicionales para el método save.
            **kwargs: Argumentos adicionales para el método save.
        """   
        super().save(*args, **kwargs)        
        
        if self.archivo:
            self.ruta = os.path.join(settings.MEDIA_URL, self.archivo.name)
            super().save(update_fields=['ruta']) 