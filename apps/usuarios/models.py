from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin

class CustomUserManager(BaseUserManager):
    """
    Administrador de usuarios personalizado para gestionar la creación de usuarios.

    Métodos:
        create_user: Crea y devuelve un usuario normal.
        create_superuser: Crea y devuelve un superusuario.
    """
    
    def create_user(self, username, password=None, **extra_fields):
        """
        Crea y devuelve un usuario con un nombre de usuario y una contraseña.

        Args:
            username (str): El nombre de usuario para el nuevo usuario.
            password (str, optional): La contraseña del nuevo usuario.
            **extra_fields: Campos adicionales a añadir al usuario.

        Raises:
            ValueError: Si el campo de nombre de usuario no está definido.

        Returns:
            UsuariosVisualizador: El usuario creado.
        """
        
        if not username:
            raise ValueError('The Username field must be set')
        user = self.model(username=username, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, username, password=None, **extra_fields):
        """
        Crea y devuelve un superusuario con un nombre de usuario y una contraseña.

        Args:
            username (str): El nombre de usuario para el superusuario.
            password (str, optional): La contraseña del superusuario.
            **extra_fields: Campos adicionales a añadir al superusuario.

        Raises:
            ValueError: Si el campo is_staff o is_superuser no está establecido a True.

        Returns:
            UsuariosVisualizador: El superusuario creado.
        """
        
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')
        
        return self.create_user(username, password, **extra_fields)


class NivelAcceso(models.Model):
    """
    Modelo que representa los niveles de acceso para los usuarios.

    Atributos:
        tacceso (str): El tipo de acceso, debe ser único.
    """

    tacceso = models.CharField(unique=True, max_length=100, verbose_name='tipoacceso')
    
    def __str__(self):
        return self.tacceso
    
    class Meta:
       verbose_name='Nivel_Acceso' 
       verbose_name_plural='Niveles_Accesos'
       ordering = ['tacceso']  
       db_table = 'Nivel_Acceso'

       
       
class UsuariosVisualizador(AbstractBaseUser, PermissionsMixin):
    """
    Modelo que representa a los usuarios visualizadores en el sistema.

    Atributos:
        username (str): Nombre de usuario único.
        apellido (str): Apellido del usuario.
        nombres (str): Nombres del usuario.
        correo (str): Correo electrónico del usuario.
        telefono (str): Teléfono del usuario.
        nivelacceso (NivelAcceso): Nivel de acceso del usuario, con relación a NivelAcceso.
        activo (bool): Indica si el usuario está activo.
        is_staff (bool): Indica si el usuario es parte del personal.
        is_superuser (bool): Indica si el usuario tiene privilegios de superusuario.

    Métodos:
        __str__: Retorna el nombre de usuario.
    """
    
    username = models.CharField(unique=True, max_length=9, verbose_name='usuario')
    apellido = models.CharField(max_length=150, verbose_name='apellido')
    nombres = models.CharField(max_length=150, verbose_name='nombres')
    correo = models.EmailField(verbose_name='correo')
    telefono = models.CharField(max_length=20, verbose_name='telefono')
    nivelacceso = models.ForeignKey(NivelAcceso, on_delete=models.CASCADE, to_field='tacceso', verbose_name='nivelacceso')
    activo = models.BooleanField(default=True, verbose_name='activo')
    is_staff = models.BooleanField(default=True, verbose_name='is_staff')
    is_superuser = models.BooleanField(default=False, verbose_name='is_superuser')

    REQUIRED_FIELDS = ['apellido', 'nombres', 'correo', 'telefono', 'nivelacceso']

    objects = CustomUserManager()

    USERNAME_FIELD = 'username'

    def __str__(self):
        return self.username

    class Meta:
        verbose_name = 'Usuario_Visualizador'
        verbose_name_plural = 'Usuarios_Visualizadores'
        ordering = ['apellido', 'nombres']
        db_table = 'Usuario_Visualizador'
    


