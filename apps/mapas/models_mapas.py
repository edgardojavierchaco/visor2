# apps/mapas/models_mapas.py
from django.contrib.gis.db import models
from django.contrib.gis.geos import Point

class CapaEscuelas(models.Model):
    id = models.BigIntegerField(primary_key=True)  # 🔥 ahora existe
    cueanexo = models.BigIntegerField()
    geom=models.PointField(srid=5347)
    long = models.FloatField()
    lat = models.FloatField()
    nom_est = models.CharField(max_length=200)
    oferta = models.CharField(max_length=100)
    ambito = models.CharField(max_length=100)
    sector = models.CharField(max_length=100)
    region_loc=models.CharField(max_length=20)
    calle=models.CharField(max_length=150)
    numero=models.CharField(max_length=20)
    localidad=models.CharField(max_length=150)     
    
    class Meta:
        managed = False
        db_table="v_capa_unica_ofertas_ant"
        
    def __str__(self):
        return self.nom_est