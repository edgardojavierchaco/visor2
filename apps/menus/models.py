from django.db import models


class MenuItem(models.Model):

    label = models.CharField(max_length=100)
    icon = models.CharField(max_length=100, blank=True)
    url = models.CharField(max_length=200, blank=True)

    parent = models.ForeignKey(
        'self',
        null=True,
        blank=True,
        related_name='children',
        on_delete=models.CASCADE
    )

    roles = models.JSONField(default=list, blank=True)
    categorias = models.JSONField(default=list, blank=True)

    orden = models.PositiveIntegerField(default=0)
    activo = models.BooleanField(default=True)

    # opcional para lógica especial
    clave = models.CharField(max_length=50, blank=True)

    class Meta:
        ordering = ['orden']

    def __str__(self):
        return self.label