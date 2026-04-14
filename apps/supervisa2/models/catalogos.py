from django.db import models


class NivelModalidad(models.Model):
    nombre = models.CharField(max_length=150, unique=True)
    codigo = models.CharField(max_length=50, blank=True, null=True)

    class Meta:
        db_table = "nivel_modalidad"

    def __str__(self):
        return self.nombre


class Region(models.Model):
    nombre = models.CharField(max_length=100, unique=True)

    class Meta:
        db_table = "region"

    def __str__(self):
        return self.nombre


class SituacionRevista(models.Model):
    nombre = models.CharField(max_length=100, unique=True)

    class Meta:
        db_table = "situacion_revistas"
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre