from django.db import models
from django.forms import model_to_dict

# Definir las áreas (Lengua, Matemáticas)
class Area(models.Model):
    nombre = models.CharField(max_length=100)
    
    class Meta:
        verbose_name='Area'
        verbose_name_plural='Areas'
        db_table='Areas'

    def __str__(self):
        return self.nombre
    
    def toJSON(self):
        item=model_to_dict(self)
        item['nombre']=self.nombre
        return item


# Definir las categorías dentro de cada área (Genérico, Contenido, Puntuación, Tildación, Ortrografía, Mayúsculas)
class Categoria(models.Model):
    nombre = models.CharField(max_length=100)
    area = models.ForeignKey(Area, related_name='categorias', on_delete=models.CASCADE)
    
    class Meta:
        verbose_name='Categoria'
        verbose_name_plural='Categorias'
        db_table='Categorias'

    def __str__(self):
        return f'{self.nombre} ({self.area.nombre})'
    
    def toJSON(self):
        item=model_to_dict(self)
        item['nombre']=self.nombre
        item['area']=self.area
        return item

# Definir las preguntas, asociadas a una categoría y un área
class Pregunta(models.Model):
    texto = models.CharField(max_length=500)
    categorias = models.ManyToManyField(Categoria, related_name='preguntas')  
    area = models.ForeignKey(Area, related_name='preguntas', on_delete=models.CASCADE)
    
    class Meta:
        verbose_name='Pregunta'
        verbose_name_plural='Preguntas'
        db_table='Preguntas'

    def __str__(self):
        return self.texto
    
    def toJSON(self):
        item = model_to_dict(self, exclude=['categorias'])  # Excluye categorías porque es M2M
        item['nombre'] = self.texto
        item['categoria'] = [c.nombre for c in self.categorias.all()]  # Lista de nombres de categorías
        item['area'] = self.area.nombre  
        return item

