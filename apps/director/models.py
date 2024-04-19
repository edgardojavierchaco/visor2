from django.db import models
from django.contrib.gis.db import models

from django.contrib.gis.db import models


class PadronOfertas(models.Model):
    
    cueanexo = models.CharField(blank=True, null=True, name='cueanexo')
    id_establecimiento = models.CharField(max_length=10,blank=True, null=True, name='id_establecimiento')
    id_localizacion = models.CharField(max_length=10,blank=True, null=True, name='id_localizacion')
    id_oferta_local = models.CharField(max_length=10,primary_key=True, name='id_oferta_local')
    nom_est = models.CharField(blank=True, null=True, name='nom_est')
    acronimo_oferta = models.CharField(blank=True, null=True, name='acronimo_oferta')
    oferta = models.CharField(blank=True, null=True, name='oferta')
    nro_est = models.CharField(blank=True, null=True, name='nro_est')
    ambito = models.CharField(blank=True, null=True,name='ambito')
    sector = models.CharField(blank=True, null=True, name='sector')
    region_loc = models.CharField(blank=True, null=True, name='region_loc')
    ref_loc = models.CharField(blank=True, null=True, name='ref_loc')
    calle = models.CharField(blank=True, null=True, name='calle')
    numero = models.CharField(blank=True, null=True, name='numero')
    localidad = models.CharField(blank=True, null=True, name='localidad')
    departamento = models.CharField(blank=True, null=True, name='departamento')
    estado_loc = models.CharField(blank=True, null=True, name='estado_loc')
    est_oferta = models.CharField(blank=True, null=True, name='est_oferta')
    estado_est = models.CharField(blank=True, null=True, name='estado_est')
    jornada = models.CharField(blank=True, null=True, name='jornada')

    class Meta:
        managed = False
        db_table = 'padron_ofertas'

    def __str__(self):
        return f"{self.cueanexo} - {self.nom_est}"



