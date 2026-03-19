from tabnanny import verbose
from django.db import models, connection
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .models import PerfilUsuario
    
# --------------------------
# Manager personalizado
# --------------------------
class CustomUserManager(BaseUserManager):
    def create_user(self, username, password=None, **extra_fields):
        if not username:
            raise ValueError('The Username field must be set')
        user = self.model(username=username, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, username, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self.create_user(username, password, **extra_fields)

# --------------------------
# Nivel de Acceso
# --------------------------
class NivelAcceso(models.Model):
    tacceso = models.CharField(unique=True, max_length=100, verbose_name='tipoacceso')

    class Meta:
        db_table = 'usuarios_nivelacceso'
    def __str__(self):
        return self.tacceso

# --------------------------
# Roles
# --------------------------
class Rol(models.Model):
    nombre = models.CharField(max_length=100, unique=True)
    descripcion = models.TextField(blank=True, null=True)

    CATEGORIAS = (
        ('all', 'Todo'),
        ('regional', 'Regional'),
        ('propio', 'Propio'),
        ('nivel', 'Nivel'),
    )
    categoria_acceso = models.CharField(max_length=20, choices=CATEGORIAS, default='propio')

    def __str__(self):
        return self.nombre

# --------------------------
# Usuario
# --------------------------
class UsuariosVisualizador(AbstractBaseUser, PermissionsMixin):
    username = models.CharField(unique=True, max_length=11)
    apellido = models.CharField(max_length=150)
    nombres = models.CharField(max_length=150)
    correo = models.EmailField()
    telefono = models.CharField(max_length=20)
    nivelacceso = models.ForeignKey(
        NivelAcceso,
        on_delete=models.CASCADE,
        to_field='tacceso'
    )
    activo = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=True)
    is_superuser = models.BooleanField(default=False)
    date_joined = models.DateTimeField(auto_now_add=True)
    last_login = models.DateTimeField(blank=True, null=True)

    objects = CustomUserManager()

    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ['apellido', 'nombres', 'correo', 'telefono', 'nivelacceso']

    if TYPE_CHECKING:
        perfil: "PerfilUsuario"
        
    class Meta:
        managed = True
        verbose_name = 'Usuario Visualizador'
        verbose_name_plural = 'Usuarios Visualizadores'
        db_table = 'Usuario_Visualizador'

    def __str__(self):
        return self.username

    # Compatibilidad con Django login
    @property
    def is_active(self):
        return self.activo

    # --------------------------
    # Obtener cueanexos según rol
    # --------------------------
    def obtener_cueanexos(self):
        if not hasattr(self, 'perfil') or not self.perfil.rol:
            return []

        categoria = self.perfil.rol.categoria_acceso

        with connection.cursor() as cursor:
            if categoria == 'all':
                cursor.execute("SELECT * FROM v_capa_unica_ofertas")
            elif categoria == 'regional':
                cursor.execute("""
                    SELECT v.*
                    FROM public.v_capa_unica_ofertas v
                    JOIN public.usuarios_regionalusuarios r
                        ON r.region_loc = v.region_loc
                    WHERE r.usuario = %s
                """, [self.username])
            elif categoria == 'propio':
                cursor.execute("""
                    SELECT *
                    FROM v_capa_unica_ofertas
                    WHERE REGEXP_REPLACE(resploc_cuitcuil, '[^0-9]', '', 'g') =
                          REGEXP_REPLACE(%s, '[^0-9]', '', 'g')
                """, [self.username])
            elif categoria == 'nivel':
                cursor.execute("""
                    SELECT v.*
                    FROM public.v_capa_unica_ofertas v
                    JOIN public.niveles_asignados n
                        ON n.nivel = v.oferta
                    WHERE n.cuil= %s
                """, [self.username])
            return cursor.fetchall()
    
    def tiene_biblioteca(self):
        """
        Devuelve True si entre los cueanexos del usuario hay alguno con acrónimo 'Bi'
        """
        cueanexos = self.obtener_cueanexos()  # lista de tuplas de SQL
        # Asumimos que la columna acronimo está en la posición correcta, por ejemplo columna 2
        for fila in cueanexos:
            # Ajusta el índice según la posición de 'acronimo' en tu SELECT *
            if 'BI' in fila:
                return True
        return False
            
        
# --------------------------
# PerfilUsuario
# --------------------------
class PerfilUsuario(models.Model):
    usuario = models.OneToOneField(
        UsuariosVisualizador,
        on_delete=models.CASCADE,
        related_name='perfil'
    )
    rol = models.ForeignKey(Rol, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.usuario.username} - {self.rol.nombre}"


# ========================================
#  MODELO INTERMEDIO CUEANEXO-USUARIOS
# ========================================
class UsuarioCueanexo(models.Model):
    usuario = models.ForeignKey(
        UsuariosVisualizador,
        on_delete=models.CASCADE,
        related_name="cueanexos"
    )
    cueanexo = models.CharField(
        max_length=9,
        unique=True  # 🔥 CLAVE: un cueanexo sólo puede pertenecer a un usuario
    )

    class Meta:
        verbose_name = "Cueanexo del usuario"
        verbose_name_plural = "Cueanexos de usuarios"

    def __str__(self):
        return f"{self.usuario.username} - {self.cueanexo}"