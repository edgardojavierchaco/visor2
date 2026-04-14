from django.db import models

from apps.alumnos.models import oferta


class CapaUnicaOfertas(models.Model):

    cueanexo = models.CharField(primary_key=True, max_length=9)

    nom_est = models.CharField(max_length=255)

    region_loc = models.CharField(max_length=255)

    ref_loc = models.CharField(max_length=255)

    localidad = models.CharField(max_length=255)

    departamento = models.CharField(max_length=255)
    
    oferta = models.CharField(max_length=255)
    
    acronimo = models.CharField(max_length=100)
    
    resploc_cuitcuil= models.CharField(max_length=20)

    class Meta:
        managed = False
        db_table = "v_capa_unica_ofertas_ant"
        verbose_name = "Escuela"
        verbose_name_plural = "Escuelas"