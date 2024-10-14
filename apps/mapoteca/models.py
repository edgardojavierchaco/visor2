from django.db import models

class ArchMapas(models.Model):
    """
    Modelo que representa un mapa en la base de datos.

    Atributos:
        titulo (str): El título del mapa, con un límite de 100 caracteres. Este campo no puede estar en blanco.
        archivo (FileField): El archivo del mapa que se subirá a la carpeta 'mapoteca/'.
        ruta (str, optional): La ruta del archivo en el sistema de archivos, puede ser nulo o estar en blanco.

    Métodos:
        __str__(): Devuelve una representación en forma de cadena del objeto, que es el título del mapa.
    """
    titulo=models.CharField(max_length=100,blank=False)
    archivo = models.FileField(upload_to='mapoteca/')
    ruta = models.CharField(max_length=255, null=True, blank=True)
    
    def __str__(self):
        return self.titulo
    
