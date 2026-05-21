# models.py
import re
from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from .middleware import get_current_user
from smart_selects.db_fields import ChainedForeignKey
from django.utils import timezone


#################
# AUDITORIA
#################
class AuditoriaModel(models.Model):
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_modificacion = models.DateTimeField(auto_now=True)

    usuario_creacion = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='%(class)s_creados'
    )

    usuario_modificacion = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='%(class)s_modificados'
    )

    class Meta:
        abstract = True

    


###############################
# CODIGOS DE ÁREA TELEFÓNICAS
###############################
class CodAreasTelefonos(models.Model):
    id = models.AutoField(primary_key=True)
    cod_prov=models.IntegerField(name='cod_prov')
    provincia=models.CharField(max_length=100)
    localidad=models.CharField(max_length=150)
    codigo=models.IntegerField()
    
    class Meta:
        managed=False
        verbose_name='Codigo Area'
        verbose_name_plural='Codigos Areas'
        db_table='cod_areas'
        ordering=['codigo', 'localidad']
    
    def __str__(self):
        return f'{self.provincia} {self.localidad} - {self.codigo}'

###############################
# TIPOS DE DOCUMENTO IDENTIDAD
###############################
class DocumentoTipo(models.Model):
    c_tipo_doc=models.IntegerField(primary_key=True)
    descrip_doc=models.CharField(max_length=50)
    
    class Meta:
        managed=False
        verbose_name='Tipo Documento'
        verbose_name_plural='Tipos Documentos'
        db_table='documento_tipo'
        
    def __str__(self):
        return self.descrip_doc
    


#####################
# PROVINCIAS
#####################
class Provincias(models.Model):
    c_provincia=models.IntegerField(primary_key=True)
    descrip_provincia=models.CharField(max_length=100)

    class Meta:
        managed=False
        verbose_name='provincia'
        verbose_name_plural='provincias'
        db_table='provincia_tipo'
    
    def __str__(self):
        return self.descrip_provincia


#######################
# LOCALIDADES
#######################
class Localidades(models.Model):
    c_localidad=models.IntegerField(primary_key=True)
    descrip_localidad=models.CharField(max_length=150)
    c_departamento=models.IntegerField()
    descrip_departamento=models.CharField(max_length=150)
    c_provincia=models.ForeignKey(
        Provincias, 
        on_delete=models.PROTECT,
        db_column='c_provincia'
    )
    
    class Meta:
        managed=False
        verbose_name='Localidad'
        verbose_name_plural='Localidades'
        db_table='localidad_tipo'
        ordering=['descrip_localidad']
    
    def __str__(self):
        return f'{self.descrip_localidad} {self.descrip_departamento}'


######################
# MODALIDADES
######################
class Modalidades(models.Model):
    c_modalidad=models.IntegerField(primary_key=True)
    descrip_modalidad=models.CharField(max_length=150)
    
    class Meta:
        managed=False
        verbose_name='modalidad'
        verbose_name_plural='modalidades'
        db_table='modalidades_tipo'
    
    def __str__(self):
        return self.descrip_modalidad


#####################
# NACIONALIDAD
#####################
class Nacionalidad(models.Model):
    c_nacionalidad=models.IntegerField(primary_key=True)
    descrip_nac=models.CharField(max_length=100)
    c_pais=models.IntegerField()
    
    class Meta:
        managed=False
        verbose_name='Nacionalidad'
        verbose_name_plural='Nacionalidades'
        db_table='nacionalidad_tipo'
    
    def __str__(self):
        return self.descrip_nac

####################
# OFERTAS
####################
class NivelServicio(models.Model):
    c_nivel=models.IntegerField(primary_key=True)
    descrip_nivel=models.CharField(max_length=150)
    
    class Meta:
        managed=False
        verbose_name='oferta'
        verbose_name_plural='ofertas'
        db_table='nivel_servicio'
    
    def __str__(self):
        return self.descrip_nivel

###########
# CEIC
###########
class NomencladorCeic(models.Model):
    c_ceic=models.IntegerField(primary_key=True)
    descripcion=models.CharField(max_length=150)
    estado=models.CharField(max_length=25)
    c_niv=models.IntegerField()
    t_nivel=models.CharField(max_length=10)
    
    class Meta:
        managed=False
        verbose_name='nomenclador ceic'
        verbose_name_plural='nomencladores ceic'
        db_table='nomenclador_ceic'
        indexes = [
            models.Index(fields=['t_nivel', 'c_niv']),
        ]

    def __str__(self):
        return f'{self.descripcion} - {self.c_niv}'


##########
# PAICES
##########
class Pais(models.Model):
    c_pais=models.IntegerField(primary_key=True)
    descrip_pais=models.CharField(max_length=100)

    class Meta:
        managed=False
        verbose_name='pais'
        verbose_name_plural='paices'
        db_table='pais_tipo'
    
    def __str__(self):
        return self.descrip_pais

  

###########
# SEXO
###########
class Sexo(models.Model):
    c_sexo=models.IntegerField(primary_key=True)
    descrip_sexo=models.CharField(max_length=25)

    class Meta:
        managed=False 
        verbose_name='sexo'
        verbose_name_plural='sexos'
        db_table='sexo_tipo'
    
    def __str__(self):
        return self.descrip_sexo


##########################
# PERSONAS
##########################
class Personas(AuditoriaModel):
    id = models.BigAutoField(primary_key=True)

    cuil = models.CharField(max_length=11, null=True, blank=True, db_index=True)
    dni = models.CharField(max_length=8, null=True, blank=True, db_index=True)

    apellido = models.CharField(max_length=150, db_index=True)
    nombre = models.CharField(max_length=150, db_index=True)

    sexo = models.ForeignKey('Sexo', on_delete=models.PROTECT)
    provincia = models.ForeignKey('Provincias', on_delete=models.PROTECT)

    localidad = models.ForeignKey('Localidades', on_delete=models.PROTECT)
    
    codigo_area = models.ForeignKey(
        CodAreasTelefonos,
        on_delete=models.PROTECT,
        null=True,
        blank=True
    )

    telefono = models.CharField(
        max_length=8,
        null=True,
        blank=True,
        validators=[
            RegexValidator(
                r'^\d{6,8}$',
                message='Ingrese solo el número local (6 a 8 dígitos, sin código de área)'
            )
        ]
    )

    telefono_normalizado = models.CharField(max_length=15, null=True, blank=True, db_index=True)
    whatsapp = models.BooleanField(default=False)

    estado = models.CharField(
        max_length=10,
        choices=[('ACTIVO', 'Activo'), ('PASIVO', 'Pasivo')],
        default='ACTIVO'
    )

    class Meta:
        db_table = "personas"
        indexes = [
            models.Index(fields=['dni']), 
            models.Index(fields=['cuil']),
            models.Index(fields=['telefono_normalizado']),
        ]

    # =========================
    # VALIDACIONES
    # =========================
    def clean(self):
        if self.dni:
            validar_dni(self.dni)
        if self.cuil:
            validar_cuil(self.cuil)
    
    
    # =========================
    # NORMALIZACIÓN PRO
    # =========================
    def normalizar_telefono(self):
        """
        Devuelve número en formato E.164
        Ej: +54362445566
        """
        if not self.telefono or not self.codigo_area:
            return None

        numero = re.sub(r'\D', '', self.telefono)
        codigo = str(self.codigo_area.codigo)

        return f"+54{codigo}{numero}"
    
    
    # =========================
    # SAVE
    # =========================
    def save(self, *args, **kwargs):
        if not kwargs.pop("skip_clean", False):
            self.full_clean()
        
        # 🔥 normalización SIEMPRE antes de guardar
        self.telefono_normalizado = self.normalizar_telefono()
        super().save(*args, **kwargs)
    
    
    # =========================
    # HELPERS PRO
    # =========================
    def telefono_para_whatsapp(self):
        """
        WhatsApp usa sin '+'
        """
        if not self.telefono_normalizado:
            return None
        return self.telefono_normalizado.replace("+", "")

    def telefono_display(self):
        """
        Formato lindo para UI
        """
        if not self.telefono or not self.codigo_area:
            return ""

        return f"({self.codigo_area.codigo}) {self.telefono}"
        

############################
# FUNCIONES DE VALIDACION
############################
def validar_dni(dni):
    if not dni:
        return

    if not dni.isdigit():
        raise ValidationError('DNI debe contener solo números')

    if len(dni) not in (7, 8):
        raise ValidationError('DNI inválido')


def validar_cuil(cuil):
    if not cuil:
        return

    cuil = re.sub(r'[^\d]', '', cuil)

    if len(cuil) != 11:
        raise ValidationError('CUIL debe tener 11 dígitos')

    coef = [5,4,3,2,7,6,5,4,3,2]

    tmp = sum(int(cuil[i]) * coef[i] for i in range(10))
    resto = tmp % 11

    dv = 11 - resto
    if dv == 11:
        dv = 0
    elif dv == 10:
        dv = 9

    if dv != int(cuil[-1]):
        raise ValidationError('CUIL inválido (dígito verificador incorrecto)')
    

#########################
# SITUACION REVISTA
#########################
class SituacionServicio(models.Model):
    cod_sitrev=models.IntegerField(primary_key=True)
    descrip_sitrev=models.CharField(max_length=50)
    
    class Meta:
        managed=False
        db_table='situacion_revista'
    
    def __str__(self):
        return self.descrip_sitrev


#########################
# CONDICION DE ACTIVIDAD
#########################
class CondicionActividad(models.Model):
    cod_condicion=models.IntegerField(primary_key=True)
    descrip_condicion=models.CharField(max_length=50)
    
    class Meta:
        managed=False
        db_table='condicion_actividad_bnh'
    
    def __str__(self):
        return self.descrip_condicion


#########################
# TITULOS DE ESPACIOS
#########################
class TitulosEspacios(models.Model):
    cod_titulo=models.IntegerField(primary_key=True)
    descrip_titulo=models.CharField(max_length=255)
    
    class Meta:
        managed=False
        db_table='titulos_docentes'
    
    def __str__(self):
        return self.descrip_titulo


###############################
# REGISTRO DE ACTIVIDADES
###############################
class RegistroActividades(AuditoriaModel):

    cueanexo = models.CharField(max_length=9, db_index=True)
    persona = models.ForeignKey(Personas, on_delete=models.CASCADE, related_name='actividades')

    categoria = models.CharField(max_length=10, choices=[
        ('DOCENTE', 'Docente'),
        ('NO DOCENTE', 'No Docente'),
    ])

    modalidad = models.ForeignKey('Modalidades', on_delete=models.PROTECT)
    niveles = models.ForeignKey('NivelServicio', on_delete=models.PROTECT)

    sit_revista = models.ForeignKey('SituacionServicio', on_delete=models.PROTECT)
    cond_actividad = models.ForeignKey('CondicionActividad', on_delete=models.PROTECT)
    
    designacion=models.CharField(max_length=20, choices=[
        ('CARGO', 'CARGO'),
        ('HORAS CATEDRAS', 'HORAS CATEDRAS'),
    ], default='CARGO')

    ceic = models.ForeignKey('NomencladorCeic', on_delete=models.PROTECT)
    
    grado_anio = models.CharField(max_length=2)
    
    turno=models.CharField(max_length=20, choices=[
        ('MAÑANA', 'MAÑANA'),
        ('TARDE', 'TARDE'),
        ('NOCHE', 'NOCHE'),
        ('VESPERTINO', 'VESPERTINO'),
    ],
        default='MAÑANA'
    )
    
    secciones=models.CharField(max_length=2, null=False, blank=False)
    
    espacios=models.ForeignKey('TitulosEspacios', on_delete=models.PROTECT)
    
    f_desde = models.DateField()
    f_hasta = models.DateField()
    carga_horaria = models.DecimalField(max_digits=4, decimal_places=2)

    estado = models.CharField(max_length=10, choices=[
        ('ACTIVO', 'Activo'),
        ('INACTIVO', 'Inactivo'),
    ])

    class Meta:
        db_table = "registro_actividades"
        
    # =========================
    # 🔥 VALIDACIÓN DOMINIO
    # =========================
    def clean(self):

        errors = {}

        hoy = timezone.localdate()
        
        if self.f_desde:

            if self.f_desde > hoy:
                errors["f_desde"] = (
                    "La fecha 'desde' no puede ser posterior a la fecha actual"
                )
        
        if self.f_desde and self.f_hasta:
            if self.f_hasta < self.f_desde:
                errors["f_hasta"] = "La fecha 'hasta' no puede ser menor a 'desde'"

        if not self.cueanexo:
            errors["cueanexo"] = "CUEANEXO es obligatorio"

        if errors:
            raise ValidationError(errors)

    # =========================
    # 🔥 NORMALIZACIÓN (IMPORTANTE CON VIEWS)
    # =========================
    def normalize(self):
        """
        💡 garantiza consistencia del dato externo
        """
        if self.cueanexo:
            self.cueanexo = str(self.cueanexo).strip()
