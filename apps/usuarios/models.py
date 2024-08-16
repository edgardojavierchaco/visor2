from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin

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
        
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')
        
        return self.create_user(username, password, **extra_fields)


class NivelAcceso(models.Model):
    tacceso = models.CharField(unique=True, max_length=100, verbose_name='tipoacceso')
    
    def __str__(self):
        return self.tacceso
    
    class Meta:
       verbose_name='Nivel_Acceso' 
       verbose_name_plural='Niveles_Accesos'
       ordering = ['tacceso']  
       db_table = 'Nivel_Acceso'

       
       
class UsuariosVisualizador(AbstractBaseUser, PermissionsMixin):
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
    


