from django.db import models
from django.contrib.gis.db import models

class VCapaUnicaOfertas(models.Model):
    cueanexo = models.BigIntegerField(blank=True, null=True)
    geom = models.GeometryField(blank=True, null=True)  
    long = models.FloatField(blank=True, null=True)
    lat = models.FloatField(blank=True, null=True)
    nom_est = models.CharField(blank=True, null=True)
    padron_cueanexo = models.IntegerField(blank=True, null=True)
    acronimo = models.TextField(blank=True, null=True)
    oferta = models.TextField(blank=True, null=True)
    etiqueta = models.TextField(blank=True, null=True)
    nro_est = models.CharField(blank=True, null=True)
    ambito = models.CharField(blank=True, null=True)
    sector = models.CharField(blank=True, null=True)
    region_loc = models.CharField(blank=True, null=True)
    ref_loc = models.CharField(blank=True, null=True)
    calle = models.CharField(blank=True, null=True)
    numero = models.CharField(blank=True, null=True)
    localidad = models.CharField(blank=True, null=True)
    departamento = models.CharField(blank=True, null=True)
    estado_loc = models.TextField(blank=True, null=True)
    est_oferta = models.TextField(blank=True, null=True)
    estado_est = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'v_capa_unica_ofertas'

