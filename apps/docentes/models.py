from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator, MaxLengthValidator, RegexValidator
from django.forms import ValidationError

class NivMod(models.Model):
    id_niv=models.AutoField(primary_key=True, name='id_nivel')
    nivel=models.CharField(max_length=255, name='nivel_modalidad')
    
    def __str__(self):
        return self.nivel

class Estado(models.Model):
    id_estado=models.AutoField(primary_key=True, name='id_estado')
    estado=models.CharField(max_length=25, name='estado')
    
    def __str__(self):
        return self.estado 
    
class NomenCargosDoc(models.Model):
    id_cargo=models.AutoField(primary_key=True, name='ceic')
    desc_cargo=models.CharField(max_length=255, blank=False, null=False, name='descripcion')
    nive=models.ForeignKey(NivMod, on_delete=models.CASCADE, name='nivel')
    estad=models.ForeignKey(Estado, on_delete=models.CASCADE, name='estado')
    
    def __str__(self):
        return self.desc_cargo
