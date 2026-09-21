# models.py
import re
import uuid
from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from .middleware import get_current_user
from django.utils import timezone
from datetime import date
from dateutil.relativedelta import relativedelta


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
        db_table='documento_tipo_bnh'
        
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
        db_table='provincia_tipo_bnh'
    
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
        db_table='localidad_tipo_bnh'
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
        db_table='nacionalidad_tipo_bnh'
    
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
        ordering=['descripcion']
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
        db_table='pais_tipo_bnh'
    
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
        db_table='sexo_tipo_bnh'
    
    def __str__(self):
        return self.descrip_sexo


#############################
# OTROS CATÁLOGOS
#############################
class TipoTelefono(models.Model):
    c_tipo_telefono=models.IntegerField(primary_key=True)
    descrip_tipo_telefono=models.CharField(max_length=50)
    
    class Meta:
        managed=False
        verbose_name='Tipo Telefono'
        verbose_name_plural='Tipos Telefonos'
        db_table='tipo_telefono'
    
    def __str__(self):
        return self.descrip_tipo_telefono
    

class EstadosCiviles(models.Model):
    c_estado_civil=models.IntegerField(primary_key=True)
    descrip_estado_civil=models.CharField(max_length=50)
    
    class Meta:
        managed=False
        verbose_name='Estado Civil'
        verbose_name_plural='Estados Civiles'
        db_table='estado_civil_tipo_bnh'
    
    def __str__(self):
        return self.descrip_estado_civil


class TipoEmail(models.Model):
    c_tipo_email=models.IntegerField(primary_key=True)
    descrip_tipo_email=models.CharField(max_length=50)
    
    class Meta:
        managed=False
        verbose_name='Tipo Email'
        verbose_name_plural='Tipos Email'
        db_table='tipo_email_bnh'
    
    def __str__(self):
        return self.descrip_tipo_email


class RelacionParentesco(models.Model):
    c_relacion_parentesco=models.IntegerField(primary_key=True)
    descrip_relacion_parentesco=models.CharField(max_length=50)
    
    class Meta:
        managed=False
        verbose_name='Relacion Parentesco'
        verbose_name_plural='Relaciones Parentesco'
        db_table='relacion_parentesco_tipo'
    
    def __str__(self):
        return self.descrip_relacion_parentesco



class TipoDiscapacidad(models.Model):
    c_tipo_discapacidad=models.IntegerField(primary_key=True)
    descrip_tipo_discapacidad=models.CharField(max_length=50)
    
    class Meta:
        managed=False
        verbose_name='Tipo Discapacidad'
        verbose_name_plural='Tipos Discapacidad'
        db_table='tipo_discapacidad_bnh'
    
    def __str__(self):
        return self.descrip_tipo_discapacidad


class TipoDocenteIntegrador(models.Model):
    c_tipo_docente_integrador=models.IntegerField(primary_key=True)
    descrip_tipo_docente_integrador=models.CharField(max_length=50)
    
    class Meta:
        managed=False
        verbose_name='Tipo Docente Integrador'
        verbose_name_plural='Tipos Docente Integrador'
        db_table='tipo_docente_integrador'
    
    def __str__(self):
        return self.descrip_tipo_docente_integrador



class TipoComunidadOriginaria(models.Model):
    c_tipo_comunidad_originaria=models.IntegerField(primary_key=True)
    descrip_tipo_comunidad_originaria=models.CharField(max_length=50)
    
    class Meta:
        managed=False
        verbose_name='Tipo Comunidad Originaria'
        verbose_name_plural='Tipos Comunidad Originaria'
        db_table='tipo_comunidad_originaria_bnh'
    
    def __str__(self):
        return self.descrip_tipo_comunidad_originaria


class TipoLenguaOriginaria(models.Model):
    c_tipo_lengua_originaria=models.IntegerField(primary_key=True)
    descrip_tipo_lengua_originaria=models.CharField(max_length=50)
    
    class Meta:
        managed=False
        verbose_name='Tipo Lengua Originaria'
        verbose_name_plural='Tipos Lengua Originaria'
        db_table='tipo_lengua_originaria_bnh'
    
    def __str__(self):
        return self.descrip_tipo_lengua_originaria


class TipoPlanesSociales(models.Model):
    c_tipo_planes_sociales=models.IntegerField(primary_key=True)
    descrip_tipo_planes_sociales=models.CharField(max_length=50)
    
    class Meta:
        managed=False
        verbose_name='Tipo Plan Social'
        verbose_name_plural='Tipos Planes Sociales'
        db_table='tipo_planes_sociales_bnh'
    
    def __str__(self):
        return self.descrip_tipo_planes_sociales



class NivelFormacion(models.Model):
    c_nivel_formacion=models.IntegerField(primary_key=True)
    descrip_nivel_formacion=models.CharField(max_length=50)
    
    class Meta:
        managed=False
        verbose_name='Nivel Formación'
        verbose_name_plural='Niveles Formación'
        db_table='nivel_formacion'
    
    def __str__(self):
        return self.descrip_nivel_formacion


class TipoOS(models.Model):
    c_tipo_os=models.IntegerField(primary_key=True, db_column='c_os')
    descrip_os=models.CharField(max_length=50)
    
    class Meta:
        managed=False
        verbose_name='Tipo OS'
        verbose_name_plural='Tipos OS'
        db_table='tipo_obra_social_bnh'
    
    def __str__(self):
        return self.descrip_os


class Grado_anio(models.Model):
    c_grado_anio=models.BigAutoField(primary_key=True)
    nombre_grado_anio=models.CharField(max_length=100, null=True, blank=True, db_index=True)
    estado=models.BooleanField(default=True)
    c_niv_grado=models.IntegerField()
    t_niv_grado=models.CharField(max_length=100,null=True, blank=True)
    
    c_modalidad1 = models.IntegerField(null=True, blank=True)

    class Meta:
        indexes = [models.Index(fields=["c_modalidad1", "c_niv_grado", "estado"], name="bnh_grado_parent1_idx")]
        verbose_name="Grado_Anio"
        verbose_name_plural="Grados_Anios"
        db_table="grado_anio"
        
    def __str__(self):
        return self.nombre_grado_anio or ""


class Secciones(models.Model):
    c_seccion = models.BigAutoField(primary_key=True)

    nombre_seccion = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        db_index=True,
    )

    estado = models.BooleanField(
        default=True,
    )

    c_niv_seccion = models.IntegerField()

    t_niv_seccion = models.CharField(
        max_length=100,
        null=True,
        blank=True,
    )

    c_modalidad1 = models.IntegerField(
        null=True,
        blank=True,
    )

    class Meta:
        verbose_name = "Seccion"
        verbose_name_plural = "Secciones"
        db_table = "Secciones"

        indexes = [
            models.Index(
                fields=[
                    "c_modalidad1",
                    "c_niv_seccion",
                    "estado",
                ],
                name="bnh_seccion_parent1_idx",
            ),
        ]

    def __str__(self):
        return self.nombre_seccion or ""
    
    
##########################
# PERSONAS
##########################
class Personas(AuditoriaModel):
    id = models.BigAutoField(primary_key=True)

    cuil = models.CharField(max_length=11, null=True, blank=True)
    version = models.PositiveIntegerField(default=1)
    archivada = models.BooleanField(default=False, db_index=True)
    dni = models.CharField(max_length=8, null=True, blank=True, db_index=True)

    apellido = models.CharField(max_length=150, db_index=True)
    nombre = models.CharField(max_length=150, db_index=True)
    f_nacimiento=models.DateField()
    
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
        constraints = [
            models.UniqueConstraint(
                fields=["cuil"],
                condition=models.Q(cuil__isnull=False) & ~models.Q(cuil=""),
                name="bnh_persona_cuil_unico",
            ),
            models.CheckConstraint(
                condition=models.Q(estado__in=["ACTIVO", "PASIVO"]),
                name="bnh_persona_estado_valido",
            ),
            models.CheckConstraint(
                condition=models.Q(version__gte=1),
                name="bnh_persona_version_positiva",
            ),
        ]
        indexes = [
            models.Index(fields=["archivada", "apellido", "nombre"], name="bnh_persona_lista_idx"),
        ]

    # =========================
    # VALIDACIONES
    # =========================
    def __str__(self):
        return f"{self.apellido}, {self.nombre}"

    def clean(self):
        errors = {}
        for campo, validator in (("dni", validar_dni), ("cuil", validar_cuil)):
            value = getattr(self, campo)
            if value:
                try:
                    validator(value)
                except ValidationError as exc:
                    errors[campo] = exc.messages
        if self.cuil and self.dni and self.cuil[2:10] != self.dni.zfill(8):
            errors["dni"] = "El DNI no coincide con el CUIL."
        if self.f_nacimiento and self.f_nacimiento > timezone.localdate():
            errors["f_nacimiento"] = "La fecha de nacimiento no puede ser futura."
        if self.localidad_id and self.provincia_id:
            if not Localidades.objects.filter(pk=self.localidad_id, c_provincia_id=self.provincia_id).exists():
                errors["localidad"] = "La localidad no pertenece a la provincia."
        if bool(self.telefono) != bool(self.codigo_area_id):
            errors["telefono"] = "Complete juntos el código de área y el teléfono."
        if errors:
            raise ValidationError(errors)

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
        raise ValidationError("CUIL inválido (dígito verificador no representable)")

    if dv != int(cuil[-1]):
        raise ValidationError('CUIL inválido (dígito verificador incorrecto)')
    

#########################
# SITUACION REVISTA
#########################
class SituacionServicio(models.Model):
    cod_sitrev=models.IntegerField(primary_key=True)
    descrip_sitrev=models.CharField(max_length=50)
    ayuda = models.TextField(
        blank=True,
        null=True
    )
    
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
    ayuda = models.TextField(
        blank=True,
        null=True
    )
    
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
    descrip_titulo=models.CharField(max_length=255, unique=True)
    
    class Meta:
        managed=False
        db_table='titulos_docentes'
        ordering=['descrip_titulo']
    
    def __str__(self):
        return self.descrip_titulo


#############################
# TIPO DE FUNCIONES
#############################
class TipoFunciones(models.Model):
    c_funciones=models.IntegerField(primary_key=True)
    funciones_descripcion=models.CharField(max_length=100, unique=True)
    ayuda = models.TextField(
        blank=True,
        null=True
    )
    
    class Meta:
        managed=False
        db_table='funciones_tipo_bnh'
    
    def __str__(self):
        return self.funciones_descripcion
    
    
#################################
# TIPO DE DESIGNACIÓN / FUNCIÓN
#################################
class TipoDesigFunc(models.Model):
    c_desigfunc=models.IntegerField(primary_key=True)
    desigfunc_descripcion=models.CharField(max_length=100, unique=True)
    ayuda = models.TextField(
        blank=True,
        null=True
    )
    
    class Meta:
        managed=True
        db_table='desigfunc_tipo_bnh'
    
    def __str__(self):
        return self.desigfunc_descripcion
    

#################################
# MODALIDAD - NIVELES
#################################
class ModalidadNivel(models.Model): 
    id = models.BigAutoField(primary_key=True)
    modalidad = models.ForeignKey(Modalidades, on_delete=models.CASCADE)
    nivel = models.ForeignKey(NivelServicio, on_delete=models.CASCADE)

    class Meta:
        db_table = "modalidad_nivel"
        unique_together = ("modalidad", "nivel")

    def __str__(self):
        return f"{self.modalidad} - {self.nivel}"



#################################
# MODALIDAD - NIVELES - CEIC
#################################    
class ModalidadNivelCeic(models.Model):

    modalidad = models.ForeignKey(Modalidades, on_delete=models.CASCADE)
    nivel = models.ForeignKey(NivelServicio, on_delete=models.CASCADE)

    rango_ceic = models.CharField(
        max_length=500,
        help_text="Ej.: 1-21,220,221"
    )
    
    class Meta:
        db_table = "modalidad_nivel_ceic"
        unique_together = ("modalidad", "nivel")

    def __str__(self):
        return f"{self.modalidad} - {self.nivel} - {self.rango_ceic}"
    
    

###############################
# REGISTRO DE ACTIVIDADES
###############################
class RegistroActividades(AuditoriaModel):

    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, db_index=True)
    cueanexo = models.CharField(max_length=9, db_index=True)
    persona = models.ForeignKey(Personas, on_delete=models.CASCADE, related_name='actividades')

    tipo_personal = models.ForeignKey(
        'TipoPersonal',
        on_delete=models.PROTECT,
        to_field='c_tpersonal',
        db_column='c_tpersonal',
        related_name='actividades',
    )

    modalidad = models.ForeignKey('Modalidades', on_delete=models.PROTECT)
    niveles = models.ForeignKey('NivelServicio', on_delete=models.PROTECT)

    sit_revista = models.ForeignKey('SituacionServicio', on_delete=models.PROTECT)

    # Catálogo nuevo. Se filtra por Tipo de personal + Situación de revista.
    cond_actividad = models.ForeignKey(
        'CondicionActividadNombre',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='actividades',
    )

    # Valor histórico de la condición anterior. Se conserva únicamente
    # para trazabilidad y no se expone en formularios.
    cond_actividad_legacy = models.ForeignKey(
        'CondicionActividad',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='+',
    )

    # Designación fue eliminada. Sólo queda Tipo de designación.
    t_designacion = models.ForeignKey('TipoDesigFunc', on_delete=models.PROTECT)

    ceic = models.ForeignKey('NomencladorCeic', on_delete=models.PROTECT)

    # ========================================================
    # CIRCUITO CURRICULAR (INDEPENDIENTE DEL CEIC)
    # ========================================================
    modalidad_curricular = models.ForeignKey(
        'ModalidadTipo',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='+',
    )
    nivel_curricular = models.ForeignKey(
        'NivelServicioTipo',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='+',
    )
    titulacion = models.BigIntegerField(null=True, blank=True, db_index=True)
    titulacion_fuente = models.CharField(
        max_length=12,
        blank=True,
        default='',
        choices=[
            ('NOMBRE', 'Titulación nombre'),
            ('SUPERIOR', 'Titulación superior'),
            ('FP', 'Titulación formación profesional'),
        ],
    )
    espacio_curricular = models.ForeignKey(
        'EspacioCurricularNombre',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='+',
    )

    grado_anio = models.ForeignKey('Grado_anio', on_delete=models.PROTECT, null=True, blank=True)
    
    turno=models.CharField(max_length=20, choices=[
        ('MAÑANA', 'MAÑANA'),
        ('MAÑANA EXTENDIDA', 'MAÑANA EXTENDIDA'),
        ('TARDE', 'TARDE'),
        ('TARDE EXTENDIDA', 'TARDE EXTENDIDA'),
        ('NOCHE', 'NOCHE'),
        ('VESPERTINO', 'VESPERTINO'),
        ('DOBLE','DOBLE'),
        ('DOBLE EXTENDIDA','DOBLE EXTENDIDA'),
    ],
        default='MAÑANA'
    )
    
    secciones=models.ForeignKey('Secciones', on_delete=models.PROTECT, null=True, blank=True)
    
    espacios = models.ForeignKey(
        'TitulosEspacios',
        on_delete=models.PROTECT,
        to_field='descrip_titulo',
        db_column='descrip_titulo', null=True, blank=True
    )    
    f_desde = models.DateField()
    f_hasta = models.DateField(null=True, blank=True)
    carga_horaria = models.DecimalField(max_digits=5, decimal_places=2)

    estado = models.CharField(max_length=10, choices=[
        ('ACTIVO', 'Activo'),
        ('INACTIVO', 'Inactivo'),
    ])
    
    funciones = models.ForeignKey(
        'TipoFunciones',
        on_delete=models.PROTECT,
        db_column='c_funciones',
    )
    
    f_desde_funciones = models.DateField(default=date.today)
    f_hasta_funciones = models.DateField(null=True, blank=True)

    version = models.PositiveIntegerField(default=1)
    eliminado = models.BooleanField(default=False, db_index=True)
    validacion = models.CharField(max_length=12, default="BORRADOR", choices=[
        ("BORRADOR", "Pendiente de validación"), ("VALIDADO", "Validado"), ("OBSERVADO", "Observado")])

    # ========================================================
    # IDENTIFICACIÓN ÚNICA DEL PUESTO
    # Formato:
    # CUEANEXO_NIVEL_TITULACION_ESPACIO_GRADO_SECCION_CEIC_CONSECUTIVO
    # Los componentes curriculares que no correspondan se expresan como -2.
    # ========================================================
    puesto_base = models.CharField(
        max_length=160,
        editable=False,
        db_index=True,
    )
    puesto_consecutivo = models.PositiveIntegerField(
        editable=False,
    )
    id_puesto = models.CharField(
        max_length=180,
        editable=False,
        db_index=True,
    )

    class Meta:
        db_table = "registro_actividades"
        indexes = [
            models.Index(fields=["cueanexo", "eliminado", "estado"], name="bnh_cue_estado_idx"),
            models.Index(fields=["persona", "cueanexo", "eliminado"], name="bnh_persona_cue_del_idx"),
            models.Index(fields=["persona", "eliminado"], name="bnh_persona_del_idx"),
            models.Index(fields=["modalidad_curricular", "nivel_curricular"], name="bnh_curricular_idx"),
            # Índice de apoyo para la detección de posible duplicado.
            # Deliberadamente NO es UNIQUE: pueden existir designaciones legítimas iguales.
            models.Index(
                fields=[
                    "persona", "cueanexo", "tipo_personal", "ceic",
                    "sit_revista", "t_designacion", "f_desde",
                ],
                name="bnh_posible_dup_idx",
            ),
        ]
        constraints = [
            models.CheckConstraint(condition=models.Q(carga_horaria__gt=0), name="bnh_carga_positiva"),
            models.CheckConstraint(condition=models.Q(f_hasta__isnull=True) | models.Q(f_hasta__gte=models.F("f_desde")), name="bnh_cargo_fechas"),
            models.CheckConstraint(condition=models.Q(f_hasta_funciones__isnull=True) | models.Q(f_hasta_funciones__gte=models.F("f_desde_funciones")), name="bnh_funcion_fechas"),
            models.CheckConstraint(
                condition=models.Q(estado__in=["ACTIVO", "INACTIVO"]),
                name="bnh_actividad_estado_valido",
            ),
            models.CheckConstraint(
                condition=models.Q(validacion__in=["BORRADOR", "VALIDADO", "OBSERVADO"]),
                name="bnh_validacion_valida",
            ),
            models.CheckConstraint(
                condition=models.Q(version__gte=1),
                name="bnh_actividad_version_positiva",
            ),
            models.CheckConstraint(
                condition=models.Q(puesto_consecutivo__gte=1),
                name="bnh_puesto_consecutivo_positivo",
            ),
            models.UniqueConstraint(
                fields=["id_puesto"],
                name="bnh_id_puesto_unico",
            ),
            models.UniqueConstraint(
                fields=["puesto_base", "puesto_consecutivo"],
                name="bnh_puesto_base_consecutivo_unico",
            ),
        ]

    def clean(self):
        errors = {}
        tipo_personal_codigo = self.tipo_personal_id
        es_no_docente = tipo_personal_codigo == 2

        if not re.fullmatch(r"[0-9]{9}", str(self.cueanexo or "")):
            errors["cueanexo"] = "Ingrese los nueve dígitos del CUEANEXO."

        for start, end in (("f_desde", "f_hasta"), ("f_desde_funciones", "f_hasta_funciones")):
            desde, hasta = getattr(self, start), getattr(self, end)
            if desde and hasta and hasta < desde:
                errors[end] = "La fecha hasta debe ser igual o posterior a desde."

        if self.f_desde and self.f_desde_funciones and self.f_desde_funciones < self.f_desde:
            errors["f_desde_funciones"] = "Las funciones deben comenzar dentro del período del cargo."

        if self.f_hasta:
            if self.f_desde_funciones and self.f_desde_funciones > self.f_hasta:
                errors["f_desde_funciones"] = "Las funciones deben comenzar dentro del período del cargo."
            if not self.f_hasta_funciones or self.f_hasta_funciones > self.f_hasta:
                errors["f_hasta_funciones"] = "Indique un fin de funciones dentro del período del cargo."

        if self.carga_horaria is not None and self.carga_horaria <= 0:
            errors["carga_horaria"] = "La carga horaria debe ser positiva."

        # ----------------------------------------------------
        # CONDICIÓN DE ACTIVIDAD
        # ----------------------------------------------------
        if not self.cond_actividad_id:
            errors["cond_actividad"] = "Seleccione la condición de actividad."
        elif self.tipo_personal_id and self.sit_revista_id:
            if not CondicionActividadNombre.objects.filter(
                pk=self.cond_actividad_id,
                t_personal=self.tipo_personal_id,
                sit_rev=self.sit_revista_id,
            ).exists():
                errors["cond_actividad"] = (
                    "La condición de actividad no corresponde al tipo de personal "
                    "y situación de revista seleccionados."
                )

        if self.estado == "INACTIVO" and not self.f_hasta:
            errors["f_hasta"] = "Indique la fecha de finalización."

        # ----------------------------------------------------
        # CIRCUITO CARGO / CEIC: LÓGICA ANTERIOR INTACTA
        # ----------------------------------------------------
        from .domain.catalogs import (
            activity_catalogs,
            available_levels,
            curricular_catalogs,
            titulacion_source,
            valid_titulacion,
        )

        if (
            es_no_docente
            and self.ceic_id
            and not (1023 <= self.ceic.c_niv <= 1025)
        ):
            errors["ceic"] = (
                "Para personal no docente el Cargo / CEIC debe corresponder "
                "a c_niv 1023, 1024 o 1025."
            )

        if self.modalidad_id and self.niveles_id:
            if not available_levels(self.modalidad_id).filter(pk=self.niveles_id).exists():
                errors["niveles"] = "El nivel no pertenece a la modalidad del cargo seleccionada."

            ceic, _, _ = activity_catalogs(
                self.modalidad_id,
                self.niveles_id,
                tipo_personal=tipo_personal_codigo,
            )
            if self.ceic_id and not ceic.filter(pk=self.ceic_id).exists():
                errors["ceic"] = "El Cargo / CEIC no corresponde a la modalidad y nivel del cargo."

        # ----------------------------------------------------
        # CIRCUITO CURRICULAR NUEVO
        # ----------------------------------------------------
        if es_no_docente:
            if any((
                self.modalidad_curricular_id,
                self.nivel_curricular_id,
                self.titulacion,
                self.espacio_curricular_id,
                self.grado_anio_id,
                self.secciones_id,
            )):
                errors["tipo_personal"] = (
                    "Para personal no docente no corresponden modalidad/nivel curricular, "
                    "titulación, espacio curricular, grado/año ni sección."
                )
        else:
            if not self.modalidad_curricular_id:
                errors["modalidad_curricular"] = "Seleccione la modalidad curricular."
            if not self.nivel_curricular_id:
                errors["nivel_curricular"] = "Seleccione el nivel curricular."

            if self.modalidad_curricular_id and self.nivel_curricular_id:
                catalogs = curricular_catalogs(
                    self.modalidad_curricular_id,
                    self.nivel_curricular_id,
                    self.titulacion,
                    tipo_personal=tipo_personal_codigo,
                )
                if not catalogs["niveles"].filter(pk=self.nivel_curricular_id).exists():
                    errors["nivel_curricular"] = (
                        "El nivel curricular no pertenece a la modalidad curricular seleccionada."
                    )

                expected_source = titulacion_source(
                    self.modalidad_curricular_id, self.nivel_curricular_id
                )
                if expected_source:
                    if not self.titulacion:
                        errors["titulacion"] = "Seleccione una titulación."
                    elif not valid_titulacion(
                        self.modalidad_curricular_id,
                        self.nivel_curricular_id,
                        self.titulacion,
                        self.titulacion_fuente or expected_source,
                    ):
                        errors["titulacion"] = (
                            "La titulación no corresponde a la modalidad y nivel curricular seleccionados."
                        )
                    if self.titulacion_fuente and self.titulacion_fuente != expected_source:
                        errors["titulacion"] = "La fuente de la titulación no corresponde al catálogo seleccionado."
                elif self.titulacion:
                    errors["titulacion"] = "El nivel seleccionado no tiene catálogo de titulaciones configurado."

                if self.espacio_curricular_id:
                    if not self.titulacion:
                        errors["espacio_curricular"] = "Seleccione primero una titulación."
                    elif not catalogs["espacios"].filter(pk=self.espacio_curricular_id).exists():
                        errors["espacio_curricular"] = (
                            "El espacio curricular no corresponde a la titulación seleccionada."
                        )

                if self.grado_anio_id and not catalogs["grados"].filter(pk=self.grado_anio_id).exists():
                    errors["grado_anio"] = (
                        "El grado/año no corresponde a la modalidad y nivel curricular seleccionados."
                    )

                if self.secciones_id and not catalogs["secciones"].filter(pk=self.secciones_id).exists():
                    errors["secciones"] = (
                        "La sección no corresponde a la modalidad y nivel curricular seleccionados."
                    )

        if errors:
            raise ValidationError(errors)

    @property
    def es_no_docente(self):
        return self.tipo_personal_id == 2

    @property
    def tipo_personal_descripcion(self):
        return str(self.tipo_personal) if self.tipo_personal_id else ""

    @property
    def titulacion_descripcion(self):
        from .domain.catalogs import titulacion_label
        return titulacion_label(self.titulacion_fuente, self.titulacion)

    def normalize(self):
        self.cueanexo = str(self.cueanexo or "").strip()


################################
# SECUENCIA DE ID_PUESTO
################################
class PuestoSecuencia(models.Model):
    puesto_base = models.CharField(max_length=160, primary_key=True)
    ultimo_consecutivo = models.PositiveIntegerField(default=0)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "puesto_secuencia"
        verbose_name = "Secuencia de puesto"
        verbose_name_plural = "Secuencias de puestos"

    def __str__(self):
        return f"{self.puesto_base} -> {self.ultimo_consecutivo}"


################################
# ACTIVIDAD INTERMEDIA
################################
class ActividadSede(models.Model):
    actividad = models.ForeignKey(RegistroActividades, on_delete=models.CASCADE)
    cueanexo = models.CharField(max_length=9, db_index=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["actividad", "cueanexo"],
                name="bnh_actividad_sede_unica",
            )
        ]
    
    def __str__(self):
        return f"{self.actividad_id} - {self.cueanexo}"
        

################################
# HORARIOS ACTIVIDAD
################################
class HorarioActividad(models.Model):
    
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, db_index=True)
    
    actividad_sede = models.ForeignKey(
        ActividadSede,
        on_delete=models.CASCADE,
        related_name="horarios"
    )

    DIAS = [
        ("LUNES", "Lunes"),
        ("MARTES", "Martes"),
        ("MIERCOLES", "Miércoles"),
        ("JUEVES", "Jueves"),
        ("VIERNES", "Viernes"),
    ]

    dia = models.CharField(
        max_length=15,
        choices=DIAS
    )

    hora_desde = models.TimeField()

    hora_hasta = models.TimeField()

    class Meta:
        db_table = "horarios_actividad"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(hora_hasta__gt=models.F("hora_desde")),
                name="bnh_horario_orden",
            ),
            models.UniqueConstraint(
                fields=["actividad_sede", "dia", "hora_desde", "hora_hasta"],
                name="bnh_horario_unico",
            ),
        ]


    def __str__(self):
        return f"{self.dia} {self.hora_desde}-{self.hora_hasta}"

class AccesoRegional(AuditoriaModel):
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    region = models.CharField(max_length=100, help_text="Valor exacto de region_loc en el padrón.")
    activo = models.BooleanField(default=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["usuario", "region"], name="bnh_usuario_region_unico")]

    def __str__(self):
        return f"{self.usuario_id} / {self.region}"


class EventoAuditoria(models.Model):
    fecha = models.DateTimeField(auto_now_add=True, db_index=True)
    operacion_id = models.UUIDField(null=True, blank=True, db_index=True)
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    entidad = models.CharField(max_length=40)
    objeto_id = models.PositiveBigIntegerField()
    cueanexo = models.CharField(max_length=9, blank=True, db_index=True)
    accion = models.CharField(max_length=30)
    motivo = models.TextField(blank=True)
    antes = models.JSONField(default=dict)
    despues = models.JSONField(default=dict)

    class Meta:
        ordering = ["-fecha", "-pk"]
        indexes = [
            models.Index(fields=["entidad", "objeto_id", "-fecha"], name="bnh_audit_obj_idx"),
            models.Index(fields=["cueanexo", "-fecha"], name="bnh_audit_cue_idx"),
        ]


class PofTipo(models.Model):
    c_pof=models.SmallIntegerField(null=False, blank=False)
    descrip_pof=models.CharField(max_length=255)
    
    class Meta:
        verbose_name='Tipo Pof'
        verbose_name_plural='Tipos Pof'
        db_table='tipo_pof'

class NivelServicioTipo(models.Model):
    c_nivel=models.SmallIntegerField(primary_key=True, null=False, blank=False)
    descripcion=models.CharField(max_length=255)
    c_modalidad1=models.SmallIntegerField(null=False, blank=False)

    class Meta:
        verbose_name='Nivel Servicio Tipo'
        verbose_name_plural='Niveles Servicio Tipo'
        db_table='nivel_servicio_tipo'
        ordering=['c_modalidad1', 'c_nivel']

    def __str__(self):
        return self.descripcion

class ModalidadTipo(models.Model):
    c_modalidad1=models.SmallIntegerField(null=False, blank=False)
    descripcion=models.CharField(max_length=255)
    orden=models.SmallIntegerField(null=False, blank=False)
    
    
    class Meta:
        verbose_name='Modalidad Tipo'
        verbose_name_plural='Modalidades Tipo'
        db_table='modalidad1_tipo'
        ordering=['orden', 'descripcion']

    def __str__(self):
        return self.descripcion



class TitulacionNombre(models.Model):
    id_nombre_titulacion=models.IntegerField(null=False, blank=False)
    id_titulacion=models.IntegerField(null=False, blank=False)
    descripcion_adicional=models.CharField(max_length=255)
    nombre=models.CharField(max_length=255)
    c_nivel_servicio=models.SmallIntegerField(null=False, blank=False)
    c_modalidad1=models.SmallIntegerField(null=False, blank=False)
    class Meta:
        verbose_name='Titulacion Nombre'
        verbose_name_plural='Titulaciones Nombre'
        db_table='titulacion_nombre'

    def __str__(self):
        return self.nombre


class EspacioCurricularNombre(models.Model):
    id_espacio_curricular=models.BigIntegerField(null=False, blank=False)
    id_titulacion=models.IntegerField(null=False, blank=False)
    id_nombre_espacio_curricular=models.IntegerField(null=False, blank=False)
    nombre=models.CharField(max_length=255)
    class Meta:
        verbose_name='Espacio Curricular Nombre'
        verbose_name_plural='Espacios Curriculares Nombres'
        db_table='espacio_curricular_nombre'

    def __str__(self):
        return self.nombre


class TitulacionSuperior(models.Model):
    id_titulacion=models.IntegerField(null=False, blank=False)
    c_nivel_servicio=models.SmallIntegerField(null=False, blank=False)
    c_modalidad1=models.SmallIntegerField(null=False, blank=False)
    descripcion=models.CharField(max_length=255, unique=True)
    class Meta:
        verbose_name='Titulacion Superior'
        verbose_name_plural='Titulaciones Superior'
        db_table='titulacion_superior'

    def __str__(self):
        return self.descripcion


class TitulacionFP(models.Model):
    id_titulacion=models.IntegerField(null=False, blank=False)
    c_nivel_servicio=models.SmallIntegerField(null=False, blank=False)
    c_modalidad1=models.SmallIntegerField(null=False, blank=False)
    descripcion=models.CharField(max_length=255, unique=True)
    class Meta:
        verbose_name='Titulacion FP'
        verbose_name_plural='Titulaciones FP'
        db_table='titulacion_fp'


class CondicionActividadNombre(models.Model):
    c_nomen = models.CharField(max_length=10, null=False, blank=False)
    encuadre = models.CharField(max_length=50, null=False, blank=False)
    sit_rev = models.SmallIntegerField(null=False, blank=False)
    c_homo_sit_rev = models.SmallIntegerField(null=False, blank=False)
    c_homo_c_act = models.SmallIntegerField(null=False, blank=False)
    denominacion = models.CharField(max_length=255)
    t_personal = models.SmallIntegerField(null=False, blank=False)

    class Meta:
        verbose_name = 'Condicion Actividad Nombre'
        verbose_name_plural = 'Condiciones Actividad Nombres'
        db_table = 'condicion_actividad_nombre'
        ordering = ('denominacion', 'c_nomen', 'pk')
        indexes = [
            models.Index(
                fields=['t_personal', 'sit_rev'],
                name='bnh_cond_tipo_sit_idx',
            ),
        ]

    def __str__(self):
        return self.denominacion
        


class TipoPersonal(models.Model):
    c_tpersonal = models.SmallIntegerField(null=False, blank=False, unique=True)
    descripcion = models.CharField(max_length=50)

    class Meta:
        verbose_name = 'Tipo Personal'
        verbose_name_plural = 'Tipos Personales'
        db_table = 'tipo_personal'
        ordering = ('c_tpersonal',)

    def __str__(self):
        return self.descripcion

    @property
    def es_no_docente(self):
        return self.c_tpersonal == 2

class RevisionCatalogos(models.Model):
    """Versión global de catálogos usados por formularios operativos BNH."""

    id = models.PositiveSmallIntegerField(primary_key=True, default=1, editable=False)
    version = models.PositiveBigIntegerField(default=1)
    actualizado_en = models.DateTimeField(auto_now=True)
    actualizado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )

    class Meta:
        db_table = "bnh_revision_catalogos"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(version__gte=1),
                name="bnh_catalog_version_positiva",
            )
        ]

    @classmethod
    def current_version(cls):
        # Lectura pura: nunca se escribe durante un GET/formulario.
        obj = cls.objects.filter(pk=1).only("version").first()
        return obj.version if obj else 1

    def __str__(self):
        return f"Catálogos BNH v{self.version}"
