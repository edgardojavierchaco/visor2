from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator, MaxLengthValidator, RegexValidator
from django.forms import ValidationError

class NivMod(models.Model):
    """
    Modelo que representa un nivel o modalidad de educación.

    Atributos:
        id_niv (AutoField): Identificador único del nivel.
        nivel (CharField): Nombre del nivel o modalidad.
    """
    id_niv=models.AutoField(primary_key=True, name='id_nivel')
    nivel=models.CharField(max_length=255, name='nivel_modalidad')
    
    def __str__(self):
        return self.nivel

class Estado(models.Model):
    """
    Modelo que representa el estado de un cargo o entidad.

    Atributos:
        id_estado (AutoField): Identificador único del estado.
        estado (CharField): Descripción del estado (activo, inactivo, etc.).
    """
    id_estado=models.AutoField(primary_key=True, name='id_estado')
    estado=models.CharField(max_length=25, name='estado')
    
    def __str__(self):
        return self.estado 
    
class NomenCargosDoc(models.Model):
    """
    Modelo que representa un cargo docente con su descripción y atributos relacionados.

    Atributos:
        id_cargo (AutoField): Identificador único del cargo.
        desc_cargo (CharField): Descripción o título del cargo docente.
        nive (ForeignKey): Relación con el modelo NivMod que define el nivel o modalidad.
        estad (ForeignKey): Relación con el modelo Estado que define el estado del cargo.
    """
    id_cargo=models.AutoField(primary_key=True, name='ceic')
    desc_cargo=models.CharField(max_length=255, blank=False, null=False, name='descripcion')
    nive=models.ForeignKey(NivMod, on_delete=models.CASCADE, name='nivel')
    estad=models.ForeignKey(Estado, on_delete=models.CASCADE, name='estado')
    
    def __str__(self):
        return self.desc_cargo
