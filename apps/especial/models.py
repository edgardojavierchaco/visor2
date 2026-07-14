# -*- coding: utf-8 -*-
import re
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import CharField, Func, Q, Value
from django.db.models.functions import Cast
from django.utils import timezone
from apps.bnhalumnos.models import Alumno

# ============================================================
# CONSTANTES DEL MODULO ESPECIAL
# ============================================================
ACRONIMO_ESPECIAL = "EEE"
LONGITUD_CUEANEXO = 9
PADRON_DB_ALIAS = "default" # TODO: Check if this should be 'padron' or 'default' (BNH uses 'padron' probably, but in `models.py` it's 'default'. I will leave it as is or check later)
ROLES_AUTORIZADOS_ESPECIAL = {
    "Administrador",
    "Director",
    "Director de Modalidad Especial",
}

# ============================================================
# MODELOS EXTERNOS / INTEGRACION (Sin cambios mayores, solo limpieza)
# ============================================================

class EspecialDocenteBnh(models.Model):
    """Modelo proxy para consultar personas en el esquema BNH."""
    cuil = models.CharField(max_length=11, primary_key=True)
    dni = models.CharField(max_length=20, blank=True, null=True)
    apellido = models.CharField(max_length=150, blank=True, null=True)
    nombre = models.CharField(max_length=150, blank=True, null=True)
    estado = models.CharField(max_length=30, blank=True, null=True)

    class Meta:
        managed = False
        db_table = '"bnh"."personas"'
        ordering = ["apellido", "nombre", "cuil"]

    @property
    def nombre_completo(self):
        apellidos = (self.apellido or "").strip()
        nombres = (self.nombre or "").strip()
        if apellidos and nombres:
            return f"{apellidos}, {nombres}"
        return apellidos or nombres
class EspecialPadronOferta(models.Model):
    """Modelo de integración Especial contra la vista de Padrón."""
    id = models.BigIntegerField(primary_key=True)
    cueanexo = models.CharField(max_length=9, blank=True, null=True)
    nom_est = models.TextField(blank=True, null=True)
    # ... (resto de campos igual que antes) ...
    padron_cueanexo = models.CharField(max_length=9, blank=True, null=True)
    acronimo = models.CharField(max_length=50, blank=True, null=True)
    oferta = models.TextField(blank=True, null=True)
    etiqueta = models.TextField(blank=True, null=True)
    nro_est = models.TextField(blank=True, null=True)
    ambito = models.TextField(blank=True, null=True)
    sector = models.TextField(blank=True, null=True)
    region_loc = models.TextField(blank=True, null=True)
    ref_loc = models.TextField(blank=True, null=True)
    calle = models.TextField(blank=True, null=True)
    numero = models.TextField(blank=True, null=True)
    localidad = models.TextField(blank=True, null=True)
    departamento = models.TextField(blank=True, null=True)
    estado_loc = models.TextField(blank=True, null=True)
    est_oferta = models.TextField(blank=True, null=True)
    estado_est = models.TextField(blank=True, null=True)
    resploc_cuitcuil = models.TextField(blank=True, null=True)
    resploc_doc = models.TextField(blank=True, null=True)
    apellido_resp = models.TextField(blank=True, null=True)
    nombre_resp = models.TextField(blank=True, null=True)
    resploc_email = models.TextField(blank=True, null=True)
    resploc_telefono = models.TextField(blank=True, null=True)
    sup_tecnico = models.TextField(blank=True, null=True)
    email_suptecnico = models.TextField(blank=True, null=True)
    tel_suptecnico = models.TextField(blank=True, null=True)
    categoria = models.TextField(blank=True, null=True)
    cui_loc = models.TextField(blank=True, null=True)
    cua_loc = models.TextField(blank=True, null=True)
    cuof_loc = models.TextField(blank=True, null=True)
    jornada = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = "v_capa_unica_ofertas_ant"
        verbose_name = "Oferta Especial desde Padrón"
        verbose_name_plural = "Ofertas Especial desde Padrón"

    def __str__(self):
        cueanexo = self.cueanexo or ""
        nombre = self.nom_est or ""
        return f"{cueanexo} - {nombre}".strip(" -")

class EspecialRolUsuario(models.Model):
    id = models.BigIntegerField(primary_key=True)
    nombre = models.CharField(max_length=100, blank=True, null=True)
    class Meta:
        managed = False
        db_table = "usuarios_rol"
        verbose_name = "Rol de usuario Especial"
        verbose_name_plural = "Roles de usuario Especial"

class EspecialUsuarioPerfil(models.Model):
    id = models.BigIntegerField(primary_key=True)
    usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.DO_NOTHING,
        db_column="usuario_id",
        related_name="perfil_especial_integracion",
    )
    rol = models.ForeignKey(
        EspecialRolUsuario,
        on_delete=models.DO_NOTHING,
        db_column="rol_id",
        related_name="perfiles_especial_integracion",
    )
    class Meta:
        managed = False
        db_table = "usuarios_perfilusuario"
        verbose_name = "Perfil de usuario Especial"
        verbose_name_plural = "Perfiles de usuario Especial"

# ============================================================
# FUNCIONES DE NORMALIZACION Y ACCESO A PADRON
# ============================================================
def solo_digitos(valor):
    return re.sub(r"\D", "", str(valor or ""))

def normalizar_cueanexo(valor):
    cueanexo = solo_digitos(valor)
    if len(cueanexo) != LONGITUD_CUEANEXO:
        return ""
    return cueanexo

def normalizar_cuil_usuario(user):
    if not user or not getattr(user, "is_authenticated", False):
        return ""
    cuil = solo_digitos(getattr(user, "username", ""))
    if len(cuil) != 11:
        return ""
    return cuil

def get_escuelas_especiales_base_queryset():
    return (
        EspecialPadronOferta.objects.using(PADRON_DB_ALIAS)
        .filter(acronimo__iexact=ACRONIMO_ESPECIAL)
    )

def get_todas_las_escuelas_especiales():
    return get_escuelas_especiales_base_queryset().order_by("cueanexo")

def get_escuelas_especiales_por_cuil_responsable(user):
    cuil = normalizar_cuil_usuario(user)
    queryset = get_escuelas_especiales_base_queryset()
    if not cuil:
        return queryset.none()
    return (
        queryset
        .annotate(
            responsable_cuil_limpio=Func(
                Cast("resploc_cuitcuil", CharField()),
                Value(r"\D"),
                Value(""),
                Value("g"),
                function="REGEXP_REPLACE",
                output_field=CharField(),
            )
        )
        .filter(responsable_cuil_limpio=cuil)
        .order_by("cueanexo")
    )

def get_datos_establecimiento_especial(cueanexo):
    cueanexo = normalizar_cueanexo(cueanexo)
    if not cueanexo:
        return None
    return (
        get_escuelas_especiales_base_queryset()
        .filter(cueanexo=cueanexo)
        .order_by("cueanexo", "nom_est")
        .first()
    )

# ============================================================
# PERMISOS FUNCIONALES
# ============================================================
def obtener_rol_usuario_especial(user):
    if not user or not getattr(user, "is_authenticated", False):
        return None
    username = (getattr(user, "username", "") or "").strip()
    if not username:
        return None
    try:
        perfil = (
            EspecialUsuarioPerfil.objects.using(PADRON_DB_ALIAS)
            .select_related("rol")
            .get(usuario__username=username)
        )
    except EspecialUsuarioPerfil.DoesNotExist:
        return None
    rol_nombre = getattr(perfil.rol, "nombre", "") or ""
    return rol_nombre.strip() or None

def usuario_puede_ver_especial(user):
    rol = obtener_rol_usuario_especial(user)
    if not rol:
        return False
    return rol in ROLES_AUTORIZADOS_ESPECIAL

def usuario_es_admin_especial(user):
    return obtener_rol_usuario_especial(user) == "Administrador"

def get_escuelas_especiales_cargables_usuario(user):
    queryset = get_todas_las_escuelas_especiales()
    if not usuario_puede_ver_especial(user):
        return queryset.none()
    if usuario_es_admin_especial(user):
        return queryset
    return get_escuelas_especiales_por_cuil_responsable(user)

def get_cueanexos_cargables_usuario(user):
    cueanexos = []
    for cueanexo in (
        get_escuelas_especiales_cargables_usuario(user)
        .values_list("cueanexo", flat=True)
        .distinct()
    ):
        cueanexo_norm = normalizar_cueanexo(cueanexo)
        if cueanexo_norm and cueanexo_norm not in cueanexos:
            cueanexos.append(cueanexo_norm)
    return cueanexos

def usuario_puede_cargar_cueanexo(user, cueanexo):
    cueanexo = normalizar_cueanexo(cueanexo)
    if not cueanexo:
        return False
    return cueanexo in get_cueanexos_cargables_usuario(user)

# ============================================================
# MIXIN DE AUDITORIA
# ============================================================
class EspecialAuditoriaMixin(models.Model):
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)
    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        blank=True, null=True,
        related_name="%(app_label)s_%(class)s_creados",
    )
    actualizado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        blank=True, null=True,
        related_name="%(app_label)s_%(class)s_actualizados",
    )
    class Meta:
        abstract = True

# ============================================================
# CICLO LECTIVO
# ============================================================
class EspecialCiclo(EspecialAuditoriaMixin):
    anio = models.PositiveSmallIntegerField(
        unique=True,
        validators=[MinValueValidator(1900), MaxValueValidator(2100)],
    )
    descripcion = models.CharField(max_length=120, blank=True)
    fecha_inicio = models.DateField(blank=True, null=True)
    fecha_fin = models.DateField(blank=True, null=True)
    activo = models.BooleanField(default=True)
    actual = models.BooleanField(default=False)

    class Meta:
        db_table = "especial_ciclos"
        ordering = ["-anio"]
        verbose_name = "Ciclo Especial"
        verbose_name_plural = "Ciclos Especial"
        constraints = [
            models.UniqueConstraint(
                fields=["actual"],
                condition=Q(actual=True),
                name="uq_especial_ciclo_actual",
            ),
        ]

    def clean(self):
        if (
            self.fecha_inicio
            and self.fecha_fin
            and self.fecha_fin < self.fecha_inicio
        ):
            raise ValidationError({
                "fecha_fin": "La fecha de fin no puede ser anterior a la de inicio."
            })

    def __str__(self):
        return str(self.anio)

# ============================================================
# CATALOGOS OPERATIVOS ESPECIAL
# ============================================================
class CatalogoTipoEstructuraEspecial(models.Model):
    """Catálogo de tipos de estructura especial (CEAT, SEAT, SAI, CEFOL, etc.)."""
    cd_tipoestructuraespecial = models.IntegerField(primary_key=True)
    descripcion = models.CharField(max_length=100)

    class Meta:
        db_table = "catalogo_tipo_estructura_especial"
        verbose_name = "Tipo de estructura especial"
        verbose_name_plural = "Tipos de estructuras especiales"
    def __str__(self):
        return self.descripcion

class CatalogoTipoRangoEtario(models.Model):
    """Catálogo de rangos etarios (0 a 99 años)."""
    cd_tiporangoetario = models.IntegerField(primary_key=True)
    descripcion = models.CharField(max_length=100)
    class Meta:
        db_table = "catalogo_tipo_rango_etario"
        verbose_name = "Tipo de rango etario"
        verbose_name_plural = "Tipos de rangos etarios"
    def __str__(self):
        return self.descripcion

class SinoTipo(models.Model):
    """Modelo genérico para representar respuestas Si/No/Sin información."""
    cd_sino = models.IntegerField(primary_key=True)
    descripcion = models.CharField(max_length=100)
    class Meta:
        db_table = "sino_tipo"
        verbose_name = "Si/No/Sin info"
        verbose_name_plural = "Si/No/Sin info"
    def __str__(self):
        return self.descripcion

class seccion_tipo(models.Model):
    """Tipo de sección en la que cursa el alumno (Independiente, Múltiple, etc.)."""
    cd_tipo_seccion = models.IntegerField(primary_key=True)
    descripcion = models.CharField(max_length=100)
    class Meta:
        db_table = "seccion_tipo"
        verbose_name = "Tipo de sección"
        verbose_name_plural = "Tipos de sección"
    def __str__(self):
        return self.descripcion

class TurnoTipo(models.Model):
    """Turno en el que cursa el alumno (Mañana, Tarde, etc.)."""
    cd_turno = models.IntegerField(primary_key=True)
    descripcion = models.CharField(max_length=100)
    class Meta:
        db_table = "turno_tipo"
        verbose_name = "Turno"
        verbose_name_plural = "Turnos"
    def __str__(self):
        return self.descripcion

class ModalidadDictadoTipo(models.Model):
    """Modalidad de dictado del plan de estudios (Presencial, A distancia, etc.)."""
    cd_modalidad_dictado = models.IntegerField(primary_key=True)
    descripcion = models.CharField(max_length=100)
    class Meta:
        db_table = "modalidad_dictado_tipo"
        verbose_name = "Tipo de modalidad de cursado"
        verbose_name_plural = "Tipos de modalidad de cursado"
    def __str__(self):
        return self.descripcion

# ============================================================
# MODELOS PRINCIPALES (Adaptados a estilo CEF)
# ============================================================

class SeccionEspecial(EspecialAuditoriaMixin):
    """
    Sección/cursada en la que cursan los alumnos de educación especial.
    Equivalente a CefGrupo pero manteniendo la terminología de Sección.
    """
    class Estado(models.TextChoices):
        BORRADOR = "borrador", "Borrador"
        ACTIVO = "activo", "Activo"
        INACTIVO = "inactivo", "Inactivo"
        CERRADO = "cerrado", "Cerrado"

    id = models.BigAutoField(primary_key=True)
    cueanexo = models.CharField(max_length=9, db_index=True)
    
    cd_tipo_seccion = models.ForeignKey(
        seccion_tipo,
        on_delete=models.PROTECT,
        db_column="cd_tipo_seccion",
        related_name="secciones",
    )
    tipo_estructura_especial = models.ForeignKey(
        CatalogoTipoEstructuraEspecial,
        on_delete=models.PROTECT,
        db_column="cd_tipoestructuraespecial",
        related_name="secciones",
    )
    
    nombre_seccion = models.CharField(max_length=50)
    descripcion = models.TextField(max_length=255, blank=True, null=True)
    capacidad_total = models.PositiveIntegerField()
    
    ciclo = models.ForeignKey(
        EspecialCiclo,
        on_delete=models.PROTECT,
        related_name="secciones",
    )
    
    turno = models.ForeignKey(
        TurnoTipo,
        on_delete=models.PROTECT,
        db_column="cd_turno",
        related_name="secciones",
    )
    
    rango_etario = models.ForeignKey(
        CatalogoTipoRangoEtario,
        on_delete=models.PROTECT,
        db_column="cd_tiporangoetario",
        related_name="secciones",
    )
    
    modalidad = models.ForeignKey(
        ModalidadDictadoTipo,
        on_delete=models.PROTECT,
        db_column="cd_modalidad_dictado",
        related_name="secciones",
    )
    
    lugar_dictado = models.CharField(max_length=100, blank=True, null=True)
    estado = models.CharField(
        max_length=20,
        choices=Estado.choices,
        default=Estado.ACTIVO,
        db_index=True,
    )

    # Snapshots para histórico (estilo CEF)
    turno_nombre_snapshot = models.CharField(max_length=80, blank=True, editable=False)
    tipo_seccion_snapshot = models.CharField(max_length=100, blank=True, editable=False)
    estructura_snapshot = models.CharField(max_length=100, blank=True, editable=False)

    class Meta:
        db_table = "especial_seccion"
        verbose_name = "Sección de Educación Especial"
        verbose_name_plural = "Secciones de Educación Especial"
        constraints = [
            models.UniqueConstraint(
                fields=["cueanexo", "ciclo", "nombre_seccion", "cd_tipo_seccion"],
                name="uq_esp_sec_cue_cic_nom_tipo",
            ),
        ]
        indexes = [
            models.Index(fields=["cueanexo", "ciclo"], name="idx_esp_sec_cue_cic"),
            models.Index(fields=["cueanexo", "estado"], name="idx_esp_sec_cue_est"),
        ]

    def clean(self):
        errors = {}
        cueanexo_norm = normalizar_cueanexo(self.cueanexo)
        if not cueanexo_norm:
            errors["cueanexo"] = "CUE-Anexo inválido."
        else:
            self.cueanexo = cueanexo_norm
        
        if self.capacidad_total < 1:
            errors["capacidad_total"] = "La capacidad debe ser mayor a cero."
        
        if errors:
            raise ValidationError(errors)

    def actualizar_snapshots(self):
        """Actualiza los campos snapshot para conservar histórico si cambian los catálogos."""
        if self.turno_id:
            self.turno_nombre_snapshot = str(self.turno)
        if self.cd_tipo_seccion_id:
            self.tipo_seccion_snapshot = str(self.cd_tipo_seccion)
        if self.tipo_estructura_especial_id:
            self.estructura_snapshot = str(self.tipo_estructura_especial)

    def save(self, *args, **kwargs):
        self.actualizar_snapshots()
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.cueanexo} - {self.nombre_seccion} ({self.ciclo})"


class EspecialAlumnoBanco(EspecialAuditoriaMixin):
    """
    Banco de alumnos activos en el establecimiento para un ciclo determinado.
    Similar a CefAlumnoCef. Permite gestionar qué alumnos están disponibles 
    para ser inscritos en secciones.
    """
    class Estado(models.TextChoices):
        ACTIVO = "activo", "Activo"
        INACTIVO = "inactivo", "Inactivo"
        BAJA = "baja", "Baja"

    cueanexo = models.CharField(max_length=9, db_index=True)
    ciclo = models.ForeignKey(
        EspecialCiclo,
        on_delete=models.PROTECT,
        related_name="alumnos_banco_especial",
    )
    alumno = models.ForeignKey(
        Alumno,
        on_delete=models.PROTECT,
        related_name="bancos_especial",
    )
    estado = models.CharField(
        max_length=20,
        choices=Estado.choices,
        default=Estado.ACTIVO,
        db_index=True,
    )
    fecha_alta = models.DateField(default=timezone.localdate)
    fecha_baja = models.DateField(blank=True, null=True)
    motivo_baja = models.CharField(max_length=255, blank=True)
    
    # Snapshots
    alumno_nombre_snapshot = models.CharField(max_length=255, blank=True, editable=False)
    alumno_documento_snapshot = models.CharField(max_length=30, blank=True, editable=False)
    alumno_cuil_snapshot = models.CharField(max_length=11, blank=True, editable=False)
    observaciones = models.TextField(blank=True)

    class Meta:
        db_table = "especial_alumno_banco"
        verbose_name = "Alumno en Banco Especial"
        verbose_name_plural = "Alumnos en Banco Especial"
        constraints = [
            models.UniqueConstraint(
                fields=["cueanexo", "ciclo", "alumno"],
                condition=Q(estado="activo"),
                name="uq_esp_alumno_banco_act",
            ),
        ]
        indexes = [
            models.Index(fields=["cueanexo", "ciclo"], name="idx_esp_alum_banco_cic"),
            models.Index(fields=["alumno", "estado"], name="idx_esp_alum_banco_est"),
        ]

    def clean(self):
        errors = {}
        cueanexo_norm = normalizar_cueanexo(self.cueanexo)
        if not cueanexo_norm:
            errors["cueanexo"] = "CUE-Anexo inválido."
        else:
            self.cueanexo = cueanexo_norm

        if self.fecha_baja and self.fecha_baja < self.fecha_alta:
            errors["fecha_baja"] = "La fecha de baja no puede ser anterior a la de alta."
        
        if self.estado == self.Estado.BAJA and not self.fecha_baja:
            errors["fecha_baja"] = "Debe indicar fecha de baja cuando el estado es Baja."
            
        if self.estado != self.Estado.BAJA and self.motivo_baja:
            errors["motivo_baja"] = "Solo debe indicar motivo de baja cuando el estado es Baja."

        if errors:
            raise ValidationError(errors)

    def actualizar_snapshots_alumno(self):
        if not self.alumno_id:
            return
        apellidos = str(getattr(self.alumno, "apellidos", "") or "").strip()
        nombres = str(getattr(self.alumno, "nombres", "") or "").strip()
        if apellidos and nombres:
            self.alumno_nombre_snapshot = f"{apellidos}, {nombres}"
        else:
            self.alumno_nombre_snapshot = apellidos or nombres
        
        self.alumno_documento_snapshot = str(getattr(self.alumno, "nro_doc", "") or "")
        self.alumno_cuil_snapshot = solo_digitos(getattr(self.alumno, "cuil", "") or "")

    def save(self, *args, **kwargs):
        self.actualizar_snapshots_alumno()
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        alumno = self.alumno_nombre_snapshot or str(self.alumno_id)
        return f"{self.cueanexo} - {self.ciclo} - {alumno}"


class EspecialDocenteBanco(EspecialAuditoriaMixin):
    """
    Banco de docentes activos en el establecimiento para un ciclo determinado.
    Similar a CefDocenteCef.
    """
    class Estado(models.TextChoices):
        ACTIVO = "activo", "Activo"
        INACTIVO = "inactivo", "Inactivo"
        BAJA = "baja", "Baja"

    cueanexo = models.CharField(max_length=9, db_index=True)
    ciclo = models.ForeignKey(
        EspecialCiclo,
        on_delete=models.PROTECT,
        related_name="docentes_banco_especial",
    )
    docente_cuil = models.CharField(max_length=11, db_index=True)
    estado = models.CharField(
        max_length=20,
        choices=Estado.choices,
        default=Estado.ACTIVO,
        db_index=True,
    )
    fecha_alta = models.DateField(default=timezone.localdate)
    fecha_baja = models.DateField(blank=True, null=True)
    motivo_baja = models.CharField(max_length=255, blank=True)
    
    # Snapshots
    docente_nombre_snapshot = models.CharField(max_length=255, blank=True, editable=False)
    docente_dni_snapshot = models.CharField(max_length=20, blank=True, editable=False)
    observaciones = models.TextField(blank=True)

    class Meta:
        db_table = "especial_docente_banco"
        verbose_name = "Docente en Banco Especial"
        verbose_name_plural = "Docentes en Banco Especial"
        constraints = [
            models.UniqueConstraint(
                fields=["cueanexo", "ciclo", "docente_cuil"],
                condition=Q(estado="activo"),
                name="uq_esp_docente_banco_act",
            ),
        ]
        indexes = [
            models.Index(fields=["cueanexo", "ciclo"], name="idx_esp_doc_banco_cic"),
            models.Index(fields=["docente_cuil", "estado"], name="idx_esp_doc_banco_est"),
        ]

    def clean(self):
        errors = {}
        cueanexo_norm = normalizar_cueanexo(self.cueanexo)
        if not cueanexo_norm:
            errors["cueanexo"] = "CUE-Anexo inválido."
        else:
            self.cueanexo = cueanexo_norm
        
        docente_cuil_norm = solo_digitos(self.docente_cuil)
        if len(docente_cuil_norm) != 11:
            errors["docente_cuil"] = "El CUIL del docente debe tener 11 dígitos."
        else:
            self.docente_cuil = docente_cuil_norm

        if self.fecha_baja and self.fecha_baja < self.fecha_alta:
            errors["fecha_baja"] = "La fecha de baja no puede ser anterior a la de alta."
            
        if self.estado == self.Estado.BAJA and not self.fecha_baja:
            errors["fecha_baja"] = "Debe indicar fecha de baja cuando el estado es Baja."

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.docente_cuil = solo_digitos(self.docente_cuil)
        # Aquí podrías buscar datos del docente en bnhpersonas si quisieras llenar snapshots
        # Por simplicidad, asumimos que se llenan manualmente o vía otra vista
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        docente = self.docente_nombre_snapshot or self.docente_cuil
        return f"{self.cueanexo} - {self.ciclo} - {docente}"


class AlumnoSeccion(EspecialAuditoriaMixin):
    """
    Relación entre un alumno del banco y una sección de Educación Especial.
    Equivalente a CefInscripcion.
    """
    class Estado(models.TextChoices):
        ACTIVO = "activo", "Activo"
        INACTIVO = "inactivo", "Inactivo"
        BAJA = "baja", "Baja"

    id = models.BigAutoField(unique=True, primary_key=True)
    
    # Ya no vinculamos directo a Alumno, sino al registro del banco para trazabilidad
    # Pero para mantener compatibilidad con vistas antiguas, podemos mantener la FK a Alumno
    # o cambiarla. En CefInscripcion usan Alumno directo. Vamos a usar Alumno directo para simplificar
    # la consulta de datos personales, pero validando que esté en el banco.
    alumno = models.ForeignKey(
        Alumno,
        on_delete=models.PROTECT,
        related_name="secciones_especial",
    )
    
    seccion = models.ForeignKey(
        SeccionEspecial,
        on_delete=models.PROTECT,
        related_name="alumnos",
    )
    
    estado = models.CharField(
        max_length=20,
        choices=Estado.choices,
        default=Estado.ACTIVO,
        db_index=True,
    )
    fecha_inscripcion = models.DateField(default=timezone.localdate)
    fecha_baja = models.DateField(blank=True, null=True)
    motivo_baja = models.CharField(max_length=255, blank=True)
    observaciones = models.TextField(blank=True)

    class Meta:
        db_table = "especial_alumnoseccion"
        verbose_name = "Alumno de Educación Especial"
        verbose_name_plural = "Alumnos de Educación Especial"
        constraints = [
            models.UniqueConstraint(
                fields=["alumno", "seccion"],
                condition=Q(estado__in=["activo", "inactivo"]),
                name="uq_esp_alumno_seccion_abierta",
            ),
        ]
        indexes = [
            models.Index(fields=["estado"], name="idx_esp_alsec_est"),
            models.Index(fields=["alumno", "estado"], name="idx_esp_alsec_alum_est"),
            models.Index(fields=["seccion", "estado"], name="idx_esp_alsec_sec_est"),
        ]

    def clean(self):
        errors = {}
        if self.fecha_baja and self.fecha_baja < self.fecha_inscripcion:
            errors["fecha_baja"] = "La fecha de baja no puede ser anterior a la de inscripción."
        
        if self.estado == self.Estado.BAJA and not self.fecha_baja:
            errors["fecha_baja"] = "Debe indicar fecha de baja cuando el estado es Baja."
            
        if self.estado != self.Estado.BAJA and self.motivo_baja:
            errors["motivo_baja"] = "Solo debe indicar motivo de baja cuando el estado es Baja."

        # Validar que el alumno esté en el banco activo de esa escuela/ciclo
        if self.seccion_id and self.alumno_id:
            en_banco = EspecialAlumnoBanco.objects.filter(
                cueanexo=self.seccion.cueanexo,
                ciclo=self.seccion.ciclo,
                alumno=self.alumno,
                estado=EspecialAlumnoBanco.Estado.ACTIVO
            ).exists()
            if not en_banco:
                errors["alumno"] = "El alumno no se encuentra activo en el banco de este establecimiento y ciclo."

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return (
            f"{self.alumno.apellidos}, {self.alumno.nombres} "
            f"- {self.alumno.nro_doc} | {self.seccion.nombre_seccion}"
        )


class DocenteSeccion(EspecialAuditoriaMixin):
    """
    Relación entre un docente del banco y una sección de Educación Especial.
    Equivalente a CefDocenteGrupo.
    """
    class Rol(models.TextChoices):
        TITULAR = "titular", "Titular"
        SUPLENTE = "suplente", "Suplente"
        APOYO = "apoyo", "Apoyo"

    class Estado(models.TextChoices):
        ACTIVO = "activo", "Activo"
        INACTIVO = "inactivo", "Inactivo"
        BAJA = "baja", "Baja"

    grupo = models.ForeignKey(
        SeccionEspecial, # Usamos SeccionEspecial como 'grupo'
        on_delete=models.PROTECT,
        related_name="docentes",
    )
    docente_cuil = models.CharField(max_length=11, db_index=True)
    rol = models.CharField(
        max_length=20,
        choices=Rol.choices,
        db_index=True,
    )
    estado = models.CharField(
        max_length=20,
        choices=Estado.choices,
        default=Estado.ACTIVO,
        db_index=True,
    )
    fecha_desde = models.DateField(blank=True, null=True)
    fecha_hasta = models.DateField(blank=True, null=True)
    
    # Snapshots
    docente_nombre_snapshot = models.CharField(max_length=255, blank=True, editable=False)
    docente_dni_snapshot = models.CharField(max_length=20, blank=True, editable=False)
    observaciones = models.TextField(blank=True)

    class Meta:
        db_table = "especial_docente_seccion"
        verbose_name = "Docente de Sección Especial"
        verbose_name_plural = "Docentes de Secciones Especiales"
        constraints = [
            models.UniqueConstraint(
                fields=["grupo", "docente_cuil"],
                condition=Q(estado="activo"),
                name="uq_esp_doc_sec_cuil_act",
            ),
            models.UniqueConstraint(
                fields=["grupo", "rol"],
                condition=Q(estado="activo"),
                name="uq_esp_doc_sec_rol_act",
            ),
        ]
        indexes = [
            models.Index(fields=["docente_cuil", "estado"], name="idx_esp_doc_sec_cuil_est"),
            models.Index(fields=["grupo", "estado"], name="idx_esp_doc_sec_grp_est"),
        ]

    def clean(self):
        errors = {}
        docente_cuil_norm = solo_digitos(self.docente_cuil)
        if len(docente_cuil_norm) != 11:
            errors["docente_cuil"] = "El CUIL del docente debe tener 11 dígitos."
        else:
            self.docente_cuil = docente_cuil_norm

        if self.fecha_desde and self.fecha_hasta and self.fecha_hasta < self.fecha_desde:
            errors["fecha_hasta"] = "La fecha hasta no puede ser anterior a la fecha desde."
            
        if self.estado == self.Estado.BAJA and not self.fecha_hasta:
            errors["fecha_hasta"] = "Debe indicar fecha hasta cuando la asignación está en baja."

        # Validar que el docente esté en el banco activo
        if self.grupo_id and self.docente_cuil:
            en_banco = EspecialDocenteBanco.objects.filter(
                cueanexo=self.grupo.cueanexo,
                ciclo=self.grupo.ciclo,
                docente_cuil=self.docente_cuil,
                estado=EspecialDocenteBanco.Estado.ACTIVO
            ).exists()
            if not en_banco:
                errors["docente_cuil"] = "El docente no se encuentra activo en el banco de este establecimiento y ciclo."

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.docente_cuil = solo_digitos(self.docente_cuil)
        # Aquí podrías buscar datos del docente para llenar snapshots
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        docente = self.docente_nombre_snapshot or self.docente_cuil
        return f"{self.grupo} - {self.get_rol_display()} - {docente}"