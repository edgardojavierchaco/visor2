from django.db import models

from django.contrib.gis.db import models

class RegionalesGeometria(models.Model):
    id = models.AutoField(primary_key=True)
    geom = models.GeometryField()
    objectid = models.IntegerField()
    region_pad = models.CharField(max_length=255)
    TITULO = models.TextField()
    
    class Meta:
        managed = False
        db_table = 'c_regiones_educativas_2024_'
        

class LocalidadesRegion(models.Model):
    
    reg=models.CharField(max_length=50)
    nom_dir=models.CharField(max_length=255)
    tel_dir=models.CharField(max_length=25)
    email_dir=models.CharField(max_length=255)
    loc_reg=models.CharField(max_length=255)
    dep_reg=models.CharField(max_length=255)    
    
    class Meta:
        managed = False
        db_table = 'localidadesregion'

