from django.db import models
from django.core.exceptions import ValidationError

class RegionalUsuariosAgentes(models.Model):
    TURNOS = (
        ("manana", "Mañana (07:00 - 13:00)"),
        ("tarde", "Tarde (13:00 - 18:00)"),
    )
    
    usuario = models.CharField(max_length=11, db_index=True) 
    region_loc = models.CharField(max_length=100, db_index=True)
    turno = models.CharField(max_length=10, choices=TURNOS, db_index=True)
    activo = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Gestor Regional"
        verbose_name_plural = "Gestores Regionales"
        indexes = [
            models.Index(fields=["region_loc", "activo"]),
        ]

    def clean(self):
        # Mantenemos la lógica de validación para asegurar un solo gestor activo por región
        if self.activo and RegionalUsuariosAgentes.objects.filter(
            region_loc__iexact=self.region_loc, 
            activo=True
        ).exclude(pk=self.pk).exists():
            raise ValidationError(f"Ya existe un gestor activo en la región {self.region_loc}.")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        # Ahora 'usuario' es directamente el string (ej. el username)
        return f"{self.usuario} - {self.region_loc} ({self.get_turno_display()})"


class RegionalUsuarios(models.Model):
    usuario = models.CharField(max_length=11, db_index=True)
    region_loc = models.CharField(max_length=100, db_index=True)
    activo = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Usuario Regional"
        verbose_name_plural = "Usuarios Regionales"
        indexes = [
            models.Index(fields=["region_loc", "activo"]),
        ]

    def clean(self):
        # Validación para permitir un solo usuario activo por región
        if self.activo and RegionalUsuarios.objects.filter(
            region_loc__iexact=self.region_loc,
            activo=True
        ).exclude(pk=self.pk).exists():
            raise ValidationError(f"Ya existe un usuario activo en la región {self.region_loc}.")

    def save(self, *args, **kwargs):
        self.full_clean()  # Ejecuta clean() antes de guardar
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.usuario} - {self.region_loc}"