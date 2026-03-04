from django.db import models


class CapaUnicaOfertas(models.Model):

    cueanexo = models.CharField(primary_key=True, max_length=9)

    nom_est = models.CharField(max_length=255)

    region_loc = models.IntegerField()

    ref_loc = models.CharField(max_length=255)

    localidad = models.CharField(max_length=255)

    departamento = models.CharField(max_length=255)

    class Meta:
        managed = False
        db_table = "v_capa_unica_ofertas"
        verbose_name = "Escuela"
        verbose_name_plural = "Escuelas"