# This is an auto-generated Django model module.
# You'll have to do the following manually to clean this up:
#   * Rearrange models' order
#   * Make sure each model has one field with primary_key=True
#   * Make sure each ForeignKey and OneToOneField has `on_delete` set to the desired behavior
#   * Remove `managed = False` lines if you wish to allow Django to create, modify, and delete the table
# Feel free to rename the models, but don't rename db_table values or field names.
from django.contrib.gis.db import models


class PadronOfertas(models.Model):
    cueanexo = models.IntegerField(blank=True, null=True)
    id_establecimiento = models.CharField(blank=True, null=True)
    id_localizacion = models.CharField(blank=True, null=True)
    id_oferta_local = models.CharField(blank=True, null=True)
    nom_est = models.CharField(blank=True, null=True)
    acronimo_oferta = models.CharField(blank=True, null=True)
    oferta = models.CharField(blank=True, null=True)
    nro_est = models.CharField(blank=True, null=True)
    ambito = models.CharField(blank=True, null=True)
    sector = models.CharField(blank=True, null=True)
    region_loc = models.CharField(blank=True, null=True)
    ref_loc = models.CharField(blank=True, null=True)
    calle = models.CharField(blank=True, null=True)
    numero = models.CharField(blank=True, null=True)
    localidad = models.CharField(blank=True, null=True)
    departamento = models.CharField(blank=True, null=True)
    estado_loc = models.CharField(blank=True, null=True)
    est_oferta = models.CharField(blank=True, null=True)
    estado_est = models.CharField(blank=True, null=True)
    jornada = models.CharField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'padron_ofertas'
