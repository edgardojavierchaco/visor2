# ============================================================
# IMPORTS BASE Y DEPENDENCIAS DE BASE DE DATOS
# ============================================================
# Este archivo define modelos propios del módulo de alumnos, sin
# tocar los datos maestros. En su lugar, reutiliza modelos
# ya existentes de otros módulos del proyecto.
#
# Se usan las apps:
# 	bnhpersonas
# 	especial
#
# ============================================================
import re
from django.db import models
from django.core.exceptions import ValidationError

from apps.bnhpersonas.models import (
    Personas,
    DocumentoTipo,
    Provincias,
    Localidades,
    Nacionalidad,
    Pais,
    Sexo,
    RelacionParentesco,
    TipoPlanesSociales,
    NivelFormacion,
    TipoOS,
    TipoComunidadOriginaria,
    TipoLenguaOriginaria,
    validar_cuil,
    TipoDiscapacidad,
)

# ============================================================
# MODELO PRINCIPAL DE ALUMNOS
# ============================================================
# Este bloque define la tabla propia "alumnos".
# Los datos del alumno se guardan en esta tabla, no en la tabla
# "personas" del módulo bnhpersonas.
#
# La función bnh_max_length() solo toma el tamaño máximo de campos
# ya existentes en Personas, por ejemplo apellido y nombre, para
# mantener consistencia de longitudes. No crea ni modifica registros
# en Personas.
#
# Los ForeignKey hacia DocumentoTipo, Sexo, Provincias, Pais,
# Localidades y AreaConocimiento no copian datos de esas tablas.
# Solo guardan en "alumnos" el identificador del registro relacionado.
#
# ============================================================
def bnh_max_length(modelo, campo):
    return modelo._meta.get_field(campo).max_length

ESTADO_ACTIVO_CHOICES = [
    ("ACTIVO", "Activo"),
    ("INACTIVO", "Inactivo"),
]



class Alumno(models.Model):
    """Modelo que representa a un alumno registrado en la base nacional homologada. 
    Este modelo es referenciado en el modelo Parental, ObraSocial, Discapacidad y PlanesSociales."""
      
    id = models.BigAutoField(primary_key=True)
    apellidos = models.CharField(max_length=bnh_max_length(Personas, "apellido"))
    nombres = models.CharField(max_length=bnh_max_length(Personas, "nombre"))
    tipo_doc = models.ForeignKey(
        DocumentoTipo, 
        on_delete=models.PROTECT
        )
    nro_doc = models.CharField(max_length=20, unique=True, db_index=True)
    cuil = models.CharField(
        max_length=11,
        null=True,
        blank=True,
        db_index=True,
    )
    fecha_nacimiento = models.DateField()
    sexo = models.ForeignKey(Sexo, on_delete=models.PROTECT)
    lugar_nacimiento = models.CharField(max_length=100)
    prov_nacimiento = models.ForeignKey(
        Provincias,
        on_delete=models.PROTECT,
        db_column="prov_nacimiento",
        related_name="alumnos_provincia_nacimiento",
    )
    pais_nacimiento = models.ForeignKey(
        Pais,
        on_delete=models.PROTECT,
        db_column="pais_nacimiento",
        related_name="alumnos_pais_nacimiento",
    )
    lugar_residencia = models.CharField(max_length=150)
    prov_residencia = models.ForeignKey(
        Provincias,
        on_delete=models.PROTECT,
        db_column="prov_residencia",
        related_name="alumnos_provincia_residencia",
    )
    pais_residencia = models.ForeignKey(
        Pais,
        on_delete=models.PROTECT,
        db_column="pais_residencia",
        related_name="alumnos_pais_residencia",
    )
    loc_residencia = models.ForeignKey(
        Localidades,
        on_delete=models.PROTECT,
        db_column="loc_residencia",
        related_name="alumnos_localidad_residencia",
    )
    est_civil = models.CharField(max_length=20)
    pueblo_indigena = models.ForeignKey(
        TipoComunidadOriginaria,
        on_delete=models.PROTECT,
        db_column="cd_pueblo_indigena",
        related_name="alumnos",
    )
    discapacidad = models.ForeignKey(
        TipoDiscapacidad,
        on_delete=models.PROTECT,
        db_column="cd_discapacidad",
        related_name="alumnos",
    )
    nivel_formacion = models.ForeignKey(
    NivelFormacion,
    on_delete=models.PROTECT,
    db_column="c_nivel_formacion",
    related_name="alumnos",
		)
    tel = models.CharField(max_length=20)
    celular = models.CharField(max_length=20)
    email = models.CharField(max_length=150, blank=True)
    talla = models.DecimalField(max_digits=5, decimal_places=2)
    peso = models.DecimalField(max_digits=5, decimal_places=2)
    
    fecha_registro = models.DateTimeField(auto_now_add=True)
    
    estado = models.CharField(
        max_length=10,
        choices=ESTADO_ACTIVO_CHOICES,
        default="ACTIVO",
        db_index=True,
    )
    
    observaciones = models.TextField(blank=True)

    def clean(self):
        super().clean()

        if self.nro_doc:
            self.nro_doc = self.nro_doc.strip().upper()

        if self.tipo_doc_id == 1:
            self.nro_doc = validar_dni(self.nro_doc)

        if self.cuil:
            self.cuil = re.sub(r"\D", "", self.cuil)
            validar_cuil(self.cuil)


    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
        
    def __str__(self):
        return f"{self.apellidos}, {self.nombres} - {self.nro_doc}"

    class Meta:
        db_table = '"bnh_alumno"."alumnos"'
        verbose_name = "Alumno"
        verbose_name_plural = "Alumnos"

        indexes = [
            models.Index(fields=["nro_doc"], name="idx_alumnos_nro_doc"),
            models.Index(fields=["email"], name="idx_alumnos_email"),
        ]


# ============================================================
# OBRA SOCIAL DEL ALUMNO
# ============================================================
# Este modelo define la tabla "obra_social".
# No representa al alumno completo, sino una obra social asociada
# a un alumno existente.
#
# La relación con Alumno se guarda mediante id_alumno.
# Un alumno puede tener una o varias obras sociales relacionadas.
#
# related_name="obras_sociales" permite acceder desde un alumno a
# sus obras sociales con:
# alumno.obras_sociales.all()
#
# fecha_inicio indica desde cuándo posee la obra social.
# fecha_fin puede quedar vacía para representar una obra social
# vigente o sin fecha de finalización cargada.
# ============================================================
   
class ObraSocial(models.Model):
    """Modelo que representa la obra social de un alumno registrado en la base nacional homologada."""
    
    id = models.BigAutoField(primary_key=True)

    id_alumno = models.ForeignKey(
        Alumno,
        on_delete=models.PROTECT,
        db_column="id_alumno",
        related_name="obras_sociales",
    )

    tipo_obra = models.ForeignKey(
        TipoOS,
        on_delete=models.PROTECT,
        db_column="tipo_obra",
        related_name="obras_sociales",
    )

    nombre_obra = models.CharField(max_length=150)
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField(null=True, blank=True)
    descripcion = models.TextField(blank=True)
    estado = models.CharField(max_length=20)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = '"bnh_alumno"."obra_social"'
        verbose_name = "Obra social"
        verbose_name_plural = "Obras sociales"
        indexes = [
            models.Index(fields=["id_alumno"], name="idx_obra_social_alumno"),
        ]

    def __str__(self):
        return f"{self.nombre_obra} - {self.id_alumno}"
# ============================================================
# TUTOR / RESPONSABLE DEL ALUMNO
# ============================================================
# Este modelo define la tabla "parental".
# No representa al alumno principal, sino a una persona responsable
# o tutora vinculada a un alumno.
#
# La relación con Alumno se guarda mediante la columna id_alumno.
# Un alumno puede tener uno o varios parentales asociados, por ejemplo
# madre, padre, tutor legal o responsable.
#
# Los ForeignKey hacia parentesco, tipo de documento, nacionalidad,
# país, provincia y localidad deberían usar PROTECT porque son
# catálogos. Borrar un catálogo no debería borrar registros parentales.
# ============================================================

class Parental(models.Model):
    """Modelo que representa la relación entre el tutor y el alumno."""
    
    id = models.BigAutoField(primary_key=True)
    id_alumno = models.ForeignKey(
        Alumno,
        on_delete=models.PROTECT,
        db_column="id_alumno",
        related_name="parentales",
    )

    id_tutor = models.ForeignKey(
        'Tutor',
        on_delete=models.PROTECT,
        db_column="id_tutor",
        related_name="parentales",
    )
    
    parentesco = models.ForeignKey(
        RelacionParentesco,
        on_delete=models.PROTECT,
        db_column="id_parentesco",
        related_name="parentales",
    )

    activo = models.BooleanField(default=True)
    fecha_desde = models.DateField()
    fecha_hasta = models.DateField(null=True, blank=True)
    observaciones = models.TextField(blank=True)
    
    class Meta:
        db_table = '"bnh_alumno"."parental"'
        verbose_name = "Parental"
        verbose_name_plural = "Parentales"
        indexes = [
            models.Index(fields=["id_alumno"], name="idx_parental_alumno"),
            models.Index(fields=["id_tutor"], name="idx_parental_tutor"),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["id_alumno", "id_tutor"],
                name="uq_parental_alumno_tutor",
            )
        ]

    def __str__(self):
        return f"{self.id_tutor} - {self.parentesco}"

# ===========================================================
# ============================================================
# DISCAPACIDADES DEL ALUMNO
# ============================================================
# Este modelo define la tabla "discapacidad".
# No es el catálogo de discapacidades, sino la relación entre un
# alumno y una discapacidad registrada.
#
# La relación con Alumno se guarda mediante la columna id_alumno.
# Un alumno puede tener cero, una o varias discapacidades asociadas.
#
# La relación con DiscapacidadListado usa PROTECT porque ese modelo
# funciona como catálogo. Borrar una discapacidad del catálogo no
# debería borrar registros históricos de alumnos.
# ============================================================
class Discapacidad(models.Model):
    """Modelo que representa las discapacidades de un alumno registrado en la base nacional homologada, si las tuviera."""
    
    id = models.BigAutoField(primary_key=True)
    id_alumno = models.ForeignKey(
        Alumno,
        on_delete=models.PROTECT,
        db_column="id_alumno",
        related_name="discapacidades",
    )
    id_discapacidad = models.ForeignKey(
        TipoDiscapacidad,
        on_delete=models.PROTECT,
        db_column="id_discapacidad",
        related_name="alumnos_discapacidad",
    )
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField(null=True, blank=True)
    porcentaje = models.DecimalField(max_digits=5, decimal_places=2)
    observaciones = models.TextField(blank=True)
    certificado_cud = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = '"bnh_alumno"."discapacidad"'
        verbose_name = "Discapacidad"
        verbose_name_plural = "Discapacidades"
        indexes = [
            models.Index(fields=["id_alumno"], name="idx_discapacidad_alumno"),
            models.Index(
                fields=["id_discapacidad", "id_alumno"],
                name="idx_discapacidad_alumno_tipo",
            ),
        ]

    def __str__(self):
        return f"{self.id_alumno} - {self.id_discapacidad}"

# ============================================================
# PLANES SOCIALES DEL ALUMNO
# ============================================================
# Este modelo define la tabla "planes_sociales".
# No representa al alumno completo, sino los beneficios o planes
# sociales asociados a un alumno determinado.
#
# La relación con Alumno se guarda mediante la columna id_alumno.
# Un alumno puede tener cero, uno o varios planes sociales asociados.
#
# La relación con BeneficioSocial usa PROTECT porque ese modelo funciona
# como catálogo. Borrar un beneficio del catálogo no debería borrar
# registros históricos de alumnos.
#
# ============================================================

class PlanesSociales(models.Model):
    """Modelo que representa los planes sociales de un alumno registrado en la base nacional homologada, si los tuviera."""
    
    id = models.BigAutoField(primary_key=True)
    id_alumno = models.ForeignKey(
        Alumno,
        on_delete=models.PROTECT,
        db_column="id_alumno",
        related_name="planes_sociales",
    )
   
    id_beneficio = models.ForeignKey(
        TipoPlanesSociales,
        on_delete=models.PROTECT,
        db_column="id_beneficio",
        related_name="planes_sociales",
    )
    descripcion = models.CharField(max_length=150)
    fecha_desde = models.DateField()
    fecha_hasta = models.DateField(null=True, blank=True)
    monto = models.DecimalField(max_digits=12, decimal_places=2)
    estado = models.CharField(max_length=20)
    observaciones = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = '"bnh_alumno"."planes_sociales"'
        verbose_name = "Plan social"
        verbose_name_plural = "Planes sociales"
        indexes = [
            models.Index(fields=["id_alumno"], name="idx_planes_alumno"),
        ]

    def __str__(self):
        return f"{self.id_alumno} - {self.id_beneficio}"


      
# -----------------------------
      
class Tutor(models.Model):
    """Modelo para representar a un tutor con su propio registro, ya que no está en bnhpersonas.
    Se vincula con Parental y permite usar los datos del tutor para varios alumnos."""
      
    id = models.BigAutoField(primary_key=True)
    cuil_tutor = models.CharField(max_length=20, unique=True, db_index=True)
    apellidos = models.CharField(max_length=bnh_max_length(Personas, "apellido"))
    nombres = models.CharField(max_length=bnh_max_length(Personas, "nombre"))
    tipo_doc = models.ForeignKey(DocumentoTipo, on_delete=models.PROTECT)
    nro_doc = models.CharField(max_length=20, unique=True, db_index=True)
    fecha_nac = models.DateField()
    nacionalidad = models.ForeignKey(Nacionalidad, on_delete=models.PROTECT)
    pais_nac = models.ForeignKey(
        Pais,
        on_delete=models.PROTECT,
        db_column="pais_nac",
        related_name="tutores_pais_nacimiento",
    )
    ocupacion = models.CharField(max_length=100)
    fecha_actualiza = models.DateField(auto_now=True)
    prov_resid = models.ForeignKey(
        Provincias,
        on_delete=models.PROTECT,
        db_column="prov_resid",
        related_name="tutores_provincia_residencia",
    )
    loc_resid = models.ForeignKey(
        Localidades,
        on_delete=models.PROTECT,
        db_column="loc_resid",
        related_name="tutores_localidad_residencia",
    )

    cod_postal = models.CharField(max_length=20)
    calle = models.CharField(max_length=150)
    nro = models.CharField(max_length=20)
    piso = models.CharField(max_length=10, blank=True)
    dpto = models.CharField(max_length=10, blank=True)
    mail = models.EmailField(max_length=150)
    tel = models.CharField(max_length=20)
    celular = models.CharField(max_length=20)
    
    estado = models.CharField(
        max_length=10,
        choices=ESTADO_ACTIVO_CHOICES,
        default="ACTIVO",
        db_index=True,
    )

    class Meta:
        db_table = '"bnh_alumno"."tutores"'
        verbose_name = "Tutor"
        verbose_name_plural = "Tutores"
        indexes = [
            models.Index(fields=["cuil_tutor"], name="idx_tutores_cuil"),
            models.Index(fields=["nro_doc"], name="idx_tutores_nro_doc"),
        ]

    def __str__(self):
        return f"{self.apellidos}, {self.nombres} - {self.nro_doc}"
      
      
############################
# FUNCIONES DE VALIDACION
############################
def validar_dni(dni):
    dni = str(dni or "").strip().upper()

    # Normaliza formatos comunes: 12.345.678, 12-345-678, 12 345 678
    dni = re.sub(r"[.\-\s]", "", dni)

    if not dni:
        raise ValidationError(
            "DNI inválido: es obligatorio cuando el tipo de documento es DNI."
        )

    if not re.fullmatch(r"\d{7,8}", dni):
        raise ValidationError(
            "DNI inválido: debe contener solo números y tener 7 u 8 dígitos."
        )

    return dni