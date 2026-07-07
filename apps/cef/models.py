# -*- coding: utf-8 -*-

import re

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import CharField, Func, Q, Value
from django.db.models.functions import Cast, Trim, Upper
from django.utils import timezone


# ============================================================
# CONSTANTES DEL MODULO CEF
# ============================================================

ACRONIMO_CEF = "CEF"
OFERTA_SERVICIOS_COMPLEMENTARIOS = "Común - Servicios complementarios"
LONGITUD_CUEANEXO = 9
PADRON_DB_ALIAS = "default"

ROLES_AUTORIZADOS_CEF = {
    "Administrador",
    "Director de Servicios Complementarios",
}

# ============================================================
# MODELOS EXTERNOS / INTEGRACION
# ============================================================
# Estos modelos NO son tablas propias de CEF.
# Sirven para consultar vistas/tablas existentes.
# Tienen managed=False: Django los conoce, pero no los crea ni modifica.
# ============================================================

class CefPadronOferta(models.Model):
    """
    Modelo de integracion CEF contra la vista de Padron.

    Fuente actual:
    v_capa_unica_ofertas_ant
    """

    id = models.BigIntegerField(primary_key=True)

    cueanexo = models.CharField(max_length=9, blank=True, null=True)
    nom_est = models.TextField(blank=True, null=True)
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
        verbose_name = "Oferta CEF desde Padron"
        verbose_name_plural = "Ofertas CEF desde Padron"

    def __str__(self):
        cueanexo = self.cueanexo or ""
        nombre = self.nom_est or ""
        return f"{cueanexo} - {nombre}".strip(" -")


class CefDocenteBnh(models.Model):
    """
    Modelo de consulta contra docentes/personas de BNH.
    """

    cuil = models.CharField(max_length=11, primary_key=True)
    dni = models.CharField(max_length=20, blank=True, null=True)
    apellido = models.CharField(max_length=150, blank=True, null=True)
    nombre = models.CharField(max_length=150, blank=True, null=True)
    estado = models.CharField(max_length=30, blank=True, null=True)

    class Meta:
        managed = False
        db_table = '"bnh"."personas"'
        ordering = ["apellido", "nombre", "cuil"]
        verbose_name = "Docente BNH"
        verbose_name_plural = "Docentes BNH"

    @property
    def nombre_completo(self):
        apellido = (self.apellido or "").strip()
        nombre = (self.nombre or "").strip()

        if apellido and nombre:
            return f"{apellido}, {nombre}"

        return apellido or nombre or ""

    def __str__(self):
        nombre = self.nombre_completo

        if nombre:
            return f"{nombre} - {self.cuil}"

        return self.cuil or ""


class CefRolUsuario(models.Model):
    """
    Rol tomado desde las tablas compartidas de usuarios.
    """

    id = models.BigIntegerField(primary_key=True)
    nombre = models.CharField(max_length=100, blank=True, null=True)

    class Meta:
        managed = False
        db_table = "usuarios_rol"
        verbose_name = "Rol de usuario CEF"
        verbose_name_plural = "Roles de usuario CEF"

    def __str__(self):
        return self.nombre or ""


class CefUsuarioPerfil(models.Model):
    """
    Perfil externo que vincula usuario autenticado con rol funcional.
    """

    id = models.BigIntegerField(primary_key=True)

    usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.DO_NOTHING,
        db_column="usuario_id",
        related_name="perfil_cef_integracion",
    )

    rol = models.ForeignKey(
        CefRolUsuario,
        on_delete=models.DO_NOTHING,
        db_column="rol_id",
        related_name="perfiles_cef_integracion",
    )

    class Meta:
        managed = False
        db_table = "usuarios_perfilusuario"
        verbose_name = "Perfil de usuario CEF"
        verbose_name_plural = "Perfiles de usuario CEF"

    def __str__(self):
        usuario_txt = getattr(self.usuario, "username", self.usuario_id)
        rol_txt = getattr(self.rol, "nombre", "")
        return f"{usuario_txt} - {rol_txt}".strip(" -")


# ============================================================
# FUNCIONES DE NORMALIZACION Y ACCESO A PADRON
# ============================================================

def solo_digitos(valor):
    """
    Quita separadores y deja solo digitos.
    """

    return re.sub(r"\D", "", str(valor or ""))


def normalizar_cueanexo(valor):
    """
    Limpia un CUE-Anexo y solo lo acepta si conserva la longitud esperada.
    """

    cueanexo = solo_digitos(valor)

    if len(cueanexo) != LONGITUD_CUEANEXO:
        return ""

    return cueanexo


def normalizar_cuil_usuario(user):
    """
    Toma el username del usuario logueado y lo interpreta como CUIL/CUIT.
    """

    if not user or not getattr(user, "is_authenticated", False):
        return ""

    cuil = solo_digitos(getattr(user, "username", ""))

    if len(cuil) != 11:
        return ""

    return cuil


def get_cefs_base_queryset():
    """
    Query base contra Padron: filtra solo ofertas CEF de servicios complementarios.
    """

    return (
        CefPadronOferta.objects.using(PADRON_DB_ALIAS)
        .annotate(
            oferta_limpia=Trim("oferta"),
            acronimo_limpio=Upper(Trim("acronimo")),
        )
        .filter(
            oferta_limpia=OFERTA_SERVICIOS_COMPLEMENTARIOS,
            acronimo_limpio=ACRONIMO_CEF,
        )
    )


def get_todos_los_cef():
    """
    Devuelve todos los CEF visibles desde la vista de Padron.
    """

    return get_cefs_base_queryset().order_by("cueanexo")


def get_cefs_por_cuil_responsable(user):
    """
    Devuelve los CEF donde el CUIL/CUIT del usuario figura como responsable.

    Flujo:
    usuario logueado -> username/CUIL -> resploc_cuitcuil -> CUE-Anexo disponible.
    """

    cuil = normalizar_cuil_usuario(user)
    queryset = get_cefs_base_queryset()

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


def get_datos_establecimiento_cef(cueanexo):
    """
    Devuelve el primer registro de Padron para un CUE-Anexo CEF.
    """

    cueanexo = normalizar_cueanexo(cueanexo)

    if not cueanexo:
        return None

    return (
        get_cefs_base_queryset()
        .filter(cueanexo=cueanexo)
        .order_by("cueanexo", "nom_est")
        .first()
    )


# ============================================================
# PERMISOS FUNCIONALES DEL MODULO
# ============================================================

def obtener_rol_usuario_cef(user):
    """
    Devuelve el nombre del rol del usuario autenticado.

    Relacion:
    usuarios_perfilusuario -> usuarios_rol.
    """

    if not user or not getattr(user, "is_authenticated", False):
        return None

    username = (getattr(user, "username", "") or "").strip()

    if not username:
        return None

    try:
        perfil = (
            CefUsuarioPerfil.objects.using(PADRON_DB_ALIAS)
            .select_related("rol")
            .get(usuario__username=username)
        )
    except CefUsuarioPerfil.DoesNotExist:
        return None

    rol_nombre = getattr(perfil.rol, "nombre", "") or ""
    return rol_nombre.strip() or None


def usuario_puede_ver_cef(user):
    """
    Indica si el usuario puede acceder actualmente al modulo CEF.
    """

    rol = obtener_rol_usuario_cef(user)

    if not rol:
        return False

    return rol in ROLES_AUTORIZADOS_CEF


def usuario_es_admin_cef(user):
    """
    Atajo para controles puntuales que requieran rol Administrador.
    """

    return obtener_rol_usuario_cef(user) == "Administrador"


def get_cefs_visualizacion_usuario(user):
    """
    Devuelve todos los CEF para los roles autorizados.

    Esta funcion se conserva porque la vista actual de Localizaciones CEF
    ya la importa desde .models.
    """

    queryset = get_todos_los_cef()

    if not usuario_puede_ver_cef(user):
        return queryset.none()

    return queryset


def get_cefs_cargables_usuario(user):
    """
    Devuelve los CEF sobre los que el usuario puede cargar datos operativos.

    Regla inicial:
    - Administrador: todos los CEF.
    - Otros usuarios autorizados: CEF donde su CUIL figura como responsable.
    """

    queryset = get_todos_los_cef()

    if not usuario_puede_ver_cef(user):
        return queryset.none()

    if usuario_es_admin_cef(user):
        return queryset

    return get_cefs_por_cuil_responsable(user)


def get_cueanexos_cargables_usuario(user):
    """
    Devuelve una lista normalizada de CUE-Anexos cargables para el usuario.
    """

    cueanexos = []

    for cueanexo in get_cefs_cargables_usuario(user).values_list("cueanexo", flat=True).distinct():
        cueanexo_normalizado = normalizar_cueanexo(cueanexo)

        if cueanexo_normalizado and cueanexo_normalizado not in cueanexos:
            cueanexos.append(cueanexo_normalizado)

    return cueanexos


def usuario_puede_cargar_cueanexo(user, cueanexo):
    """
    Valida si el usuario puede operar sobre un CUE-Anexo determinado.
    """

    cueanexo = normalizar_cueanexo(cueanexo)

    if not cueanexo:
        return False

    return cueanexo in get_cueanexos_cargables_usuario(user)


# ============================================================
# MIXINS BASE PARA TABLAS PROPIAS CEF
# ============================================================

class CefAuditoriaMixin(models.Model):
    """
    Campos comunes de auditoria para tablas propias de CEF.
    """

    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="%(app_label)s_%(class)s_creados",
    )

    actualizado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="%(app_label)s_%(class)s_actualizados",
    )

    class Meta:
        abstract = True


class CefCatalogoBase(CefAuditoriaMixin):
    """
    Base para catalogos simples administrables.
    """

    nombre = models.CharField(max_length=150, unique=True)
    activo = models.BooleanField(default=True)
    orden = models.PositiveSmallIntegerField(default=0)

    class Meta:
        abstract = True
        ordering = ["orden", "nombre"]

    def __str__(self):
        return self.nombre


class CefCatalogoCodigoBase(CefAuditoriaMixin):
    """
    Base para catalogos CEF con codigo numerico.
    """

    codigo = models.IntegerField(unique=True)
    nombre = models.CharField(max_length=150)
    descripcion = models.TextField(blank=True)
    activo = models.BooleanField(default=True)
    orden = models.PositiveSmallIntegerField(default=0)

    class Meta:
        abstract = True
        ordering = ["orden", "codigo", "nombre"]

    @property
    def es_no_corresponde(self):
        return self.codigo == -1

    def __str__(self):
        return f"{self.codigo} - {self.nombre}"


# ============================================================
# CATALOGOS OPERATIVOS CEF
# ============================================================
# Estos modelos SI son tablas propias del modulo CEF.
# Van a generar migraciones y tablas nuevas.
# ============================================================

class CefCiclo(CefAuditoriaMixin):
    """
    Ciclo anual de carga.
    """

    anio = models.PositiveSmallIntegerField(
        unique=True,
        validators=[
            MinValueValidator(1900),
            MaxValueValidator(2100),
        ],
    )
    descripcion = models.CharField(max_length=120, blank=True)
    fecha_inicio = models.DateField(blank=True, null=True)
    fecha_fin = models.DateField(blank=True, null=True)
    activo = models.BooleanField(default=True)
    actual = models.BooleanField(default=False)

    class Meta:
        db_table = '"cef"."ciclos"'
        ordering = ["-anio"]
        verbose_name = "Ciclo CEF"
        verbose_name_plural = "Ciclos CEF"
        constraints = [
            models.UniqueConstraint(
                fields=["actual"],
                condition=Q(actual=True),
                name="uq_cef_ciclo_actual",
            ),
        ]

    def clean(self):
        if self.fecha_inicio and self.fecha_fin and self.fecha_fin < self.fecha_inicio:
            raise ValidationError(
                {"fecha_fin": "La fecha de fin no puede ser anterior a la fecha de inicio."}
            )

    def __str__(self):
        return str(self.anio)


class CefEje(CefCatalogoBase):
    """
    Eje institucional de actividad.

    Ejemplos:
    - Gimnasia
    - Deporte
    - Recreacion educativa
    """

    class Meta(CefCatalogoBase.Meta):
        db_table = '"cef"."ejes"'
        verbose_name = "Eje CEF"
        verbose_name_plural = "Ejes CEF"


class CefCodigoRa(CefAuditoriaMixin):
    """
    Codigo RA utilizado para reportes historicos o equivalencias.
    """

    codigo = models.CharField(max_length=20, unique=True)
    descripcion = models.CharField(max_length=255)
    activo = models.BooleanField(default=True)
    orden = models.PositiveSmallIntegerField(default=0)

    class Meta:
        db_table = '"cef"."codigos_ra"'
        ordering = ["orden", "codigo"]
        verbose_name = "Codigo RA CEF"
        verbose_name_plural = "Codigos RA CEF"

    def __str__(self):
        return f"{self.codigo} - {self.descripcion}".strip(" -")


class CefActividad(CefAuditoriaMixin):
    """
    Actividad real seleccionable por el director.

    La actividad define:
    - a que eje pertenece;
    - que codigo RA usa normalmente.
    """

    nombre = models.CharField(max_length=150, unique=True)

    eje = models.ForeignKey(
        CefEje,
        on_delete=models.PROTECT,
        related_name="actividades",
    )

    codigo_ra = models.ForeignKey(
        CefCodigoRa,
        on_delete=models.PROTECT,
        related_name="actividades",
    )

    descripcion = models.TextField(blank=True)
    activo = models.BooleanField(default=True)
    orden = models.PositiveSmallIntegerField(default=0)

    class Meta:
        db_table = '"cef"."actividades"'
        ordering = ["orden", "nombre"]
        verbose_name = "Actividad CEF"
        verbose_name_plural = "Actividades CEF"

    def __str__(self):
        return self.nombre


class CefNivelActividad(CefCatalogoBase):
    """
    Nivel del grupo.

    Ejemplos:
    - Recreativo
    - Inicial o de formacion
    - Avanzado y/o de competencia
    """

    class Meta(CefCatalogoBase.Meta):
        db_table = '"cef"."niveles_actividad"'
        verbose_name = "Nivel de actividad CEF"
        verbose_name_plural = "Niveles de actividad CEF"


class CefRangoEtario(CefAuditoriaMixin):
    """
    Rango etario permitido o sugerido para un grupo.

    Se guarda en dias para poder representar 45 dias, anios y adultos mayores.
    """

    nombre = models.CharField(max_length=120, unique=True)
    edad_desde_dias = models.PositiveIntegerField(default=0)
    edad_hasta_dias = models.PositiveIntegerField(blank=True, null=True)
    activo = models.BooleanField(default=True)
    orden = models.PositiveSmallIntegerField(default=0)

    class Meta:
        db_table = '"cef"."rangos_etarios"'
        ordering = ["orden", "edad_desde_dias", "nombre"]
        verbose_name = "Rango etario CEF"
        verbose_name_plural = "Rangos etarios CEF"

    def clean(self):
        if self.edad_hasta_dias is not None and self.edad_hasta_dias < self.edad_desde_dias:
            raise ValidationError(
                {"edad_hasta_dias": "La edad hasta no puede ser menor que la edad desde."}
            )

    def __str__(self):
        return self.nombre


class CefDiaSemana(CefAuditoriaMixin):
    """
    Catalogo normalizado de dias de funcionamiento.
    """

    nombre = models.CharField(max_length=30, unique=True)
    numero = models.PositiveSmallIntegerField(unique=True)
    activo = models.BooleanField(default=True)
    orden = models.PositiveSmallIntegerField(default=0)

    class Meta:
        db_table = '"cef"."dias_semana"'
        ordering = ["orden", "numero"]
        verbose_name = "Dia de semana CEF"
        verbose_name_plural = "Dias de semana CEF"
        constraints = [
            models.CheckConstraint(
                check=Q(numero__gte=1, numero__lte=7),
                name="ck_cef_dia_num",
            ),
        ]

    def __str__(self):
        return self.nombre


class CefTurno(CefAuditoriaMixin):
    """
    Catalogo de turnos de funcionamiento.

    Ejemplos:
    - Matutino (08:00 a 12:00)
    - Vespertino (14:00 a 18:00)
    - Nocturno (18:00 a 22:00)
    """

    ciclo = models.ForeignKey(
        CefCiclo,
        on_delete=models.PROTECT,
        related_name="turnos",
    )

    nombre = models.CharField(max_length=80)
    hora_desde_referencia = models.TimeField()
    hora_hasta_referencia = models.TimeField()
    activo = models.BooleanField(default=True)
    orden = models.PositiveSmallIntegerField(default=0)

    class Meta:
        db_table = '"cef"."turnos"'
        ordering = ["-ciclo__anio", "orden", "nombre"]
        verbose_name = "Turno CEF"
        verbose_name_plural = "Turnos CEF"
        constraints = [
            models.UniqueConstraint(
                fields=["ciclo", "nombre"],
                name="uq_cef_turno_cic_nom",
            ),
        ]

    def clean(self):
        if (
            self.hora_desde_referencia
            and self.hora_hasta_referencia
            and self.hora_hasta_referencia <= self.hora_desde_referencia
        ):
            raise ValidationError(
                {"hora_hasta_referencia": "La hora hasta debe ser posterior a la hora desde."}
            )

    def __str__(self):
        if not self.hora_desde_referencia or not self.hora_hasta_referencia:
            return self.nombre

        hora_desde = self.hora_desde_referencia.strftime("%H:%M")
        hora_hasta = self.hora_hasta_referencia.strftime("%H:%M")
        return f"{self.nombre} ({hora_desde} a {hora_hasta})"


class CefBeneficioSinoTipo(CefCatalogoCodigoBase):
    """
    Catalogo de beneficio alimentario gratuito.
    """

    class Meta(CefCatalogoCodigoBase.Meta):
        db_table = '"cef"."beneficio_sino_tipo"'
        verbose_name = "Tipo de beneficio alimentario CEF"
        verbose_name_plural = "Tipos de beneficio alimentario CEF"


class CefFuenteFinanciamientoTipo(CefCatalogoCodigoBase):
    """
    Catalogo de fuente de financiamiento del beneficio alimentario.
    """

    class Meta(CefCatalogoCodigoBase.Meta):
        db_table = '"cef"."fuente_financiamiento_tipo"'
        verbose_name = "Tipo de fuente de financiamiento CEF"
        verbose_name_plural = "Tipos de fuente de financiamiento CEF"


class CefPrestacionTipo(CefCatalogoCodigoBase):
    """
    Catalogo de prestaciones alimentarias gratuitas.
    """

    class Meta(CefCatalogoCodigoBase.Meta):
        db_table = '"cef"."prestacion_tipo"'
        verbose_name = "Tipo de prestacion CEF"
        verbose_name_plural = "Tipos de prestacion CEF"


class CefEspacioComedorTipo(CefCatalogoCodigoBase):
    """
    Catalogo de espacios fisicos para comedor.
    """

    class Meta(CefCatalogoCodigoBase.Meta):
        db_table = '"cef"."espacio_comedor_tipo"'
        verbose_name = "Tipo de espacio comedor CEF"
        verbose_name_plural = "Tipos de espacio comedor CEF"


class CefOrientacionTipo(CefCatalogoCodigoBase):
    """
    Catalogo de orientaciones del plan de estudio.
    """

    class Meta(CefCatalogoCodigoBase.Meta):
        db_table = '"cef"."orientacion_tipo"'
        verbose_name = "Tipo de orientacion CEF"
        verbose_name_plural = "Tipos de orientacion CEF"


# ============================================================
# DATOS COMPLEMENTARIOS / RELEVAMIENTO CEF
# ============================================================

class CefDatosRelevamiento(CefAuditoriaMixin):
    """
    Datos complementarios relevados por CUE-Anexo y ciclo.
    """

    ciclo = models.ForeignKey(
        CefCiclo,
        on_delete=models.PROTECT,
        related_name="datos_relevamiento",
    )

    cueanexo = models.CharField(max_length=9, db_index=True)

    beneficio_alimentario_gratuito = models.ForeignKey(
        CefBeneficioSinoTipo,
        on_delete=models.PROTECT,
        related_name="datos_beneficio",
    )

    fuente_financiamiento = models.ForeignKey(
        CefFuenteFinanciamientoTipo,
        on_delete=models.PROTECT,
        related_name="datos_fuente_financiamiento",
    )

    prestacion_tipo = models.ForeignKey(
        CefPrestacionTipo,
        on_delete=models.PROTECT,
        related_name="datos_prestacion",
    )

    espacio_comedor = models.ForeignKey(
        CefEspacioComedorTipo,
        on_delete=models.PROTECT,
        related_name="datos_espacio_comedor",
    )

    c_orientacion = models.ForeignKey(
        CefOrientacionTipo,
        on_delete=models.PROTECT,
        related_name="datos_orientacion",
    )

    nombre_seccion = models.CharField(max_length=120, default="No corresponde")
    observaciones = models.TextField(blank=True)

    beneficio_codigo_snapshot = models.IntegerField(blank=True, null=True, editable=False)
    beneficio_nombre_snapshot = models.CharField(max_length=150, blank=True, editable=False)
    fuente_codigo_snapshot = models.IntegerField(blank=True, null=True, editable=False)
    fuente_nombre_snapshot = models.CharField(max_length=150, blank=True, editable=False)
    prestacion_codigo_snapshot = models.IntegerField(blank=True, null=True, editable=False)
    prestacion_nombre_snapshot = models.CharField(max_length=150, blank=True, editable=False)
    espacio_comedor_codigo_snapshot = models.IntegerField(blank=True, null=True, editable=False)
    espacio_comedor_nombre_snapshot = models.CharField(max_length=150, blank=True, editable=False)
    orientacion_codigo_snapshot = models.IntegerField(blank=True, null=True, editable=False)
    orientacion_nombre_snapshot = models.CharField(max_length=150, blank=True, editable=False)

    class Meta:
        db_table = '"cef"."datos_relevamiento"'
        ordering = ["cueanexo", "-ciclo__anio"]
        verbose_name = "Datos de relevamiento CEF"
        verbose_name_plural = "Datos de relevamiento CEF"
        constraints = [
            models.UniqueConstraint(
                fields=["cueanexo", "ciclo"],
                name="uq_cef_dat_cue_cic",
            ),
        ]
        indexes = [
            models.Index(fields=["cueanexo", "ciclo"], name="idx_cef_dat_cue_cic"),
        ]

    def _beneficio_requiere_no_corresponde(self):
        if not self.beneficio_alimentario_gratuito_id:
            return False

        nombre = (self.beneficio_alimentario_gratuito.nombre or "").strip().lower()
        nombre_normalizado = nombre.translate(str.maketrans("áéíóúüñ", "aeiouun"))
        return (
            self.beneficio_alimentario_gratuito.es_no_corresponde
            or nombre_normalizado in {"no", "sin informacion"}
        )

    def clean(self):
        errors = {}

        cueanexo_normalizado = normalizar_cueanexo(self.cueanexo)
        if not cueanexo_normalizado:
            errors["cueanexo"] = "CUE-Anexo invalido."
        else:
            self.cueanexo = cueanexo_normalizado

        nombre_seccion = (self.nombre_seccion or "").strip()
        self.nombre_seccion = nombre_seccion or "No corresponde"

        if self._beneficio_requiere_no_corresponde():
            if self.fuente_financiamiento_id and self.fuente_financiamiento.codigo != -1:
                errors["fuente_financiamiento"] = (
                    "Debe seleccionar No corresponde cuando no hay beneficio alimentario."
                )

            if self.prestacion_tipo_id and self.prestacion_tipo.codigo != -1:
                errors["prestacion_tipo"] = (
                    "Debe seleccionar No corresponde cuando no hay beneficio alimentario."
                )

        if errors:
            raise ValidationError(errors)

    def actualizar_snapshots_catalogo(self):
        """
        Copia catalogos seleccionados para conservar historico.
        """

        datos_anteriores = None
        if self.pk:
            try:
                datos_anteriores = (
                    type(self).objects
                    .only(
                        "beneficio_alimentario_gratuito_id",
                        "fuente_financiamiento_id",
                        "prestacion_tipo_id",
                        "espacio_comedor_id",
                        "c_orientacion_id",
                    )
                    .get(pk=self.pk)
                )
            except type(self).DoesNotExist:
                datos_anteriores = None

        es_nuevo = datos_anteriores is None

        def debe_actualizar(fk_campo, codigo_snapshot, nombre_snapshot):
            fk_id_campo = f"{fk_campo}_id"
            if not getattr(self, fk_id_campo):
                return False

            if es_nuevo:
                return True

            return (
                getattr(datos_anteriores, fk_id_campo) != getattr(self, fk_id_campo)
                or getattr(self, codigo_snapshot) is None
                or not getattr(self, nombre_snapshot)
            )

        if debe_actualizar(
            "beneficio_alimentario_gratuito",
            "beneficio_codigo_snapshot",
            "beneficio_nombre_snapshot",
        ):
            self.beneficio_codigo_snapshot = self.beneficio_alimentario_gratuito.codigo
            self.beneficio_nombre_snapshot = self.beneficio_alimentario_gratuito.nombre

        if debe_actualizar(
            "fuente_financiamiento",
            "fuente_codigo_snapshot",
            "fuente_nombre_snapshot",
        ):
            self.fuente_codigo_snapshot = self.fuente_financiamiento.codigo
            self.fuente_nombre_snapshot = self.fuente_financiamiento.nombre

        if debe_actualizar(
            "prestacion_tipo",
            "prestacion_codigo_snapshot",
            "prestacion_nombre_snapshot",
        ):
            self.prestacion_codigo_snapshot = self.prestacion_tipo.codigo
            self.prestacion_nombre_snapshot = self.prestacion_tipo.nombre

        if debe_actualizar(
            "espacio_comedor",
            "espacio_comedor_codigo_snapshot",
            "espacio_comedor_nombre_snapshot",
        ):
            self.espacio_comedor_codigo_snapshot = self.espacio_comedor.codigo
            self.espacio_comedor_nombre_snapshot = self.espacio_comedor.nombre

        if debe_actualizar(
            "c_orientacion",
            "orientacion_codigo_snapshot",
            "orientacion_nombre_snapshot",
        ):
            self.orientacion_codigo_snapshot = self.c_orientacion.codigo
            self.orientacion_nombre_snapshot = self.c_orientacion.nombre

    def save(self, *args, **kwargs):
        self.actualizar_snapshots_catalogo()
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.cueanexo} - {self.ciclo}"


# ============================================================
# GRUPOS CEF
# ============================================================

class CefGrupo(CefAuditoriaMixin):
    """
    Grupo operativo de CEF.

    El CUE-Anexo no deberia escribirse libremente desde el formulario.
    La view debe tomarlo del CEF activo o de los CEF cargables del usuario.
    """

    class Estado(models.TextChoices):
        BORRADOR = "borrador", "Borrador"
        ACTIVO = "activo", "Activo"
        INACTIVO = "inactivo", "Inactivo"
        CERRADO = "cerrado", "Cerrado"

    cueanexo = models.CharField(max_length=9, db_index=True)

    ciclo = models.ForeignKey(
        CefCiclo,
        on_delete=models.PROTECT,
        related_name="grupos",
    )

    actividad = models.ForeignKey(
        CefActividad,
        on_delete=models.PROTECT,
        related_name="grupos",
    )

    numero = models.PositiveSmallIntegerField(default=1)
    nombre = models.CharField(max_length=150, blank=True)

    nivel = models.ForeignKey(
        CefNivelActividad,
        on_delete=models.PROTECT,
        related_name="grupos",
    )

    rango_etario = models.ForeignKey(
        CefRangoEtario,
        on_delete=models.PROTECT,
        related_name="grupos",
    )

    turno = models.ForeignKey(
        CefTurno,
        on_delete=models.PROTECT,
        related_name="grupos",
    )

    hora_inicio = models.TimeField()
    hora_fin = models.TimeField()

    cupo_maximo = models.PositiveSmallIntegerField(blank=True, null=True)

    estado = models.CharField(
        max_length=20,
        choices=Estado.choices,
        default=Estado.ACTIVO,
        db_index=True,
    )

    codigo_ra_override = models.ForeignKey(
        CefCodigoRa,
        on_delete=models.PROTECT,
        blank=True,
        null=True,
        related_name="grupos_con_codigo_ra_override",
    )

    motivo_codigo_ra_override = models.TextField(blank=True)

    actividad_nombre_snapshot = models.CharField(max_length=150, blank=True, editable=False)
    eje_nombre_snapshot = models.CharField(max_length=150, blank=True, editable=False)
    codigo_ra_snapshot = models.CharField(max_length=20, blank=True, editable=False)
    codigo_ra_descripcion_snapshot = models.CharField(max_length=255, blank=True, editable=False)
    turno_nombre_snapshot = models.CharField(max_length=80, blank=True, editable=False)
    turno_hora_desde_snapshot = models.TimeField(blank=True, null=True, editable=False)
    turno_hora_hasta_snapshot = models.TimeField(blank=True, null=True, editable=False)

    observaciones = models.TextField(blank=True)

    class Meta:
        db_table = '"cef"."grupos"'
        ordering = [
            "cueanexo",
            "-ciclo__anio",
            "actividad__nombre",
            "numero",
        ]
        verbose_name = "Grupo CEF"
        verbose_name_plural = "Grupos CEF"
        constraints = [
            models.UniqueConstraint(
                fields=["cueanexo", "ciclo", "actividad", "numero"],
                name="uq_cef_grp_cic_act_num",
            ),
        ]
        indexes = [
            models.Index(fields=["cueanexo", "estado"], name="idx_cef_grp_cue_est"),
            models.Index(fields=["cueanexo", "ciclo"], name="idx_cef_grp_cue_cic"),
            models.Index(fields=["actividad", "estado"], name="idx_cef_grp_act_est"),
        ]

    def clean(self):
        errors = {}

        cueanexo_normalizado = normalizar_cueanexo(self.cueanexo)
        if not cueanexo_normalizado:
            errors["cueanexo"] = "CUE-Anexo invalido."
        else:
            self.cueanexo = cueanexo_normalizado

        if self.cupo_maximo is not None and self.cupo_maximo < 1:
            errors["cupo_maximo"] = "El cupo maximo debe ser mayor a cero."

        if self.hora_inicio and self.hora_fin and self.hora_fin <= self.hora_inicio:
            errors["hora_fin"] = "La hora de fin debe ser posterior a la hora de inicio."

        if self.turno_id and self.ciclo_id and self.turno.ciclo_id != self.ciclo_id:
            errors["turno"] = "El turno debe pertenecer al mismo ciclo del grupo."

        if self.turno_id and self.hora_inicio:
            if self.hora_inicio < self.turno.hora_desde_referencia:
                errors["hora_inicio"] = "La hora de inicio debe estar dentro del turno seleccionado."

        if self.turno_id and self.hora_fin:
            if self.hora_fin > self.turno.hora_hasta_referencia:
                errors.setdefault(
                    "hora_fin",
                    "La hora de fin debe estar dentro del turno seleccionado.",
                )

        if self.codigo_ra_override and not self.motivo_codigo_ra_override.strip():
            errors["motivo_codigo_ra_override"] = (
                "Debe indicar el motivo si usa un codigo RA distinto al de la actividad."
            )

        if errors:
            raise ValidationError(errors)

    def actualizar_snapshots_catalogo(self):
        """
        Copia catalogos al grupo para conservar historico.
        """

        grupo_anterior = None
        if self.pk:
            try:
                grupo_anterior = (
                    type(self).objects
                    .only("actividad_id", "codigo_ra_override_id", "turno_id")
                    .get(pk=self.pk)
                )
            except type(self).DoesNotExist:
                grupo_anterior = None

        es_nuevo = grupo_anterior is None
        cambio_actividad = es_nuevo or grupo_anterior.actividad_id != self.actividad_id
        cambio_codigo_ra = (
            es_nuevo
            or grupo_anterior.codigo_ra_override_id != self.codigo_ra_override_id
        )
        cambio_turno = es_nuevo or grupo_anterior.turno_id != self.turno_id

        actividad_snapshot_vacio = (
            not self.actividad_nombre_snapshot
            or not self.eje_nombre_snapshot
        )
        codigo_ra_snapshot_vacio = (
            not self.codigo_ra_snapshot
            or not self.codigo_ra_descripcion_snapshot
        )
        turno_snapshot_vacio = (
            not self.turno_nombre_snapshot
            or not self.turno_hora_desde_snapshot
            or not self.turno_hora_hasta_snapshot
        )

        if self.actividad_id and (cambio_actividad or actividad_snapshot_vacio):
            self.actividad_nombre_snapshot = self.actividad.nombre
            self.eje_nombre_snapshot = self.actividad.eje.nombre

        if self.actividad_id and (
            cambio_actividad
            or cambio_codigo_ra
            or codigo_ra_snapshot_vacio
        ):
            codigo_ra = self.codigo_ra_override or self.actividad.codigo_ra
            self.codigo_ra_snapshot = codigo_ra.codigo
            self.codigo_ra_descripcion_snapshot = codigo_ra.descripcion

        if self.turno_id and (cambio_turno or turno_snapshot_vacio):
            self.turno_nombre_snapshot = self.turno.nombre
            self.turno_hora_desde_snapshot = self.turno.hora_desde_referencia
            self.turno_hora_hasta_snapshot = self.turno.hora_hasta_referencia

    def save(self, *args, **kwargs):
        self.actualizar_snapshots_catalogo()
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        actividad = self.actividad_nombre_snapshot or str(self.actividad)
        base = f"{self.cueanexo} - {self.ciclo} - {actividad}"

        if self.nombre:
            return f"{base} - {self.nombre}"

        return f"{base} - Grupo {self.numero}"


class CefGrupoDiaFuncionamiento(CefAuditoriaMixin):
    """
    Dias de funcionamiento de un grupo.

    El horario se toma del turno seleccionado en el grupo.
    """

    grupo = models.ForeignKey(
        CefGrupo,
        on_delete=models.CASCADE,
        related_name="dias_funcionamiento",
    )

    dia_semana = models.ForeignKey(
        CefDiaSemana,
        on_delete=models.PROTECT,
        related_name="grupos_funcionamiento",
    )

    observaciones = models.CharField(max_length=255, blank=True)

    class Meta:
        db_table = '"cef"."grupo_dias_func"'
        ordering = ["grupo", "dia_semana__orden", "dia_semana__numero"]
        verbose_name = "Dia de funcionamiento de grupo CEF"
        verbose_name_plural = "Dias de funcionamiento de grupos CEF"
        constraints = [
            models.UniqueConstraint(
                fields=["grupo", "dia_semana"],
                name="uq_cef_grp_dia",
            ),
        ]

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.grupo} - {self.dia_semana}"


# ============================================================
# BANCO DE ALUMNOS Y DOCENTES CEF
# ============================================================
# Capa previa por CUE-Anexo y ciclo.
# La inscripcion/asignacion a grupos sigue viviendo en sus tablas actuales.
# ============================================================

class CefAlumnoCef(CefAuditoriaMixin):
    """
    Alumno incorporado al banco operativo de un CEF para un ciclo.
    """

    class Estado(models.TextChoices):
        ACTIVO = "activo", "Activo"
        INACTIVO = "inactivo", "Inactivo"
        BAJA = "baja", "Baja"

    cueanexo = models.CharField(max_length=9, db_index=True)

    ciclo = models.ForeignKey(
        CefCiclo,
        on_delete=models.PROTECT,
        related_name="alumnos_cef",
    )

    alumno = models.ForeignKey(
        "bnhalumnos.Alumno",
        on_delete=models.PROTECT,
        related_name="bancos_cef",
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
    alumno_nombre_snapshot = models.CharField(max_length=255, blank=True, editable=False)
    alumno_documento_snapshot = models.CharField(max_length=30, blank=True, editable=False)
    alumno_cuil_snapshot = models.CharField(max_length=11, blank=True, editable=False)
    observaciones = models.TextField(blank=True)

    class Meta:
        db_table = '"cef"."alumnos_cef"'
        ordering = ["cueanexo", "-ciclo__anio", "alumno_nombre_snapshot"]
        verbose_name = "Alumno CEF"
        verbose_name_plural = "Alumnos CEF"
        constraints = [
            models.UniqueConstraint(
                fields=["cueanexo", "ciclo", "alumno"],
                condition=Q(estado="activo"),
                name="uq_cef_alumnocef_act",
            ),
        ]
        indexes = [
            models.Index(fields=["cueanexo", "ciclo"], name="idx_cef_alumnocef_cic"),
            models.Index(fields=["alumno", "estado"], name="idx_cef_alumnocef_est"),
        ]

    def clean(self):
        errors = {}

        cueanexo_normalizado = normalizar_cueanexo(self.cueanexo)
        if not cueanexo_normalizado:
            errors["cueanexo"] = "CUE-Anexo invalido."
        else:
            self.cueanexo = cueanexo_normalizado

        if self.fecha_baja and self.fecha_baja < self.fecha_alta:
            errors["fecha_baja"] = "La fecha de baja no puede ser anterior a la fecha de alta."

        if self.estado == self.Estado.BAJA and not self.fecha_baja:
            errors["fecha_baja"] = "Debe indicar fecha de baja cuando el alumno esta en baja."

        if self.estado != self.Estado.BAJA and self.motivo_baja:
            errors["motivo_baja"] = "Solo debe indicar motivo de baja cuando el alumno esta en baja."

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

        self.alumno_documento_snapshot = str(
            getattr(self.alumno, "nro_doc", "") or ""
        )
        self.alumno_cuil_snapshot = solo_digitos(
            getattr(self.alumno, "cuil", "") or ""
        )

    def save(self, *args, **kwargs):
        self.actualizar_snapshots_alumno()
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        alumno = self.alumno_nombre_snapshot or str(self.alumno_id)
        return f"{self.cueanexo} - {self.ciclo} - {alumno}"


class CefDocenteCef(CefAuditoriaMixin):
    """
    Docente incorporado al banco operativo de un CEF para un ciclo.
    """

    class Estado(models.TextChoices):
        ACTIVO = "activo", "Activo"
        INACTIVO = "inactivo", "Inactivo"
        BAJA = "baja", "Baja"

    cueanexo = models.CharField(max_length=9, db_index=True)

    ciclo = models.ForeignKey(
        CefCiclo,
        on_delete=models.PROTECT,
        related_name="docentes_cef",
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
    docente_nombre_snapshot = models.CharField(max_length=255, blank=True, editable=False)
    docente_dni_snapshot = models.CharField(max_length=20, blank=True, editable=False)
    docente_estado_bnh_snapshot = models.CharField(max_length=30, blank=True, editable=False)
    observaciones = models.TextField(blank=True)

    class Meta:
        db_table = '"cef"."docentes_cef"'
        ordering = ["cueanexo", "-ciclo__anio", "docente_nombre_snapshot", "docente_cuil"]
        verbose_name = "Docente CEF"
        verbose_name_plural = "Docentes CEF"
        constraints = [
            models.UniqueConstraint(
                fields=["cueanexo", "ciclo", "docente_cuil"],
                condition=Q(estado="activo"),
                name="uq_cef_docentecef_act",
            ),
        ]
        indexes = [
            models.Index(fields=["cueanexo", "ciclo"], name="idx_cef_docentecef_cic"),
            models.Index(fields=["docente_cuil", "estado"], name="idx_cef_docentecef_est"),
        ]

    def clean(self):
        errors = {}

        cueanexo_normalizado = normalizar_cueanexo(self.cueanexo)
        if not cueanexo_normalizado:
            errors["cueanexo"] = "CUE-Anexo invalido."
        else:
            self.cueanexo = cueanexo_normalizado

        docente_cuil_normalizado = solo_digitos(self.docente_cuil)
        if len(docente_cuil_normalizado) != 11:
            errors["docente_cuil"] = "El CUIL del docente debe tener 11 digitos."
        else:
            self.docente_cuil = docente_cuil_normalizado

        if self.fecha_baja and self.fecha_baja < self.fecha_alta:
            errors["fecha_baja"] = "La fecha de baja no puede ser anterior a la fecha de alta."

        if self.estado == self.Estado.BAJA and not self.fecha_baja:
            errors["fecha_baja"] = "Debe indicar fecha de baja cuando el docente esta en baja."

        if self.estado != self.Estado.BAJA and self.motivo_baja:
            errors["motivo_baja"] = "Solo debe indicar motivo de baja cuando el docente esta en baja."

        if errors:
            raise ValidationError(errors)

    def actualizar_snapshots_docente(self):
        docente = (
            CefDocenteBnh.objects.using(PADRON_DB_ALIAS)
            .filter(cuil=self.docente_cuil)
            .first()
        )

        if not docente:
            return

        self.docente_nombre_snapshot = docente.nombre_completo
        self.docente_dni_snapshot = docente.dni or ""
        self.docente_estado_bnh_snapshot = docente.estado or ""

    def save(self, *args, **kwargs):
        self.docente_cuil = solo_digitos(self.docente_cuil)
        self.actualizar_snapshots_docente()
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        docente = self.docente_nombre_snapshot or self.docente_cuil
        return f"{self.cueanexo} - {self.ciclo} - {docente}"


# ============================================================
# INSCRIPCIONES DE ALUMNOS A GRUPOS
# ============================================================
# El alumno vive en bnhalumnos.Alumno.
# CEF no duplica datos personales.
#
# El estado ACTIVO/BAJA del alumno dentro de CEF vive aca,
# no en el alumno global.
# ============================================================

class CefInscripcion(CefAuditoriaMixin):
    """
    Vinculo entre un alumno global de BNH Alumnos y un grupo CEF.
    """

    class Estado(models.TextChoices):
        ACTIVO = "activo", "Activo"
        BAJA = "baja", "Baja"

    grupo = models.ForeignKey(
        CefGrupo,
        on_delete=models.PROTECT,
        related_name="inscripciones",
    )

    alumno = models.ForeignKey(
        "bnhalumnos.Alumno",
        on_delete=models.PROTECT,
        related_name="inscripciones_cef",
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
        db_table = '"cef"."inscripciones"'
        ordering = ["grupo", "alumno"]
        verbose_name = "Inscripcion CEF"
        verbose_name_plural = "Inscripciones CEF"
        constraints = [
            models.UniqueConstraint(
                fields=["grupo", "alumno"],
                condition=Q(estado="activo"),
                name="uq_cef_insc_abierta",
            ),
        ]
        indexes = [
            models.Index(fields=["estado"], name="idx_cef_insc_est"),
            models.Index(fields=["fecha_inscripcion"], name="idx_cef_insc_fecha"),
            models.Index(fields=["alumno", "estado"], name="idx_cef_insc_alum_est"),
        ]

    def clean(self):
        errors = {}

        if self.fecha_baja and self.fecha_baja < self.fecha_inscripcion:
            errors["fecha_baja"] = "La fecha de baja no puede ser anterior a la fecha de inscripcion."

        if self.estado == self.Estado.BAJA and not self.fecha_baja:
            errors["fecha_baja"] = "Debe indicar fecha de baja cuando la inscripcion esta en baja."

        if self.estado != self.Estado.BAJA and self.motivo_baja:
            errors["motivo_baja"] = "Solo debe indicar motivo de baja cuando la inscripcion esta en baja."

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.alumno} - {self.grupo} - {self.get_estado_display()}"


# ============================================================
# DOCENTES DE GRUPOS CEF
# ============================================================
# El docente vive en bnh.personas.
# CEF guarda solo el vinculo operativo con el grupo.
# ============================================================

class CefDocenteGrupo(CefAuditoriaMixin):
    """
    Vinculo entre un docente BNH y un grupo CEF.
    """

    class Rol(models.TextChoices):
        TITULAR = "titular", "Titular"
        SUPLENTE = "suplente", "Suplente"

    class Estado(models.TextChoices):
        ACTIVO = "activo", "Activo"
        INACTIVO = "inactivo", "Inactivo"
        BAJA = "baja", "Baja"

    grupo = models.ForeignKey(
        CefGrupo,
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
    docente_nombre_snapshot = models.CharField(max_length=255, blank=True, editable=False)
    docente_dni_snapshot = models.CharField(max_length=20, blank=True, editable=False)
    docente_estado_bnh_snapshot = models.CharField(max_length=30, blank=True, editable=False)
    observaciones = models.TextField(blank=True)

    class Meta:
        db_table = '"cef"."docentes_grupo"'
        ordering = ["grupo", "rol", "docente_nombre_snapshot", "docente_cuil"]
        verbose_name = "Docente de grupo CEF"
        verbose_name_plural = "Docentes de grupos CEF"
        constraints = [
            models.UniqueConstraint(
                fields=["grupo", "docente_cuil"],
                condition=Q(estado="activo"),
                name="uq_cef_doc_grp_cuil_act",
            ),
            models.UniqueConstraint(
                fields=["grupo", "rol"],
                condition=Q(estado="activo"),
                name="uq_cef_doc_grp_rol_act",
            ),
        ]
        indexes = [
            models.Index(fields=["docente_cuil", "estado"], name="idx_cef_doc_cuil_est"),
            models.Index(fields=["grupo", "estado"], name="idx_cef_doc_grp_est"),
            models.Index(fields=["rol", "estado"], name="idx_cef_doc_rol_est"),
        ]

    def clean(self):
        errors = {}

        docente_cuil_normalizado = solo_digitos(self.docente_cuil)
        if len(docente_cuil_normalizado) != 11:
            errors["docente_cuil"] = "El CUIL del docente debe tener 11 digitos."
        else:
            self.docente_cuil = docente_cuil_normalizado

        if self.fecha_desde and self.fecha_hasta and self.fecha_hasta < self.fecha_desde:
            errors["fecha_hasta"] = "La fecha hasta no puede ser anterior a la fecha desde."

        if self.estado == self.Estado.BAJA and not self.fecha_hasta:
            errors["fecha_hasta"] = "Debe indicar fecha hasta cuando la asignacion esta en baja."

        if errors:
            raise ValidationError(errors)

    def actualizar_snapshots_docente(self):
        """
        Copia datos basicos del docente BNH si se encuentra por CUIL.
        """

        docente = (
            CefDocenteBnh.objects.using(PADRON_DB_ALIAS)
            .filter(cuil=self.docente_cuil)
            .first()
        )

        if not docente:
            return

        self.docente_nombre_snapshot = docente.nombre_completo
        self.docente_dni_snapshot = docente.dni or ""
        self.docente_estado_bnh_snapshot = docente.estado or ""

    def save(self, *args, **kwargs):
        self.docente_cuil = solo_digitos(self.docente_cuil)
        self.actualizar_snapshots_docente()
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        docente = self.docente_nombre_snapshot or self.docente_cuil
        return f"{self.grupo} - {self.get_rol_display()} - {docente}"


# ============================================================
# INVENTARIO CEF
# ============================================================
# El inventario sigue la planilla oficial:
# Materiales, Cantidad y Estado.
# ============================================================


class CefMaterial(CefAuditoriaMixin):
    """
    Material seleccionable para la carga de inventario CEF.
    """

    nombre = models.CharField(max_length=150, unique=True)
    descripcion = models.TextField(blank=True)
    activo = models.BooleanField(default=True)
    orden = models.PositiveSmallIntegerField(default=0)

    class Meta:
        db_table = '"cef"."materiales"'
        ordering = ["orden", "nombre"]
        verbose_name = "Material CEF"
        verbose_name_plural = "Materiales CEF"

    def __str__(self):
        return self.nombre


class CefInventarioMaterial(CefAuditoriaMixin):
    """
    Inventario simple por CEF y ciclo segun planilla:
    Materiales, Cantidad y Estado.
    """

    cueanexo = models.CharField(max_length=9, db_index=True)

    ciclo = models.ForeignKey(
        CefCiclo,
        on_delete=models.PROTECT,
        related_name="inventario_materiales",
    )

    material = models.ForeignKey(
        CefMaterial,
        on_delete=models.PROTECT,
        related_name="inventarios",
    )

    cantidad = models.PositiveIntegerField(default=0)
    estado_descripcion = models.TextField(blank=True)
    material_nombre_snapshot = models.CharField(max_length=150, blank=True, editable=False)
    observaciones = models.TextField(blank=True)

    class Meta:
        db_table = '"cef"."inventario_materiales"'
        ordering = [
            "cueanexo",
            "-ciclo__anio",
            "material__orden",
            "material__nombre",
        ]
        verbose_name = "Inventario de material CEF"
        verbose_name_plural = "Inventario de materiales CEF"
        constraints = [
            models.UniqueConstraint(
                fields=["cueanexo", "ciclo", "material"],
                name="uq_cef_inv_cic_mat",
            ),
        ]
        indexes = [
            models.Index(fields=["cueanexo", "ciclo"], name="idx_cef_inv_cue_cic"),
            models.Index(fields=["material"], name="idx_cef_inv_mat"),
        ]

    def clean(self):
        errors = {}

        cueanexo_normalizado = normalizar_cueanexo(self.cueanexo)
        if not cueanexo_normalizado:
            errors["cueanexo"] = "CUE-Anexo invalido."
        else:
            self.cueanexo = cueanexo_normalizado

        if errors:
            raise ValidationError(errors)

    def actualizar_snapshots_catalogo(self):
        """
        Copia material para conservar historico.
        """

        inventario_anterior = None
        if self.pk:
            try:
                inventario_anterior = (
                    type(self).objects
                    .only("material_id")
                    .get(pk=self.pk)
                )
            except type(self).DoesNotExist:
                inventario_anterior = None

        snapshot_vacio = not self.material_nombre_snapshot
        material_cambiado = (
            inventario_anterior is None
            or inventario_anterior.material_id != self.material_id
        )

        if self.material_id and (material_cambiado or snapshot_vacio):
            self.material_nombre_snapshot = self.material.nombre

    def save(self, *args, **kwargs):
        self.actualizar_snapshots_catalogo()
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.cueanexo} - {self.ciclo} - {self.material} x {self.cantidad}"
