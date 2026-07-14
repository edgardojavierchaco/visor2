from django.conf import settings
from django.db import models



class PerfilSirtee(models.Model):
    """
    Perfil de participación del usuario dentro de SIRTEE.

    Los permisos reales se obtienen desde:
    
    - apps.usuarios -> PerfilUsuario -> Rol
    - apps.supervisa2 -> RegionalUsuario
    - apps.consultasge -> CapaUnicaOfertas

    Este modelo NO duplica información.
    """


    usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="perfil_sirtee"
    )


    activo = models.BooleanField(
        default=True
    )


    observaciones = models.TextField(
        blank=True,
        null=True
    )


    creado = models.DateTimeField(
        auto_now_add=True
    )


    actualizado = models.DateTimeField(
        auto_now=True
    )



    class Meta:

        db_table = "sirtee_perfilusuario"

        verbose_name = (
            "Perfil SIRTEE"
        )

        verbose_name_plural = (
            "Perfiles SIRTEE"
        )



    def __str__(self):

        return (
            f"SIRTEE - "
            f"{self.usuario.username}"
        )



    # ==================================================
    # Acceso al rol existente
    # apps.usuarios
    # ==================================================

    @property
    def rol(self):

        try:

            return self.usuario.perfil.rol

        except Exception:

            return None



    @property
    def categoria_acceso(self):

        if self.rol:

            return self.rol.categoria_acceso

        return None