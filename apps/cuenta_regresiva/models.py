from django.db import models

class FechaEvento(models.Model):
    nombre = models.CharField(max_length=100)
    fecha_evento = models.DateTimeField()

    def __str__(self):
        return self.nombre

