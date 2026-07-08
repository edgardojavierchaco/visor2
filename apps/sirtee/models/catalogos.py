from django.db import models


class CategoriaHallazgo(models.Model):
    nombre = models.CharField(max_length=150, unique=True)
    descripcion = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.nombre


class TipoIntervencion(models.Model):
    nombre = models.CharField(max_length=150, unique=True)
    requiere_aprobacion = models.BooleanField(default=False)

    def __str__(self):
        return self.nombre


class EstadoGeneral(models.Model):
    """
    Catálogo transversal para relevamientos, hallazgos e intervenciones.
    """
    entidad = models.CharField(max_length=50)  # relevamiento | hallazgo | intervencion
    nombre = models.CharField(max_length=50)

    class Meta:
        unique_together = ("entidad", "nombre")

    def __str__(self):
        return f"{self.entidad} - {self.nombre}"


class Criticidad(models.Model):
    nivel = models.CharField(max_length=50, unique=True)  # BAJA / MEDIA / ALTA / CRITICA
    prioridad = models.IntegerField(default=0)

    class Meta:
        ordering = ["-prioridad"]

    def __str__(self):
        return self.nivel