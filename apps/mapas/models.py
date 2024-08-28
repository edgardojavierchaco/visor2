from django.db import models
from django.contrib.gis.db import models as gis_models

class VCapaUnicaOfertas(models.Model):
    cueanexo = models.CharField(max_length=12, primary_key=True)
    geom = gis_models.GeometryField(srid=4326, null=True, blank=True)
    long = models.FloatField(null=True, blank=True)
    lat = models.FloatField(null=True, blank=True)
    nom_est = models.CharField(max_length=255)
    padron_cueanexo = models.CharField(max_length=12)
    acronimo = models.TextField()
    oferta = models.TextField()
    etiqueta = models.TextField()
    nro_est = models.IntegerField()
    ambito = models.CharField(max_length=255)
    sector = models.CharField(max_length=255)
    region_loc = models.CharField(max_length=255)
    ref_loc = models.CharField(max_length=255, null=True, blank=True)
    calle = models.CharField(max_length=255, null=True, blank=True)
    numero = models.CharField(max_length=10, null=True, blank=True)
    localidad = models.CharField(max_length=255)
    departamento = models.CharField(max_length=255)
    estado_loc = models.TextField()
    est_oferta = models.TextField()
    estado_est = models.TextField()

    class Meta:
        db_table = 'v_capa_unica_ofertas'
        managed = False  # Esto indica que Django no gestionará la creación de la tabla.

    def __str__(self):
        return f"{self.nom_est} - {self.cueanexo}"




    

