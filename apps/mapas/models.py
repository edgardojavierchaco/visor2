from tabnanny import verbose
from django.db import models
from django.contrib.gis.db import models
from django.forms import model_to_dict
from apps.usuarios.models import UsuariosVisualizador
import json

"""
Este módulo define dos modelos de Django que interactúan con tablas específicas en una base de datos externa. 
Uno de los modelos incluye datos geoespaciales y el otro datos administrativos de localidades.

Clases:
    RegionalesGeometria: Modelo que representa las geometrías de las regiones educativas con datos espaciales.
    LocalidadesRegion: Modelo que representa los detalles de contacto y localización de las localidades dentro de una región.

Ambos modelos están configurados para no ser gestionados por Django (managed=False) ya que las tablas son externas.
"""

class RegionalesGeometria(models.Model):
    """
    Modelo que representa las geometrías de las regiones educativas.

    Atributos:
        id (AutoField): Identificador único del registro.
        geom (GeometryField): Campo espacial que almacena la geometría de la región.
        objectid (IntegerField): Identificador del objeto en la base de datos externa.
        region_pad (CharField): Nombre o código de la región.
        TITULO (TextField): Descripción o título de la región.
    """
    id = models.AutoField(primary_key=True)
    geom = models.GeometryField()
    objectid = models.IntegerField()
    region_pad = models.CharField(max_length=255)
    TITULO = models.TextField()
    
    class Meta:
        managed = False
        db_table = 'c_regiones_educativas_2024_'
        

class LocalidadesRegion(models.Model):
    """
    Modelo que representa los detalles de contacto y localización de las localidades dentro de una región.

    Atributos:
        reg (CharField): Código o nombre de la región.
        nom_dir (CharField): Nombre del director regional.
        tel_dir (CharField): Teléfono de contacto del director regional.
        email_dir (CharField): Correo electrónico del director regional.
        loc_reg (CharField): Nombre de la localidad correspondiente a la región.
        dep_reg (CharField): Nombre del departamento correspondiente a la región.
    """
    reg=models.CharField(max_length=50)
    nom_dir=models.CharField(max_length=255)
    tel_dir=models.CharField(max_length=25)
    email_dir=models.CharField(max_length=255)
    loc_reg=models.CharField(max_length=255)
    dep_reg=models.CharField(max_length=255)    
    
    class Meta:
        managed = False
        db_table = 'localidadesregion'


# Modelo para guardar las interacciones en la búsqueda por LN
class Interaccion(models.Model):
    user = models.ForeignKey(UsuariosVisualizador, on_delete=models.CASCADE, null=True, blank=True)
    query = models.TextField()  # Consulta realizada por el usuario
    resultado = models.TextField()  # Resultado que se devolvió al usuario
    fecha = models.DateTimeField(auto_now_add=True)  # Fecha de la interacción
    criterios_extraidos = models.JSONField(null=True, blank=True)  # Criterios extraídos (para posterior análisis)
    feedback = models.CharField(max_length=255, null=True, blank=True)  # Posible feedback del usuario sobre la respuesta

    class Meta:
        verbose_name='Interaccion'
        verbose_name_plural='Interacciones'
        db_table='interacciones'
        
    def __str__(self):
        return f"Interacción de {self.user} en {self.fecha}"
    
    def toJSON(self):
        item=model_to_dict(self)
        item['user']=self.user.username
        item['query']=self.query
        item['resultado']=self.resultado
        item['fecha']=self.fecha
        item['criterios_extraidos']=self.criterios_extraidos
        item['feedback']=self.feedback
        return item