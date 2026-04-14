from django.db import models

class FAQ(models.Model):
    pregunta = models.TextField(verbose_name="Pregunta")
    respuesta = models.TextField(verbose_name="Respuesta")
    orden = models.PositiveIntegerField(default=0, verbose_name="Orden")

    class Meta:
        ordering = ["orden"]

    def __str__(self):
        return self.pregunta[:70]


class Concepto(models.Model):
    termino = models.CharField(max_length=255, verbose_name="Término")
    definicion = models.TextField(verbose_name="Definición")
    orden = models.PositiveIntegerField(default=0, verbose_name="Orden")

    class Meta:
        ordering = ["orden"]

    def __str__(self):
        return self.termino

