from django.db import models
from django.forms import model_to_dict
from django.core.exceptions import ValidationError
from django.utils.dateparse import parse_date
import re

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
    
    REVISTA = [
        ('Titular', 'Titular'),
        ('Interino', 'Interino'),
        ('Suplente', 'Suplente'),
    ]
    
    SEXO=[
        ('Masculino', 'Masculino'),
        ('Femenino', 'Femenino'),
    ]
    
    NIVEL=[
        ('Inicial', 'Inicial'),
        ('Primario', 'Primario'),
        ('Secundario', 'Secundario'),
        ('Superior', 'Superior'),
        ('Multinivel', 'Multinivel'),
    ]
    
    MODALIDAD=[
        ('Común', 'Común'),
        ('Jóvenes y Adultos', 'Jóvenes y Adultos'),
        ('Artística', 'Artística'),
        ('Bilingüe Intercultural', 'Bilingüe Intercultural'),
        ('Educación Especial', 'Educación Especial'),
        ('Educación Física', 'Educación Física'),
        ('Servicios Complementarios', 'Servicios Complementarios'),
        ('Rural', 'Rural'),
        ('Técnica - Form. Prof.', 'Técnica - Form. Prof.'),
        ('Hospitalaria - Domiciliaria', 'Hospitalaria - Domiciliaria'),
        ('Mutimodalidad', 'Multimodalidad'),
    ]
    
    SECTOR=[
        ('Gestión Estatal', 'Gestión Estatal'),
        ('Gestión Social', 'Gestión Social'),
        ('Gestión Comunitaria', 'Gestión Comunitaria'),
        ('Gestión Privada', 'Gestión Privada'),
        ('Multigestión', 'Multigestión'),        
    ]
    
    dni=models.CharField(max_length=8, blank=False, null=False, verbose_name='DNI')
    cuil=models.CharField(max_length=11, blank=False, null=False, verbose_name='CUIL')
    apellido=models.CharField(max_length=255, blank=False, null=False, verbose_name='Apellido')
    nombres=models.CharField(max_length=255, blank=False, null=False,verbose_name='Nombres')
    f_nac=models.DateField(default='1900-01-01',verbose_name='Fecha_Nac')
    sexo=models.CharField(max_length=9, choices=SEXO, verbose_name='Sexo')
    sit_revista=models.CharField(max_length=100, choices=REVISTA, verbose_name='Sit_Revista')
    f_designacion=models.DateField(default='1900-01-01',verbose_name='Fecha_Designacion')
    cuof=models.IntegerField(verbose_name='CUOF')
    cuof_anexo=models.IntegerField(verbose_name='Anexo CUOF')
    nivel=models.CharField(max_length=25, choices=NIVEL, verbose_name='Nivel')
    modalidad=models.CharField(max_length=50, choices=MODALIDAD, verbose_name='Modalidad')
    sector=models.CharField(max_length=50, choices=SECTOR, verbose_name='Sector')
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
        item['cuil'] = self.cuil
        item['apellido'] = self.apellido
        item['nombres'] = self.nombres 
        item['f_nac'] = self.f_nac
        item['sexo'] = self.sexo
        item['sit_revista'] = self.sit_revista
        item['f_desingacion'] = self.f_designacion
        item['cuof'] = self.cuof
        item['cuof_anexo'] = self.cuof_anexo
        item['nivel'] = self.nivel
        item['modalidad'] = self.modalidad
        item['sector'] = self.sector
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

        # Validar que `cuof` sea numérico y tenga máximo 4 dígitos
        if not (0 <= self.cuof <= 9999):
            raise ValidationError("El CUOF debe ser numérico y no puede tener más de 4 dígitos.")

        # Validar que `cuof_anexo` tenga máximo 2 dígitos
        if not (0 <= self.cuof_anexo <= 99):
            raise ValidationError("El Anexo CUOF no puede tener más de 2 dígitos.")

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