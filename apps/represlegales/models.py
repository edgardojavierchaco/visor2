from django.db import models
from django.forms import model_to_dict
from django.core.exceptions import ValidationError
from django.utils.dateparse import parse_date
import re

from apps import represlegales

class RepresentantesLegales(models.Model):
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
    
    REVISTA = [
        ('Titular', 'Titular'),
        ('Interino', 'Interino'),
        ('Suplente', 'Suplente'),
        ('Contratado', 'Contratado'),
        ('Otro', 'Otro'),
    ]
    
    SEXO=[
        ('Masculino', 'Masculino'),
        ('Femenino', 'Femenino'),
    ]
    
    
    dni=models.CharField(max_length=8, blank=False, null=False, verbose_name='DNI')
    cuil=models.CharField(max_length=11, blank=False, null=False, verbose_name='CUIL')
    apellido=models.CharField(max_length=255, blank=False, null=False, verbose_name='Apellido')
    nombres=models.CharField(max_length=255, blank=False, null=False,verbose_name='Nombres')
    f_nac=models.DateField(default='1900-01-01',verbose_name='Fecha_Nac')
    sexo=models.CharField(max_length=9, choices=SEXO, verbose_name='Sexo')
    sit_revista=models.CharField(max_length=100, choices=REVISTA, verbose_name='Sit_Revista')
    f_designacion=models.DateField(default='1900-01-01',verbose_name='Fecha_Designacion')
    email=models.EmailField(max_length=255, blank=False, null=False,verbose_name='Correo')
    telefono=models.CharField(max_length=11, blank=False, null=False,verbose_name='Teléfono')
    region=models.CharField(max_length=100, choices=REGIONES, verbose_name='Regional')
    
    class Meta:
        verbose_name = 'RepresentanteLegal_Escuela'
        verbose_name_plural='RepresentantesLegales_Escuelas'
        db_table= 'representantelegal_escuelas'    
    
    def __str__(self):
        return f"{self.apellido} {self.nombres} {self.region}"

    def toJSON(self):
        item = model_to_dict(self)
        item['dni'] = self.dni
        item['cuil'] = self.cuil
        item['apellido'] = self.apellido
        item['nombres'] = self.nombres 
        item['f_nac'] = self.f_nac
        item['sexo'] = self.sexo
        item['sit_revista'] = self.sit_revista
        item['f_desingacion'] = self.f_designacion
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
        
        # Validar formato de `f_nac` y `f_designacion` (dd/mm/aaaa)
        if not self.is_valid_date_format(self.f_nac):
            raise ValidationError("La fecha de nacimiento debe tener el formato DD/MM/AAAA.")
        if not self.is_valid_date_format(self.f_designacion):
            raise ValidationError("La fecha de designación debe tener el formato DD/MM/AAAA.")


    def is_valid_date_format(self, date):
        """Valida si una fecha tiene el formato dd/mm/aaaa."""
        try:
            if isinstance(date, str):
                # Verificar formato dd/mm/aaaa
                if not re.match(r'^\d{2}/\d{2}/\d{4}$', date):
                    return False
                parse_date(date)  # Asegura que sea una fecha válida
            return True
        except ValueError:
            return False

    def save(self, *args, **kwargs):
        # Llama a la validación y luego guarda
        self.clean()
        super(RepresentantesLegales, self).save(*args, **kwargs)
        

class EscuelasRepresentadas(models.Model):
    cueanexo=models.CharField(max_length=9, verbose_name='Cueanexo')
    nom_est=models.CharField(max_length=255, verbose_name='Nombre')
    oferta=models.CharField(max_length=255, verbose_name='Oferta')
    region=models.CharField(max_length=100, verbose_name='Regional')
    
    
    class Meta:        
        verbose_name = 'Escuela_Representada'
        verbose_name_plural='Escuelas_Representadas'
        db_table= 'escuelas_representadas'    
    
    def __str__(self):
        return f"{self.cueanexo} {self.nom_est} {self.oferta}"

    def toJSON(self):
        item = model_to_dict(self)
        item['cueanexo'] = self.cueanexo
        item['nom_est'] = self.nom_est
        item['oferta']=self.oferta
        item['region'] = self.region        
        return item       
        

class Asignacion(models.Model):
    replegales=models.ForeignKey(RepresentantesLegales, on_delete=models.CASCADE, verbose_name='Replegales')
    total=models.IntegerField(default=0, verbose_name='Total')

    def __str__(self):
        return f"{self.replegales.apellido} {self.replegales.nombres} {self.replegales.region}"
    
    def toJSON(self):
        item = model_to_dict(self)
        item['replegales'] = f"{self.replegales.apellido} {self.replegales.nombres}"
        item['total'] = self.total
        item['det'] = [i.toJSON() for i in self.detalleasignacion_set.all()]
        return item
    
    class Meta:
        verbose_name = 'Asignacion'
        verbose_name_plural = 'Asignaciones'
        ordering = ['replegales']
        db_table='Asignacion_Representadas'


class DetalleAsignacion(models.Model):
    asignacion=models.ForeignKey(Asignacion, on_delete=models.CASCADE, verbose_name='Asignacion')
    escuela=models.ForeignKey(EscuelasRepresentadas,on_delete=models.CASCADE, verbose_name='Escuela')
    
    def __str__(self):
        return f"{self.escuela.cueanexo} {self.escuela.nom_est}"
    
    def toJSON(self):
        item = model_to_dict(self)
        item['asignacion_id'] = self.asignacion.id
        item['escuela'] = self.escuela.toJSON()
        return item
    
    class Meta:
        verbose_name='Detalle_Escuela_Representada'
        verbose_name_plural='Detalles_Escuelas_Representadas'
        ordering=['escuela']
        db_table='Detalle_Asignacion_Representadas'
