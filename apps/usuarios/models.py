from django.contrib.auth.models import AbstractBaseUser,BaseUserManager,PermissionsMixin
from django.db import models

# Create your models here.

class NivelAcceso(models.Model):
    tacceso = models.CharField(unique=True, max_length=100, verbose_name='tipoacceso')
    
    def __str__(self):
        return self.tacceso
    
    class Meta:
       verbose_name='Nivel_Acceso' 
       verbose_name_plural='Niveles_Accesos'
       ordering = ['tacceso']
       db_table = 'Nivel_Acceso'

class UsuariosVisualizadorManager(BaseUserManager):
    def create_user(self, username, password=None, **extra_fields):
        if not username:
            raise ValueError('El nombre de usuario debe ser proporcionado')
        user = self.model(username=username, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, username, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('El superusuario debe tener is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('El superusuario debe tener is_superuser=True.')

        return self.create_user(username, password, **extra_fields)

    def get_by_natural_key(self, username):
        return self.get(username=username)  
       
class UsuariosVisualizador(AbstractBaseUser):
    id = models.AutoField(primary_key=True, verbose_name='id')
    username = models.CharField(unique=True, max_length=9, verbose_name='usuario')
    password = models.CharField(max_length=150,verbose_name='contraseña')
    apellido = models.CharField(max_length=150, verbose_name='apellido')
    nombres = models.CharField(max_length=150, verbose_name='nombres')
    correo = models.EmailField(verbose_name='correo')
    telefono = models.CharField(max_length=20,verbose_name='telefono')
    nivelacceso = models.ForeignKey(NivelAcceso, on_delete=models.CASCADE, verbose_name='nivelacceso')
    activo = models.BooleanField(default=True, verbose_name='activo')
    is_staff = models.BooleanField(default=True, verbose_name='is_staff')
    is_superuser = models.BooleanField(default=False, verbose_name='is_superuser')
  
    # Define el campo de nombre de usuario y establece su valor en 'nomusua'
    USERNAME_FIELD = 'username'

    # Define una lista de campos adicionales requeridos al crear un usuario
    REQUIRED_FIELDS = ['password', 'apellido', 'nombres', 'correo', 'telefono', 'nivelacceso', 'activo']
    
    objects = UsuariosVisualizadorManager()
    
    def has_perm(self, perm, obj=None):
        # En este ejemplo, todos los usuarios tienen todos los permisos
        return True

    def has_module_perms(self, app_label):
        # En este ejemplo, todos los usuarios tienen permisos en todos los módulos
        return True
    
    def __str__(self):
        return self.username
    
    class Meta:
       verbose_name='Usuario_Visualizador' 
       verbose_name_plural='Usuarios_Visulizadores'
       ordering = ['apellido','nombres']
       db_table = 'Usuario_Visualizador'
    
    
    