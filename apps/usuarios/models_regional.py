from django.db import models
from regex import B


class RegionalUsuariosAgentes(models.Model):

    TURNOS = (
        ("manana", "Mañana (07:00 - 13:00)"),
        ("tarde", "Tarde (13:00 - 18:00)"),
    )

    usuario = models.OneToOneField(
        "usuarios.UsuariosVisualizador",  # 🔥 referencia por string
        on_delete=models.CASCADE,
        related_name="perfil_regional",
        db_column="usuario_id",
        to_field="username"
    )

    region_loc = models.CharField(
        max_length=100,
        verbose_name="Regional",
        db_index=True  # 🚀 mejora rendimiento en filtros
    )

    turno = models.CharField(
        max_length=10,
        choices=TURNOS,
        verbose_name="Turno laboral",
        db_index=True
    )

    activo = models.BooleanField(
        default=True,
        db_index=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        verbose_name = "Gestor Regional"
        verbose_name_plural = "Gestores Regionales"
        indexes = [
            models.Index(fields=["region_loc", "turno"]),
        ]

    def __str__(self):
        return f"{self.usuario.username} - {self.region_loc} ({self.get_turno_display()})"