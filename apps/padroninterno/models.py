from django.conf import settings
from django.db import models


# ==========================================================
# MODELOS DE PERMISOS PARA PADRÓN INTERNO
# ==========================================================
# Estos modelos leen las tablas globales de usuarios/roles,
# pero pertenecen al módulo padroninterno.
# managed = False porque las tablas ya existen en la BD.
# ==========================================================


class PadronRolUsuario(models.Model):
    nombre = models.CharField(max_length=100)

    class Meta:
        managed = False
        db_table = 'usuarios_rol'
        verbose_name = 'Rol de usuario'
        verbose_name_plural = 'Roles de usuario'

    def __str__(self):
        return self.nombre or ''


class PadronUsuarioPerfil(models.Model):
    usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.DO_NOTHING,
        db_column='usuario_id',
        related_name='perfil_padroninterno',
    )
    rol = models.ForeignKey(
        PadronRolUsuario,
        on_delete=models.DO_NOTHING,
        db_column='rol_id',
        related_name='perfiles_padroninterno',
    )

    class Meta:
        managed = False
        db_table = 'usuarios_perfilusuario'
        verbose_name = 'Perfil de usuario para Padrón Interno'
        verbose_name_plural = 'Perfiles de usuario para Padrón Interno'

    def __str__(self):
        usuario_txt = getattr(self.usuario, 'username', self.usuario_id)
        rol_txt = getattr(self.rol, 'nombre', '')
        return f'{usuario_txt} - {rol_txt}'


# ==========================================================
# FUNCIONES DE PERMISOS PARA PADRÓN INTERNO
# ==========================================================

# models.py -> define quién puede entrar
# permisos.py -> solo aplica el bloqueo
# views_*.py -> solo usan el decorador

ROLES_PADRON_INTERNO = {
    'Administrador',
    'Gestor',
}


def obtener_rol_usuario_padron(user):
    """
    Devuelve el nombre del rol del usuario logueado.
    Usa usuarios_perfilusuario -> usuarios_rol.
    """
    if not user or not user.is_authenticated:
        return None

    try:
        perfil = (
            PadronUsuarioPerfil.objects
            .select_related('rol')
            .get(usuario__username=user.username)
        )
        return (perfil.rol.nombre or '').strip()
    except PadronUsuarioPerfil.DoesNotExist:
        return None


def usuario_puede_ver_padron_interno(user):
    """
    Solo permite acceso al módulo Padrón Interno a Administrador o Gestor.
    """
    rol = obtener_rol_usuario_padron(user)

    if not rol:
        return False

    return rol in ROLES_PADRON_INTERNO