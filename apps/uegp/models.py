from django.db import models
from django.core.exceptions import ValidationError
from django.utils.dateparse import parse_date
from django.forms import model_to_dict
import re


class CargosCeicUegp(models.Model):
    id = models.AutoField(primary_key=True)
    nivel=models.CharField(max_length=255, verbose_name='nivel')
    ceic_id=models.IntegerField(verbose_name='ceic_id')
    descripcion_ceic=models.CharField(max_length=255, verbose_name='descripcion_ceic')
    estado=models.BooleanField(default=True, verbose_name='estado')
    puntos=models.IntegerField(verbose_name='puntos')    
    
    class Meta:
        db_table='ceic_puntos_uegp'
        managed=False
    
    def __str__(self):
        return f"{self.ceic_id}-{self.descripcion_ceic}"
    
    def toJSON(self):    
        item=model_to_dict(self)    
        item['id']=self.id
        item['nivel']=self.nivel
        item['ceic_id']=self.ceic_id
        item['descripcion_ceic']=self.descripcion_ceic
        item['estado']=self.estado
        item['puntos']=self.puntos
        return item
        
    
class FuncionesDocUegp(models.Model):
    id = models.AutoField(primary_key=True)
    funcion=models.CharField(max_length=100, verbose_name='funcion')
    
    class Meta:
        db_table='funciones_uegp'
        managed=False
    
    def __str__(self):
        return self.funcion
    
    def toJSON(self):    
        item=model_to_dict(self)    
        item['id']=self.id
        item['funcion']=self.funcion        
        return item


class EscalafonUegp(models.Model):
    categoria=models.IntegerField(verbose_name='categoria')
    nom_categ=models.CharField(max_length=255, verbose_name='nom_categ')    
    
    class Meta:
            verbose_name = 'Escalafon_uegp'
            verbose_name_plural='Escalafones_uegp'
            db_table= 'Escalafon_uegp'    
    
    def __str__(self):
        return f"{self.categoria}-{self.nom_categ}"
    
    def toJSON(self):    
        item = model_to_dict(self)
        item['categoria'] = self.categoria
        item['nom_categ'] = self.nom_categ   
        return item
    

class PersonalDocUegp(models.Model):
    
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
    ]
    
    SEXO=[
        ('Masculino', 'Masculino'),
        ('Femenino', 'Femenino'),
    ]
    
        
    NIVEL=[
        ('INICIAL', 'INICIAL'),
        ('PRIMARIO', 'PRIMARIO'),
        ('SECUNDARIO', 'SECUNDARIO'),
        ('TÉCNICA', 'TÉCNICA'),
        ('SUPERIOR', 'SUPERIOR'),
        ('ARTÍSTICA', 'ARTÍSTICA'),
        ('BIBLIOTECAS', 'BIBLIOTECAS'),
        ('SERVICIOS TÉCNICOS', 'SERVICIOS TÉCNICOS'),
        ('EDUCACIÓN FÍSICA', 'EDUCACIÓN FÍSICA'),
        ('ESPECIAL', 'ESPECIAL'),
    ]    
    
    
    SECTOR=[                
        ('Gestión Privada', 'Gestión Privada'),               
    ]
    
    T_DNI=[
        ('DNI', 'DNI'),
        ('CI', 'CI'),
        ('LC', 'LC'),
        ('LE', 'LE'),
        ('CEDULA MERCOSUR', 'CEDULA MERCOSUR'),
        ('PASAPORTE EXTRANJERO', 'PASAPORTE EXTRANJERO'),
        ('CI EXTRANJERA', 'CI EXTRANJERA'),
        ('OTRO DOCUMENTO EXTRANJERO', 'OTRO DOCUMENTO EXTRANJERO'),
    ]
    t_dni=models.CharField(choices=T_DNI, verbose_name='T_DNI')
    dni=models.CharField(max_length=8, blank=False, null=False, verbose_name='DNI')
    cuil=models.CharField(max_length=11, blank=False, null=False, verbose_name='CUIL')
    apellido=models.CharField(max_length=255, blank=False, null=False, verbose_name='Apellido')
    nombres=models.CharField(max_length=255, blank=False, null=False,verbose_name='Nombres')
    f_nac=models.DateField(default='1900-01-01',verbose_name='Fecha_Nac')
    sexo=models.CharField(max_length=9, choices=SEXO, verbose_name='Sexo')
    nivelmod=models.CharField(max_length=25, choices=NIVEL, verbose_name='Nivel_Mod')    
    sector=models.CharField(max_length=50, choices=SECTOR, verbose_name='Sector')    
    cargo=models.ForeignKey(CargosCeicUegp, on_delete=models.CASCADE, verbose_name='Cargos')
    sit_revista=models.CharField(max_length=100, choices=REVISTA, verbose_name='Sit_Revista')
    f_designacion=models.DateField(default='1900-01-01',verbose_name='Fecha_Designacion')  
    subvencionado=models.BooleanField(default=False, verbose_name='Subvencionado')   
    nom_funcion=models.ForeignKey(FuncionesDocUegp,on_delete=models.CASCADE, verbose_name='nom_funcion')
    f_desde=models.DateField(default='1900-01-01',verbose_name='Fecha_Desde') 
    f_hasta=models.DateField(default='2059-12-31',verbose_name='Fecha_Hasta') 
    carga_horaria_sem=models.DecimalField(max_digits=4, decimal_places=2, verbose_name='Horas_Semanales')    
    email=models.EmailField(max_length=255, blank=False, null=False,verbose_name='Correo')
    telefono=models.CharField(max_length=11, blank=False, null=False,verbose_name='Teléfono')
    region=models.CharField(max_length=100, choices=REGIONES, verbose_name='Regional')
    cueanexo=models.CharField(max_length=9, blank=True, null=True,verbose_name='Cueanexo')
    
    class Meta:
            verbose_name = 'Personal_Doc_Uegp'
            verbose_name_plural='Personales_Doc_Uegp'
            db_table= 'Personal_Doc_Uegp'    
        
    def __str__(self):
        return f"{self.apellido} {self.nombres} - {self.dni}"
    
    def toJSON(self):
        item=model_to_dict(self)
        item['t_dni']=self.t_dni
        item['dni']=self.dni
        item['cuil']=self.cuil
        item['apellido']=self.apellido
        item['nombres']=self.nombres
        item['f_nac']=self.f_nac
        item['sexo']=self.sexo
        item['nivelmod']=self.nivelmod
        item['sector']=self.sector
        item['cargo']=self.cargo.descripcion_ceic
        item['sit_revista']=self.sit_revista
        item['f_designacion']=self.f_designacion
        item['subvencionado']=self.subvencionado
        item['nom_funcion']=self.nom_funcion.funcion
        item['f_desde']=self.f_desde
        item['f_hasta']=self.f_hasta
        item['carga_horaria_sem']=self.carga_horaria_sem        
        item['email']=self.email
        item['telefono']=self.telefono
        item['region']=self.region
        item['cueanexo']=self.cueanexo
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
        super(PersonalDocUegp, self).save(*args, **kwargs)


class PersonalNoDocUegp(models.Model):
    
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
    
    NOMBRAMIENTO=[
        ('Tiempo Indeterminado','Tiempo Indeterminado'),
        ('Temporario','Temporario'),        
    ]
    
    SEXO=[
        ('Masculino', 'Masculino'),
        ('Femenino', 'Femenino'),
    ]
    
    NIVEL=[
        ('INICIAL', 'INICIAL'),
        ('PRIMARIO', 'PRIMARIO'),
        ('SECUNDARIO', 'SECUNDARIO'),
        ('TÉCNICA', 'TÉCNICA'),
        ('SUPERIOR', 'SUPERIOR'),
        ('ARTÍSTICA', 'ARTÍSTICA'),
        ('BIBLIOTECAS', 'BIBLIOTECAS'),
        ('SERVICIOS TÉCNICOS', 'SERVICIOS TÉCNICOS'),
        ('EDUCACIÓN FÍSICA', 'EDUCACIÓN FÍSICA'),
        ('ESPECIAL', 'ESPECIAL'),
    ]    
    
    
    SECTOR=[        
        ('Gestión Privada', 'Gestión Privada'),                
    ]
    
    T_DNI=[
        ('DNI', 'DNI'),
        ('CI', 'CI'),
        ('LC', 'LC'),
        ('LE', 'LE'),
        ('CEDULA MERCOSUR', 'CEDULA MERCOSUR'),
        ('PASAPORTE EXTRANJERO', 'PASAPORTE EXTRANJERO'),
        ('CI EXTRANJERA', 'CI EXTRANJERA'),
        ('OTRO DOCUMENTO EXTRANJERO', 'OTRO DOCUMENTO EXTRANJERO'),
    ]
    t_dni=models.CharField(choices=T_DNI, verbose_name='T_DNI')
    dni=models.CharField(max_length=8, blank=False, null=False, verbose_name='DNI')
    cuil=models.CharField(max_length=11, blank=False, null=False, verbose_name='CUIL')
    apellido=models.CharField(max_length=255, blank=False, null=False, verbose_name='Apellido')
    nombres=models.CharField(max_length=255, blank=False, null=False,verbose_name='Nombres')
    f_nac=models.DateField(default='1900-01-01',verbose_name='Fecha_Nac')
    sexo=models.CharField(max_length=9, choices=SEXO, verbose_name='Sexo')    
    categoria=models.ForeignKey(EscalafonUegp, on_delete=models.CASCADE, verbose_name='Categoria')
    sit_nom=models.CharField(max_length=100, choices=NOMBRAMIENTO, verbose_name='Sit_Nombramiento')
    f_designacion=models.DateField(default='1900-01-01',verbose_name='Fecha_Designacion')   
    subvencionado=models.BooleanField(default=False,verbose_name='Subvencionado')  
    nom_funcion=models.ForeignKey(FuncionesDocUegp,on_delete=models.CASCADE, verbose_name='nom_funcion')
    f_desde=models.DateField(default='1900-01-01',verbose_name='Fecha_Desde') 
    f_hasta=models.DateField(default='2059-12-31',verbose_name='Fecha_Hasta') 
    carga_horaria_sem=models.DecimalField(max_digits=4, decimal_places=2, verbose_name='Horas_Semanales')    
    email=models.EmailField(max_length=255, blank=False, null=False,verbose_name='Correo')
    telefono=models.CharField(max_length=11, blank=False, null=False,verbose_name='Teléfono')
    region=models.CharField(max_length=100, choices=REGIONES, verbose_name='Regional')
    cueanexo=models.CharField(max_length=9, blank=True, null=True, verbose_name='Cueanexo')
    
    class Meta:
            verbose_name = 'Personal_No_Doc_Uegp'
            verbose_name_plural='Personales_No_Doc_Uegp'
            db_table= 'Personal_No_Doc_Uegp'    
        
    def __str__(self):
        return f"{self.apellido} {self.nombres} - {self.dni}"
    
    def toJSON(self):
        item=model_to_dict(self)
        item['t_dni']=self.t_dni
        item['dni']=self.dni
        item['cuil']=self.cuil
        item['apellido']=self.apellido
        item['nombres']=self.nombres
        item['f_nac']=self.f_nac
        item['sexo']=self.sexo
        item['categoria']=self.categoria.nom_categ
        item['sit_nom']=self.sit_nom
        item['f_designacion']=self.f_designacion
        item['subvencionado']=self.subvencionado
        item['nom_funcion']=self.nom_funcion.funcion
        item['f_desde']=self.f_desde
        item['f_hasta']=self.f_hasta
        item['carga_horaria_sem']=self.carga_horaria_sem        
        item['email']=self.email
        item['telefono']=self.telefono
        item['region']=self.region
        item['cueanexo']=self.cueanexo
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
        super(PersonalNoDocUegp, self).save(*args, **kwargs)
        
# verificaciones
