from django.db import models
from django.forms import model_to_dict
from django.core.exceptions import ValidationError

class Supervisor(models.Model):
    REGIONES = [
        ('R.E. 1', 'R.E. 1'),
        ('R.E. 2', 'R.E. 2'),
        ('R.E. 3', 'R.E. 3'),
        ('R.E. 4-A', 'R.E. 4-A'),
        ('R.E. 4-B', 'R.E. 4-B'),
        ('R.E. 5', 'R.E. 5'),
        ('R.E. 6', 'R.E. 6'),
        ('R.E. 7', 'R.E. 7'),
        ('R.E. 8-A', 'R.E. 8-A'),
        ('R.E. 8-B', 'R.E. 8-B'),
        ('R.E. 9', 'R.E. 9'),
        ('R.E. 10-A', 'R.E. 10-A'),
        ('R.E. 10-B', 'R.E. 10-B'),
        ('R.E. 10-C', 'R.E. 10-C'),
        ('SUB. R.E. 1-A', 'SUB. R.E. 1-A'),
        ('SUB. R.E. 1-B', 'SUB. R.E. 1-B'), 
        ('SUB. R.E. 2', 'SUB. R.E. 2'),
        ('SUB. R.E. 3', 'SUB. R.E. 3'),
        ('SUB. R.E. 5', 'SUB. R.E. 5'),
    ]
    
    dni=models.CharField(max_length=8, blank=False, null=False, verbose_name='DNI')
    apellido=models.CharField(max_length=255, blank=False, null=False, verbose_name='Apellido')
    nombres=models.CharField(max_length=255, blank=False, null=False,verbose_name='Nombres')
    email=models.EmailField(max_length=255, blank=False, null=False,verbose_name='Correo')
    telefono=models.CharField(max_length=11, blank=False, null=False,verbose_name='Teléfono')
    region=models.CharField(max_length=100, choices=REGIONES, verbose_name='Regional')
    
    class Meta:
        verbose_name = 'Supervisor_Escuela'
        verbose_name_plural='Supervisores_Escuelas'
        db_table= 'supervisores_escuelas'    
    
    def __str__(self):
        return f"{self.apellido} {self.nombres}"

    def toJSON(self):
        item = model_to_dict(self)
        item['dni'] = self.dni
        item['apellido'] = self.apellido
        item['nombres'] = self.nombres 
        item['email'] = self.email
        item['telefono'] = self.telefono
        item['region'] = self.region 
        return item
    
    def clean(self):
        # Validación para que `dni` tenga entre 7 y 8 dígitos
        if not self.dni.isdigit() or not (7 <= len(self.dni) <= 8):
            raise ValidationError("El DNI debe contener entre 7 y 8 dígitos numéricos, sin puntos ni letras.")

        # Convertir `apellido` y `nombres` a mayúsculas automáticamente
        self.apellido = self.apellido.upper()
        self.nombres = self.nombres.upper()

    def save(self, *args, **kwargs):
        # Llama a la validación y luego guarda
        self.clean()
        super(Supervisor, self).save(*args, **kwargs)
        

class EscuelasSupervisadas(models.Model):
    cueanexo=models.CharField(max_length=9, verbose_name='Cueanexo')
    nom_est=models.CharField(max_length=255, verbose_name='Nombre')
    region=models.CharField(max_length=100, verbose_name='Regional')
    
    class Meta:
        verbose_name = 'Escuela_Supervisada'
        verbose_name_plural='Escuelas_Supervisadas'
        db_table= 'escuelas_supervisadas'    
    
    def __str__(self):
        return f"{self.cueanexo} {self.nom_est}"

    def toJSON(self):
        item = model_to_dict(self)
        item['cueanexo'] = self.cueanexo
        item['nom_est'] = self.nom_est
        item['region'] = self.region 
        return item       
        

class Asignacion(models.Model):
    supervisor=models.ForeignKey(Supervisor, on_delete=models.CASCADE, verbose_name='Supervisor')
    total=models.IntegerField(default=0, verbose_name='Total')

    def __str__(self):
        return f"{self.supervisor.apellido} {self.supervisor.nombres}"
    
    def toJSON(self):
        item = model_to_dict(self)
        item['supervisor'] = f"{self.supervisor.apellido} {self.supervisor.nombres}"
        item['total'] = self.total
        item['det'] = [i.toJSON() for i in self.detalleasignacion_set.all()]
        return item
    
    class Meta:
        verbose_name = 'Asignacion'
        verbose_name_plural = 'Asignaciones'
        ordering = ['supervisor']
        db_table='Asignacion'


class DetalleAsignacion(models.Model):
    asignacion=models.ForeignKey(Asignacion, on_delete=models.CASCADE, verbose_name='Asignacion')
    escuela=models.ForeignKey(EscuelasSupervisadas,on_delete=models.CASCADE, verbose_name='Escuela')
    
    def __str__(self):
        return f"{self.escuela.cueanexo} {self.escuela.nom_est}"
    
    def toJSON(self):
        item = model_to_dict(self)
        item['asignacion_id'] = self.asignacion.id
        item['escuela'] = self.escuela.toJSON()
        return item
    
    class Meta:
        verbose_name='Detalle_Escuela_Supervisada'
        verbose_name_plural='Detalles_Escuelas_Supervisadas'
        ordering=['escuela']
        db_table='Detalle_Asignacion'