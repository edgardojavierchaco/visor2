from django.db import models
from django.contrib.postgres.fields import JSONField

class Indicator(models.Model):
    code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=200)
    description = models.TextField(null=True, blank=True)

    level = models.CharField(max_length=50)  # escuela, depto, provincia
    unit = models.CharField(max_length=20, default="%")

    formula = models.JSONField()  # 🔥 motor flexible
    active = models.BooleanField(default=True)

    def __str__(self):
        return self.code


class IndicatorResult(models.Model):
    indicator_code = models.CharField(max_length=50)

    cueanexo = models.CharField(max_length=50)
    ra = models.CharField(max_length=50, null=True, blank=True)
    orientacion = models.CharField(max_length=50, null=True, blank=True)
    grado = models.CharField(max_length=20, null=True, blank=True)

    period = models.CharField(max_length=10)  # 2024, 2025
    value = models.FloatField()

    metadata = models.JSONField(default=dict)
    calculated_at = models.DateTimeField(auto_now_add=True)