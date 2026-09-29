from django.db import connection, models
from django.conf import settings
#from django.forms import model_to_dict
#from apps.cenpe.models import CeicPuntos
from django.core.exceptions import ValidationError, ObjectDoesNotExist
#from django.core.validators import RegexValidator
from django.utils import timezone
from decimal import Decimal, ROUND_HALF_UP


POF_DB_ALIAS = "default"
DOS_DECIMALES = Decimal("0.01")


def _decimal_o_cero(valor):
    if valor in (None, ""):
        return Decimal("0")
    if isinstance(valor, Decimal):
        return valor
    return Decimal(str(valor))


def _decimal_dos_decimales(valor):
    return _decimal_o_cero(valor).quantize(DOS_DECIMALES, rounding=ROUND_HALF_UP)

ROLES_POF_ACCESO_COMPLETO = {
    "Pof",
    "Administrador",
}

ROLES_POF_SOLO_VISUALIZACION_COMPLETA = {
    "Director General",
    "Subsecretario",
    "Gestor",
}

ROL_POF_REGIONAL = "Regional"
ROL_POF_DIRECTOR = "Director"

ROLES_AUTORIZADOS_POF = (
    ROLES_POF_ACCESO_COMPLETO
    | ROLES_POF_SOLO_VISUALIZACION_COMPLETA
)


class PofRolUsuario(models.Model):
    """
    Rol tomado desde las tablas compartidas de usuarios.
    """

    id = models.BigIntegerField(primary_key=True)
    nombre = models.CharField(max_length=100, blank=True, null=True)

    class Meta:
        managed = False
        db_table = "usuarios_rol"
        verbose_name = "Rol de usuario POF"
        verbose_name_plural = "Roles de usuario POF"
        

    def __str__(self):
        return self.nombre or ""


class PofUsuarioPerfil(models.Model):
    """
    Perfil externo que vincula usuario autenticado con rol funcional.
    """

    id = models.BigIntegerField(primary_key=True)

    usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.DO_NOTHING,
        db_column="usuario_id",
        related_name="perfil_pof_integracion",
    )

    rol = models.ForeignKey(
        PofRolUsuario,
        on_delete=models.DO_NOTHING,
        db_column="rol_id",
        related_name="perfiles_pof_integracion",
    )

    class Meta:
        managed = False
        db_table = "usuarios_perfilusuario"
        verbose_name = "Perfil de usuario POF"
        verbose_name_plural = "Perfiles de usuario POF"

    def __str__(self):
        usuario_txt = getattr(self.usuario, "username", self.usuario_id)
        rol_txt = getattr(self.rol, "nombre", "")
        return f"{usuario_txt} - {rol_txt}".strip(" -")


def obtener_rol_usuario_pof(user):
    """
    Devuelve el nombre del rol funcional del usuario autenticado.
    """

    if not user or not getattr(user, "is_authenticated", False):
        return None

    if hasattr(user, "_rol_pof_cache"):
        return user._rol_pof_cache

    try:
        perfil = (
            PofUsuarioPerfil.objects.using(POF_DB_ALIAS)
            .select_related("rol")
            .get(usuario_id=user.pk)
        )
    except PofUsuarioPerfil.DoesNotExist:
        user._rol_pof_cache = None
        return None

    rol_nombre = getattr(perfil.rol, "nombre", "") or ""
    user._rol_pof_cache = rol_nombre.strip() or None
    return user._rol_pof_cache


def usuario_puede_ver_pof(user):
    rol = obtener_rol_usuario_pof(user)

    if not rol:
        return False

    return rol in ROLES_AUTORIZADOS_POF


def usuario_tiene_acceso_completo_pof(user):
    return obtener_rol_usuario_pof(user) in ROLES_POF_ACCESO_COMPLETO


def usuario_puede_ver_visualizacion_pof(user):
    return usuario_puede_ver_pof(user)


def usuario_tiene_alcance_restringido_pof(user):
    return obtener_rol_usuario_pof(user) in {ROL_POF_REGIONAL, ROL_POF_DIRECTOR}


def obtener_regiones_usuario_pof(user):
    if hasattr(user, "_regiones_pof_cache"):
        return set(user._regiones_pof_cache)

    username = getattr(user, "username", "")
    if not username:
        return set()

    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT region_loc
            FROM public.usuarios_regionalusuarios
            WHERE usuario = %s
              AND activo = true
            """,
            [username],
        )
        regiones = {
            str(fila[0]).strip()
            for fila in cursor.fetchall()
            if fila[0] and str(fila[0]).strip()
        }
    user._regiones_pof_cache = frozenset(regiones)
    return regiones


def obtener_cueanexos_director_pof(user):
    if hasattr(user, "_cueanexos_director_pof_cache"):
        return set(user._cueanexos_director_pof_cache)

    username = str(getattr(user, "username", "") or "").strip()
    if not username:
        return set()

    from .services.filtros_pof_service import normalizar_cuil

    cuil_normalizado = normalizar_cuil(username)
    variantes_cuil = {username}
    if cuil_normalizado:
        variantes_cuil.update(
            {
                cuil_normalizado,
                f"{cuil_normalizado[:2]}-{cuil_normalizado[2:10]}-{cuil_normalizado[10:]}",
                f"{cuil_normalizado[:2]} {cuil_normalizado[2:10]} {cuil_normalizado[10:]}",
            }
        )

    filas = (
        VCapaUnicaOfertasAnt.objects.using(POF_DB_ALIAS)
        .filter(resploc_cuitcuil__in=variantes_cuil)
        .values_list("padron_cueanexo", "cueanexo")
    )
    cueanexos = set()
    for padron_cueanexo, cueanexo in filas:
        valor = str(padron_cueanexo or cueanexo or "").strip()
        if valor:
            cueanexos.add(valor)
    user._cueanexos_director_pof_cache = frozenset(cueanexos)
    return cueanexos


def usuario_es_admin_pof(user):
    return obtener_rol_usuario_pof(user) == "Administrador"


def usuario_puede_operar_pof(user):
    return usuario_tiene_acceso_completo_pof(user)


# REPRESENTA AÑO Y NIVEL DE UNA REUNIDA POF ----------------------------------------------------------
class ReunidaPof(models.Model):
    """
    Representa una Reunida POF por año y nivel.
    Es la cabecera general sobre la que luego se cargan localizaciones y cargos.
    """

    class Nivel(models.TextChoices):
        """
        Niveles disponibles para organizar la Reunida POF.
        """
        INICIAL = "INICIAL", "Inicial"
        PRIMARIA = "PRIMARIA", "Primaria"
        SECUNDARIA = "SECUNDARIA", "Secundaria"
        SECUNDARIA_TECNICA = "SECUNDARIA_TECNICA", "Secundaria Técnica"
        ESPECIAL = "ESPECIAL", "Educación Especial"
        FISICA = "FISICA", "Educación Física"
        ADULTOS = "ADULTOS", "Adultos"
        TERCIARIO = "TERCIARIO", "Terciario"
        BIBLIOTECA = "BIBLIOTECA", "Biblioteca"

    # Año al que corresponde la Reunida POF. Permite años históricos para cargar Reunidas anteriores.
    anio = models.PositiveSmallIntegerField(
        verbose_name="Año",
        help_text="Año de la Reunida POF.",
    )

    # Nivel educativo o área al que pertenece la Reunida.
    nivel = models.CharField(
        max_length=30,
        choices=Nivel.choices,
        verbose_name="Nivel",
    )

    # Reunida del mismo nivel y del año inmediato anterior usada como base, si corresponde.
    reunida_base_anterior = models.ForeignKey(
        "self",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="reunidas_derivadas",
        verbose_name="Reunida base anterior",
        help_text=(
            "Reunida POF del mismo nivel y del año inmediatamente anterior "
            "usada como base, si corresponde."
        ),
    )

    # Fecha real de la última modificación del registro.
    actualizado_en = models.DateTimeField(
        auto_now=True,
        verbose_name="Actualizado en",
    )

    class Meta:
        db_table = '"reunidas_pof"."reunida_pof"'
        verbose_name = "Reunida POF"
        verbose_name_plural = "Reunidas POF"

        # Evita duplicar una misma Reunida para igual año y nivel.
        constraints = [
            models.UniqueConstraint(
                fields=["anio", "nivel"],
                name="uq_reunida_pof_anio_nivel",
            ),
            models.CheckConstraint(
                condition = models.Q(anio__gte=1000, anio__lte=9999),
                name = "ck_reunida_pof_anio_4_dig",
            ),
        ]

        # Índice útil para buscar rápido por año y nivel.
        indexes = [
            models.Index(
                fields=["anio", "nivel"],
                name="idx_reunida_pof_anio_nivel",
            ),
        ]

        # Ordena primero las Reunidas más recientes.
        ordering = ["-anio", "nivel"]

    def clean(self):
        """
        Valida la cabecera de la Reunida y su base anual opcional.

        - Mantiene el año dentro de cuatro dígitos.
        - Solo admite una base del mismo nivel y del año inmediato anterior.
        - Rechaza explícitamente la autorreferencia sin modificar la Reunida base.
        """
        super().clean()

        errores = {}

        if not self.anio or self.anio < 1000 or self.anio > 9999:
            errores["anio"] = "El año debe tener 4 dígitos."
        elif self.anio > timezone.localdate().year + 1:
            errores["anio"] = "El año no puede superar el año próximo."

        if self.reunida_base_anterior_id:
            if self.pk and self.reunida_base_anterior_id == self.pk:
                errores["reunida_base_anterior"] = (
                    "La Reunida base anterior no puede ser el mismo registro."
                )
            else:
                reunida_base_anterior = self.reunida_base_anterior

                if reunida_base_anterior.nivel != self.nivel:
                    errores["reunida_base_anterior"] = (
                        "La Reunida base anterior debe pertenecer al mismo nivel."
                    )
                elif reunida_base_anterior.anio != self.anio - 1:
                    errores["reunida_base_anterior"] = (
                        "La Reunida base anterior debe corresponder exactamente al año "
                        "inmediatamente anterior."
                    )

        if errores:
            raise ValidationError(errores)

    def _resolver_reunida_base_anterior(self):
        """
        Resuelve la única base válida para una Reunida nueva.

        - Busca solo el mismo nivel y el año inmediatamente anterior.
        - Devuelve None si el año o nivel aún no permiten una consulta válida.
        - Lee la base sin modificarla ni recorrer otras Reunidas.
        """
        if not isinstance(self.anio, int) or not self.nivel:
            return None

        return type(self).objects.only("pk", "anio", "nivel").filter(
            anio=self.anio - 1,
            nivel=self.nivel,
        ).first()

    def save(self, *args, **kwargs):
        """
        Resuelve la base anual al crear y valida antes de persistir.

        - Reemplaza cualquier base externa por la coincidencia exacta del año previo.
        - No recalcula la base al guardar una Reunida ya existente.
        - Ejecuta full_clean después de resolver la referencia automática.
        """
        if self._state.adding:
            self.reunida_base_anterior = self._resolver_reunida_base_anterior()

        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        """
        Muestra una descripción legible de la Reunida.
        """
        return f"{self.get_nivel_display()} {self.anio}"


# REPRESENTA PROYECTOS ESPECIALES POF ---------------------------------------------------------------------
class ProyectosEspecialesPof(models.Model):
    """
    Representa una cabecera anual flexible para Proyectos Especiales POF.
    Permite agrupar cargas por nombre libre y continuidad opcional.
    """

    # Año al que corresponden los Proyectos Especiales POF.
    anio = models.PositiveSmallIntegerField(
        verbose_name="Año",
        help_text="Año de los Proyectos Especiales POF.",
    )

    # Nombre libre del proyecto, programa, dispositivo o agrupador.
    nombre = models.CharField(
        max_length=255,
        verbose_name="Nombre",
        help_text="Nombre libre del proyecto, programa, dispositivo o agrupador.",
    )

    # Resolución asociada al proyecto, si corresponde.
    resolucion = models.CharField(
        max_length=150,
        blank=True,
        verbose_name="Resolución",
    )

    # Observación opcional para describir el contexto del proyecto.
    observacion = models.TextField(
        blank=True,
        verbose_name="Observación",
    )

    # Proyecto Especial POF de un año anterior usado como base, si corresponde.
    proyecto_base_anterior = models.ForeignKey(
        "self",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="proyectos_derivados",
        verbose_name="Proyecto base anterior",
        help_text="Proyecto Especial POF del año anterior usado como base, si corresponde.",
    )

    # Fecha real de la última modificación del registro.
    actualizado_en = models.DateTimeField(
        auto_now=True,
        verbose_name="Actualizado en",
    )

    class Meta:
        db_table = '"reunidas_pof"."proyectos_especiales_pof"'
        verbose_name = "Proyectos Especiales POF"
        verbose_name_plural = "Proyectos Especiales POF"

        constraints = [
            models.CheckConstraint(
                condition=models.Q(anio__gte=1000, anio__lte=9999),
                name="ck_proy_esp_pof_anio_4_dig",
            ),
            models.UniqueConstraint(
                fields=["anio", "nombre", "resolucion"],
                name="uq_proyectos_especiales_pof_anio_nombre_res",
            ),
        ]

        indexes = [
            models.Index(
                fields=["anio", "nombre"],
                name="idx_proy_esp_pof_anio_nombre",
            ),
            models.Index(
                fields=["proyecto_base_anterior"],
                name="idx_proy_esp_pof_base_ant",
            ),
        ]

        ordering = ["-anio", "nombre"]

    def clean(self):
        """
        Valida reglas internas antes de guardar el Proyecto Especial POF.
        Evita años inválidos, nombres vacíos y referencias incoherentes.
        """
        super().clean()

        self.nombre = str(self.nombre or "").strip()
        self.resolucion = str(self.resolucion or "").strip()
        self.observacion = str(self.observacion or "").strip()

        if not self.anio or self.anio < 1000 or self.anio > 9999:
            raise ValidationError({
                "anio": "El año debe tener 4 dígitos."
            })

        if not self.nombre:
            raise ValidationError({
                "nombre": "El nombre de los Proyectos Especiales POF es obligatorio."
            })

        if self.proyecto_base_anterior_id:
            if self.pk and self.proyecto_base_anterior_id == self.pk:
                raise ValidationError({
                    "proyecto_base_anterior": "El proyecto base anterior no puede ser el mismo registro."
                })

            if self.proyecto_base_anterior.anio >= self.anio:
                raise ValidationError({
                    "proyecto_base_anterior": "El proyecto base anterior debe corresponder a un año anterior."
                })

    def save(self, *args, **kwargs):
        """
        Ejecuta las validaciones del modelo antes de guardar.
        Esto evita guardar registros inconsistentes desde vistas, admin o scripts.
        """
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        """
        Muestra una descripción legible de los Proyectos Especiales POF.
        """
        resolucion = f" - {self.resolucion}" if self.resolucion else ""
        return f"{self.nombre} {self.anio}{resolucion}"


#REPRESENTA EL CUANEXO DENTRO DE UNA REUNIDA POF ----------------------------------------------------------

class LocalizacionPof(models.Model):
    """
    Representa una localización/oferta usada por POF dentro de una cabecera.
    Guarda solo los identificadores necesarios; los datos del padrón van en snapshots.
    """

    # Reunida a la que pertenece esta localización.
    reunida = models.ForeignKey(
        ReunidaPof,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="localizaciones",
        verbose_name="Reunida POF",
    )

    # Proyectos Especiales POF a los que pertenece esta localización.
    proyecto_especial = models.ForeignKey(
        ProyectosEspecialesPof,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="localizaciones",
        verbose_name="Proyectos Especiales POF",
    )

    # CUEANEXO completo de 9 dígitos. Obligatorio para Reunidas y opcional para Proyectos Especiales POF.
    cueanexo = models.CharField(
        max_length=20,
        blank=True,
        db_index=True,
        verbose_name="CUEANEXO",
        help_text="CUEANEXO completo de 9 dígitos. Obligatorio para Reunidas; opcional para Proyectos Especiales POF.",
    )

    # CUOF de la oferta/localización, usado para diferenciar ofertas dentro de una cabecera.
    cuof = models.CharField(
        max_length=100,
        verbose_name="CUOF",
    )

    # CUI de la localización, si el padrón lo informa.
    cui = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="CUI",
    )

    # Fecha real en la que se creó el registro.
    creado_en = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Creado en",
    )

    # Fecha real de la última modificación del registro.
    actualizado_en = models.DateTimeField(
        auto_now=True,
        verbose_name="Actualizado en",
    )

    class Meta:
        db_table = '"reunidas_pof"."localizacion_pof"'
        verbose_name = "Localización POF"
        verbose_name_plural = "Localizaciones POF"

        constraints = [
            # Asegura que la localización pertenezca a una sola cabecera.
            models.CheckConstraint(
                condition=(
                    models.Q(reunida__isnull=False, proyecto_especial__isnull=True) |
                    models.Q(reunida__isnull=True, proyecto_especial__isnull=False)
                ),
                name="ck_localizacion_pof_una_cabecera",
            ),

            # Evita duplicar la misma oferta/localización dentro de una misma Reunida.
            models.UniqueConstraint(
                fields=["reunida", "cueanexo", "cuof"],
                condition=models.Q(reunida__isnull=False),
                name="uq_loc_pof_reunida_cueanexo_cuof",
            ),

            # Evita duplicar la misma CUOF dentro de un Proyecto Especial POF.
            models.UniqueConstraint(
                fields=["proyecto_especial", "cuof"],
                condition=models.Q(proyecto_especial__isnull=False),
                name="uq_loc_pof_proyecto_cuof",
            ),
        ]

        indexes = [
            # Búsqueda principal: localizaciones de una Reunida por CUEANEXO.
            models.Index(
                fields=["reunida", "cueanexo"],
                name="idx_loc_pof_reunida_cue",
            ),

            # Búsqueda directa por CUEANEXO.
            models.Index(
                fields=["cueanexo"],
                name="idx_localizacion_pof_cueanexo",
            ),

            # Búsqueda por CUOF.
            models.Index(
                fields=["cuof"],
                name="idx_localizacion_pof_cuof",
            ),

            # Búsqueda principal: localizaciones de Proyectos Especiales POF por CUOF.
            models.Index(
                fields=["proyecto_especial", "cuof"],
                name="idx_loc_pof_proyecto_cuof",
            ),
        ]

    @property
    def cue_base(self):
        """
        Devuelve el CUE base calculado desde el CUEANEXO.
        No se guarda como columna para evitar dato derivado duplicado.
        """
        return self.cueanexo[:7] if self.cueanexo and len(self.cueanexo) >= 7 else ""

    @property
    def anexo_localizacion(self):
        """
        Devuelve los dos últimos dígitos del CUEANEXO.
        No se guarda como columna porque deriva directamente del CUEANEXO.
        """
        return self.cueanexo[-2:] if self.cueanexo and len(self.cueanexo) >= 9 else ""

    def clean(self):
        """
        Valida reglas internas de la localización antes de guardar.
        Controla cabecera, CUOF y formato del CUEANEXO cuando corresponde.
        """
        super().clean()

        self.cueanexo = str(self.cueanexo or "").strip()
        self.cuof = str(self.cuof or "").strip()
        self.cui = str(self.cui or "").strip()

        tiene_reunida = bool(self.reunida_id)
        tiene_proyecto = bool(self.proyecto_especial_id)

        if tiene_reunida == tiene_proyecto:
            raise ValidationError({
                "reunida": "La localización debe pertenecer a una única cabecera.",
                "proyecto_especial": "La localización debe pertenecer a una única cabecera.",
            })

        if not self.cuof:
            raise ValidationError({
                "cuof": "El CUOF es obligatorio."
            })

        if tiene_reunida and not self.cueanexo:
            raise ValidationError({
                "cueanexo": "El CUEANEXO es obligatorio para Reunidas POF."
            })

        if self.cueanexo and not self.cueanexo.isdigit():
            raise ValidationError({
                "cueanexo": "El CUEANEXO debe contener solo números."
            })

        if self.cueanexo and len(self.cueanexo) != 9:
            raise ValidationError({
                "cueanexo": "El CUEANEXO debe tener 9 dígitos."
            })

    def save(self, *args, **kwargs):
        """
        Ejecuta validaciones antes de guardar.
        Evita inconsistencias aunque el dato venga desde vista, admin o script.
        """
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        """
        Muestra una descripción legible de la localización POF.
        """
        if self.cueanexo:
            return f"{self.cueanexo} - CUOF {self.cuof}"
        return f"Proyectos Especiales POF - CUOF {self.cuof}"


# ANEXO POF LEGACY 0014 - SOLO COMPATIBILIDAD DE ESQUEMA --------------------------------------------------
#
# Estas clases preservan el estado ORM de las tablas creadas por la migración 0014
# hasta que exista una decisión explícita de retiro físico. Ningún circuito vigente
# de Anexo POF debe leerlas ni escribirlas. El dominio canónico comienza más abajo
# en CatalogoAnexoPof / AsociacionAnexoPof.
#
# No eliminar estas clases aisladamente: hacerlo haría que un futuro makemigrations
# proponga DeleteModel sobre las tablas legacy.

class AsignacionAnexoPof(models.Model):
    """
    MODELO LEGACY 0014. No utilizar en funcionalidad nueva ni vigente.

    Se conserva exclusivamente para mantener alineado el estado de modelos con las
    tablas históricas mientras el dominio canónico opera por CUE/CUOF.
    """

    reunida = models.ForeignKey(
        ReunidaPof,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="asignaciones_anexo_pof",
        verbose_name="Reunida POF",
    )

    proyecto_especial = models.ForeignKey(
        ProyectosEspecialesPof,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="asignaciones_anexo_pof",
        verbose_name="Proyecto Especial POF",
    )

    cueanexo = models.CharField(
        max_length=20,
        blank=True,
        default="",
        verbose_name="CUEANEXO",
    )

    cuof = models.CharField(
        max_length=100,
        blank=True,
        default="",
        verbose_name="CUOF",
    )

    codigo = models.CharField(
        max_length=50,
        blank=True,
        default="",
        verbose_name="Código Anexo POF",
    )

    usuario_actualizacion = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="asignaciones_anexo_pof_actualizadas",
        verbose_name="Usuario de última actualización",
    )

    creado_en = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Creado en",
    )

    actualizado_en = models.DateTimeField(
        auto_now=True,
        verbose_name="Actualizado en",
    )

    class Meta:
        db_table = '"reunidas_pof"."asignacion_anexo_pof"'
        verbose_name = "Asignación de Anexo POF"
        verbose_name_plural = "Asignaciones de Anexo POF"

        constraints = [
            models.CheckConstraint(
                condition=(
                    (
                        models.Q(
                            reunida__isnull=False,
                            proyecto_especial__isnull=True,
                            cuof="",
                        )
                        & ~models.Q(cueanexo="")
                    )
                    |
                    (
                        models.Q(
                            reunida__isnull=True,
                            proyecto_especial__isnull=False,
                            cueanexo="",
                        )
                        & ~models.Q(cuof="")
                    )
                ),
                name="ck_anexo_pof_identidad_cabecera",
            ),
            models.UniqueConstraint(
                fields=["reunida", "cueanexo"],
                condition=models.Q(reunida__isnull=False),
                name="uq_anexo_pof_reunida_cue",
            ),
            models.UniqueConstraint(
                fields=["proyecto_especial", "cuof"],
                condition=models.Q(proyecto_especial__isnull=False),
                name="uq_anexo_pof_proyecto_cuof",
            ),
        ]

    def clean(self):
        """
        Refuerza las dos identidades válidas y normaliza el código sin alterar su contenido.
        """
        super().clean()

        self.cueanexo = str(self.cueanexo or "").strip()
        self.cuof = str(self.cuof or "").strip()
        self.codigo = str(self.codigo or "").strip()

        tiene_reunida = bool(self.reunida_id)
        tiene_proyecto = bool(self.proyecto_especial_id)

        if tiene_reunida == tiene_proyecto:
            raise ValidationError({
                "reunida": "La asignación debe pertenecer a una única cabecera POF.",
                "proyecto_especial": "La asignación debe pertenecer a una única cabecera POF.",
            })

        if tiene_reunida:
            if not self.cueanexo:
                raise ValidationError({
                    "cueanexo": "El CUEANEXO es obligatorio para Anexo POF de Reunidas."
                })
            if not self.cueanexo.isdigit() or len(self.cueanexo) != 9:
                raise ValidationError({
                    "cueanexo": "El CUEANEXO debe tener exactamente 9 dígitos."
                })
            if self.cuof:
                raise ValidationError({
                    "cuof": "El CUOF debe quedar vacío para Anexo POF de Reunidas."
                })
        else:
            if not self.cuof:
                raise ValidationError({
                    "cuof": "El CUOF es obligatorio para Anexo POF de Proyecto Especial."
                })
            if self.cueanexo:
                raise ValidationError({
                    "cueanexo": "El CUEANEXO debe quedar vacío para Anexo POF de Proyecto Especial."
                })

        if "," in self.codigo:
            raise ValidationError({
                "codigo": "El Código Anexo POF no puede contener comas."
            })

        if any(not caracter.isprintable() for caracter in self.codigo):
            raise ValidationError({
                "codigo": "El Código Anexo POF no puede contener caracteres de control."
            })

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        if self.reunida_id:
            identidad = f"Reunida {self.reunida_id} - CUEANEXO {self.cueanexo}"
        else:
            identidad = (
                f"Proyecto Especial {self.proyecto_especial_id} - CUOF {self.cuof}"
            )
        return f"{identidad} - Anexo POF {self.codigo or 'sin asignar'}"


class HistorialAnexoPof(models.Model):
    """
    MODELO LEGACY 0014. No utilizar como historial vigente de Anexo POF.

    Se conserva junto con AsignacionAnexoPof únicamente por compatibilidad de
    esquema hasta un retiro físico explícito y seguro.
    """

    class Origen(models.TextChoices):
        CARGA = "CARGA", "Carga"
        GESTION = "GESTION", "Gestión"
        HERENCIA = "HERENCIA", "Herencia"

    asignacion = models.ForeignKey(
        AsignacionAnexoPof,
        on_delete=models.PROTECT,
        related_name="historial",
        verbose_name="Asignación Anexo POF",
    )

    codigo_anterior = models.CharField(
        max_length=50,
        blank=True,
        default="",
        verbose_name="Código anterior",
    )

    codigo_nuevo = models.CharField(
        max_length=50,
        blank=True,
        default="",
        verbose_name="Código nuevo",
    )

    origen = models.CharField(
        max_length=20,
        choices=Origen.choices,
        verbose_name="Origen",
    )

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="historial_anexos_pof",
        verbose_name="Usuario",
    )

    fecha = models.DateTimeField(
        default=timezone.now,
        verbose_name="Fecha",
    )

    class Meta:
        db_table = '"reunidas_pof"."historial_anexo_pof"'
        verbose_name = "Historial de Anexo POF"
        verbose_name_plural = "Historial de Anexos POF"
        ordering = ["-fecha", "-id"]

        constraints = [
            models.CheckConstraint(
                condition=~models.Q(codigo_anterior=models.F("codigo_nuevo")),
                name="ck_hist_anexo_pof_cambio_real",
            ),
        ]

        indexes = [
            models.Index(
                fields=["asignacion", "fecha"],
                name="idx_hist_anexo_pof_asig_fecha",
            ),
        ]

    def clean(self):
        """
        Evita movimientos vacíos y conserva el mismo formato permitido para el valor vigente.
        """
        super().clean()

        self.codigo_anterior = str(self.codigo_anterior or "").strip()
        self.codigo_nuevo = str(self.codigo_nuevo or "").strip()

        for campo, valor in (
            ("codigo_anterior", self.codigo_anterior),
            ("codigo_nuevo", self.codigo_nuevo),
        ):
            if "," in valor:
                raise ValidationError({
                    campo: "El Código Anexo POF no puede contener comas."
                })
            if any(not caracter.isprintable() for caracter in valor):
                raise ValidationError({
                    campo: "El Código Anexo POF no puede contener caracteres de control."
                })

        if self.codigo_anterior == self.codigo_nuevo:
            raise ValidationError({
                "codigo_nuevo": "El historial sólo puede registrar cambios reales."
            })

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return (
            f"{self.asignacion} - "
            f"{self.codigo_anterior or 'sin asignar'} -> "
            f"{self.codigo_nuevo or 'sin asignar'}"
        )


# ANEXO POF - DOMINIO CANONICO POR CUE/CUOF ------------------------------------------------------------

class CatalogoAnexoPof(models.Model):
    """
    Catálogo global de valores posibles de Código Anexo POF.

    El estado activo controla si el código puede utilizarse para nuevas
    asociaciones. Desactivarlo no modifica asociaciones CUE/CUOF existentes.
    El valor del código es inmutable una vez creado.
    """

    codigo = models.CharField(
        max_length=50,
        unique=True,
        verbose_name="Código Anexo POF",
    )

    activo = models.BooleanField(
        default=True,
        verbose_name="Activo",
    )

    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="catalogos_anexo_pof_creados",
        verbose_name="Creado por",
    )

    usuario_actualizacion = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="catalogos_anexo_pof_actualizados",
        verbose_name="Usuario de última actualización",
    )

    creado_en = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Creado en",
    )

    actualizado_en = models.DateTimeField(
        auto_now=True,
        verbose_name="Actualizado en",
    )

    class Meta:
        db_table = '"reunidas_pof"."catalogo_anexo_pof"'
        verbose_name = "Código Anexo POF"
        verbose_name_plural = "Catálogo de Anexo POF"
        ordering = ["codigo", "id"]

    def clean(self):
        super().clean()

        self.codigo = str(self.codigo or "").strip()

        if not self.codigo:
            raise ValidationError({
                "codigo": "El Código Anexo POF no puede quedar vacío."
            })

        if "," in self.codigo:
            raise ValidationError({
                "codigo": "El Código Anexo POF no puede contener comas."
            })

        if any(not caracter.isprintable() for caracter in self.codigo):
            raise ValidationError({
                "codigo": "El Código Anexo POF no puede contener caracteres de control."
            })

        if self.pk and not self._state.adding:
            codigo_original = (
                type(self).objects
                .filter(pk=self.pk)
                .values_list("codigo", flat=True)
                .first()
            )
            if codigo_original is not None and codigo_original != self.codigo:
                raise ValidationError({
                    "codigo": (
                        "Un Código Anexo POF existente no puede renombrarse. "
                        "Desactívelo y cree otro código si corresponde."
                    )
                })

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        estado = "activo" if self.activo else "inactivo"
        return f"{self.codigo} ({estado})"


class HistorialCatalogoAnexoPof(models.Model):
    """Auditoría de altas, bajas lógicas y reactivaciones del catálogo."""

    class Accion(models.TextChoices):
        CREAR = "CREAR", "Crear"
        DESACTIVAR = "DESACTIVAR", "Desactivar"
        REACTIVAR = "REACTIVAR", "Reactivar"

    class Origen(models.TextChoices):
        ADMINISTRACION = "ADMINISTRACION", "Administración"
        MIGRACION_LEGACY = "MIGRACION_LEGACY", "Migración legacy"

    catalogo = models.ForeignKey(
        CatalogoAnexoPof,
        on_delete=models.PROTECT,
        related_name="historial",
        verbose_name="Código Anexo POF",
    )

    accion = models.CharField(
        max_length=20,
        choices=Accion.choices,
        verbose_name="Acción",
    )

    origen = models.CharField(
        max_length=30,
        choices=Origen.choices,
        verbose_name="Origen",
    )

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="historial_catalogo_anexo_pof",
        verbose_name="Usuario",
    )

    fecha = models.DateTimeField(
        default=timezone.now,
        verbose_name="Fecha",
    )

    class Meta:
        db_table = '"reunidas_pof"."historial_catalogo_anexo_pof"'
        verbose_name = "Historial de catálogo Anexo POF"
        verbose_name_plural = "Historial de catálogo Anexo POF"
        ordering = ["-fecha", "-id"]
        indexes = [
            models.Index(
                fields=["catalogo", "fecha"],
                name="idx_hist_cat_anexo_fecha",
            ),
        ]

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.catalogo.codigo} - {self.accion}"


class AsociacionAnexoPof(models.Model):
    """
    Asociación canónica entre un Código Anexo POF y su propietario.

    El propietario es exactamente uno:
    - CUE para el dominio normal y para Proyecto Especial cuando existe CUE.
    - CUOF únicamente como fallback de Proyecto Especial cuando no existe CUE.

    Una asociación no se elimina físicamente: su vigencia se controla con activo.
    La identidad propietario+código es inmutable una vez creada.
    """

    cue = models.CharField(
        max_length=7,
        blank=True,
        default="",
        verbose_name="CUE",
    )

    cuof = models.CharField(
        max_length=100,
        blank=True,
        default="",
        verbose_name="CUOF",
    )

    codigo_catalogo = models.ForeignKey(
        CatalogoAnexoPof,
        on_delete=models.PROTECT,
        related_name="asociaciones",
        verbose_name="Código Anexo POF",
    )

    activo = models.BooleanField(
        default=True,
        verbose_name="Activo",
    )

    usuario_actualizacion = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="asociaciones_anexo_pof_actualizadas",
        verbose_name="Usuario de última actualización",
    )

    creado_en = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Creado en",
    )

    actualizado_en = models.DateTimeField(
        auto_now=True,
        verbose_name="Actualizado en",
    )

    class Meta:
        db_table = '"reunidas_pof"."asociacion_anexo_pof"'
        verbose_name = "Asociación Anexo POF"
        verbose_name_plural = "Asociaciones Anexo POF"
        constraints = [
            models.CheckConstraint(
                condition=(
                    (
                        ~models.Q(cue="")
                        & models.Q(cuof="")
                    )
                    |
                    (
                        models.Q(cue="")
                        & ~models.Q(cuof="")
                    )
                ),
                name="ck_asoc_anexo_pof_propietario",
            ),
            models.UniqueConstraint(
                fields=["cue", "codigo_catalogo"],
                condition=~models.Q(cue=""),
                name="uq_asoc_anexo_pof_cue_codigo",
            ),
            models.UniqueConstraint(
                fields=["cuof", "codigo_catalogo"],
                condition=~models.Q(cuof=""),
                name="uq_asoc_anexo_pof_cuof_codigo",
            ),
        ]
        indexes = [
            models.Index(
                fields=["cue", "activo"],
                name="idx_asoc_anexo_cue_activo",
            ),
            models.Index(
                fields=["cuof", "activo"],
                name="idx_asoc_anexo_cuof_activo",
            ),
        ]

    def clean(self):
        super().clean()

        self.cue = str(self.cue or "").strip()
        self.cuof = str(self.cuof or "").strip()

        tiene_cue = bool(self.cue)
        tiene_cuof = bool(self.cuof)

        if tiene_cue == tiene_cuof:
            raise ValidationError({
                "cue": "La asociación debe tener exactamente un propietario: CUE o CUOF.",
                "cuof": "La asociación debe tener exactamente un propietario: CUE o CUOF.",
            })

        if tiene_cue and (len(self.cue) != 7 or not self.cue.isdigit()):
            raise ValidationError({
                "cue": "El CUE debe tener exactamente 7 dígitos."
            })

        if tiene_cuof and any(not caracter.isprintable() for caracter in self.cuof):
            raise ValidationError({
                "cuof": "El CUOF no puede contener caracteres de control."
            })

        if self.pk and not self._state.adding:
            identidad_original = (
                type(self).objects
                .filter(pk=self.pk)
                .values("cue", "cuof", "codigo_catalogo_id")
                .first()
            )
            if identidad_original is not None:
                identidad_actual = {
                    "cue": self.cue,
                    "cuof": self.cuof,
                    "codigo_catalogo_id": self.codigo_catalogo_id,
                }
                if identidad_original != identidad_actual:
                    raise ValidationError({
                        "__all__": (
                            "La identidad CUE/CUOF + Código Anexo POF no puede modificarse. "
                            "Desactive la asociación y cree otra si corresponde."
                        )
                    })

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    @property
    def tipo_propietario(self):
        return "CUE" if self.cue else "CUOF"

    @property
    def propietario(self):
        return self.cue or self.cuof

    def __str__(self):
        estado = "activo" if self.activo else "inactivo"
        return (
            f"{self.tipo_propietario} {self.propietario} - "
            f"Anexo POF {self.codigo_catalogo.codigo} ({estado})"
        )


class HistorialAsociacionAnexoPof(models.Model):
    """Auditoría de altas, bajas lógicas y reactivaciones de asociaciones."""

    class Accion(models.TextChoices):
        ASOCIAR = "ASOCIAR", "Asociar"
        DESACTIVAR = "DESACTIVAR", "Desactivar"
        REACTIVAR = "REACTIVAR", "Reactivar"

    class Origen(models.TextChoices):
        ADMINISTRACION = "ADMINISTRACION", "Administración"
        MIGRACION_LEGACY = "MIGRACION_LEGACY", "Migración legacy"

    asociacion = models.ForeignKey(
        AsociacionAnexoPof,
        on_delete=models.PROTECT,
        related_name="historial",
        verbose_name="Asociación Anexo POF",
    )

    accion = models.CharField(
        max_length=20,
        choices=Accion.choices,
        verbose_name="Acción",
    )

    origen = models.CharField(
        max_length=30,
        choices=Origen.choices,
        verbose_name="Origen",
    )

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="historial_asociaciones_anexo_pof",
        verbose_name="Usuario",
    )

    fecha = models.DateTimeField(
        default=timezone.now,
        verbose_name="Fecha",
    )

    class Meta:
        db_table = '"reunidas_pof"."historial_asociacion_anexo_pof"'
        verbose_name = "Historial de asociación Anexo POF"
        verbose_name_plural = "Historial de asociaciones Anexo POF"
        ordering = ["-fecha", "-id"]
        indexes = [
            models.Index(
                fields=["asociacion", "fecha"],
                name="idx_hist_asoc_anexo_fecha",
            ),
        ]

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.asociacion} - {self.accion}"


# GUARDA LAS FOTOS DEL PADRÓN ASOCIADAS A UNA LOCALIZACIÓN POF ------------------------------------------------------------


class SnapshotPadronLocalizacionPof(models.Model):
    """
    Guarda una foto del padrón asociada a una Localización POF.
    Permite conservar datos históricos sin mezclar padrón dentro de LocalizacionPof.
    """

    class EstadoPadron(models.TextChoices):
        """
        Estado del padrón registrado en esta foto.
        """
        SIN_VERIFICAR = "SIN_VERIFICAR", "Sin verificar"
        VIGENTE = "VIGENTE", "Vigente"
        MODIFICADO = "MODIFICADO", "Modificado"
        BAJA = "BAJA", "Baja"
        NO_ENCONTRADO = "NO_ENCONTRADO", "No encontrado"

    class TipoSnapshot(models.TextChoices):
        """
        Tipo de foto guardada del padrón.
        """
        INICIAL = "INICIAL", "Inicial"
        VERIFICACION = "VERIFICACION", "Verificación"
        SINCRONIZACION = "SINCRONIZACION", "Sincronización"

    class TipoZonaEducativa(models.TextChoices):
        """
        Tipo de catálogo usado para la asignación de Zona Educativa.
        """
        URBANA = "URBANA", "Urbana"
        RURAL = "RURAL", "Rural"

    class OrigenDatos(models.TextChoices):
        """
        Indica si los datos congelados del padrón fueron tomados desde padrón
        o ingresados/modificados manualmente.
        """
        PADRON = "PADRON", "Ingreso por padrón"
        MANUAL = "MANUAL", "Ingreso manual"

    # Localización POF a la que pertenece esta foto del padrón.
    localizacion = models.ForeignKey(
        LocalizacionPof,
        on_delete=models.PROTECT,
        related_name="snapshots_padron",
        verbose_name="Localización POF",
    )

    # Tipo de snapshot: inicial, verificación o sincronización.
    tipo_snapshot = models.CharField(
        max_length=30,
        choices=TipoSnapshot.choices,
        default=TipoSnapshot.INICIAL,
        verbose_name="Tipo de snapshot",
    )

    # Origen de los datos congelados en esta foto del padrón.
    origen_datos = models.CharField(
        max_length=20,
        choices=OrigenDatos.choices,
        default=OrigenDatos.PADRON,
        verbose_name="Origen de datos",
    )

    # Indica si esta foto es la foto vigente usada por POF.
    vigente = models.BooleanField(
        default=True,
        verbose_name="Snapshot vigente",
    )

    # Estado del padrón registrado en esta foto.
    estado_padron = models.CharField(
        max_length=30,
        choices=EstadoPadron.choices,
        default=EstadoPadron.SIN_VERIFICAR,
        verbose_name="Estado del padrón",
    )

    # Estado real de la localización/CUEANEXO según padrón al momento del snapshot.
    estado_localizacion_padron = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Estado localización padrón",
    )

    # Estado real de la oferta según padrón al momento del snapshot.
    estado_oferta_padron = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Estado oferta padrón",
    )

    # Estado real del establecimiento según padrón al momento del snapshot.
    estado_establecimiento_padron = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Estado establecimiento padrón",
    )

    # Nombre de la oferta educativa asociada a la localización.
    oferta = models.TextField(
        blank=True,
        verbose_name="Oferta",
    )

    # Acrónimo o descripción corta de la oferta.
    acronimo = models.TextField(
        blank=True,
        verbose_name="Acrónimo",
    )

    # Nombre del establecimiento según padrón.
    nombre_establecimiento = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="Nombre del establecimiento",
    )

    # Número del establecimiento según padrón.
    numero_establecimiento = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Número del establecimiento",
    )

    # Región educativa/localización informada por padrón.
    region = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Región",
    )

    # Localidad de la localización.
    localidad = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="Localidad",
    )

    # Departamento de la localización.
    departamento = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="Departamento",
    )

    # Ámbito de la oferta/localización.
    ambito = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Ámbito",
    )

    # Categoría informada por el padrón.
    categoria = models.TextField(
        blank=True,
        verbose_name="Categoría",
    )

    # Jornada informada por el padrón.
    jornada = models.TextField(
        blank=True,
        verbose_name="Jornada",
    )

    # Ubicación textual principal.
    ubicacion = models.TextField(
        blank=True,
        verbose_name="Ubicación",
    )

    # Ubicación compuesta para mostrar localidad y departamento.
    ubicacion_localidad_departamento = models.TextField(
        blank=True,
        verbose_name="Ubicación localidad/departamento",
    )

    # Tipo de catálogo usado para la Zona Educativa congelada en esta foto.
    zona_educativa_tipo = models.CharField(
        max_length=10,
        choices=TipoZonaEducativa.choices,
        blank=True,
        default="",
        verbose_name="Tipo de Zona Educativa",
    )

    # Código o denominación de Zona Educativa vigente al momento del snapshot.
    zona_educativa = models.CharField(
        max_length=50,
        blank=True,
        default="",
        verbose_name="Zona Educativa",
    )

    # Puntaje de Zona Educativa vigente al momento del snapshot.
    puntos_zona_educativa = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name="Puntos Zona Educativa",
    )

    # Datos completos del padrón en formato JSON para conservar la foto original.
    datos_padron = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="Datos completos del padrón",
    )

    # Usuario que generó o confirmó esta foto del padrón.
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="snapshots_padron_pof",
        verbose_name="Usuario",
    )

    # Fecha lógica en la que se tomó esta foto del padrón.
    fecha_snapshot = models.DateTimeField(
        default=timezone.now,
        verbose_name="Fecha del snapshot",
    )

    # Fecha real en la que se creó el registro.
    creado_en = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Creado en",
    )

    class Meta:
        db_table = '"reunidas_pof"."snapshot_padron_localizacion_pof"'
        verbose_name = "Snapshot padrón localización POF"
        verbose_name_plural = "Snapshots padrón localización POF"

        constraints = [
            # Permite una sola foto vigente del padrón por localización.
            models.UniqueConstraint(
                fields=["localizacion"],
                condition=models.Q(vigente=True),
                name="uq_snapshot_padron_loc_vigente",
            ),

            # La Zona Educativa queda completamente ausente o completamente definida.
            models.CheckConstraint(
                condition=(
                    models.Q(
                        zona_educativa_tipo="",
                        zona_educativa="",
                        puntos_zona_educativa__isnull=True,
                    )
                    |
                    (
                        models.Q(zona_educativa_tipo__in=["URBANA", "RURAL"])
                        & ~models.Q(zona_educativa="")
                        & models.Q(puntos_zona_educativa__gt=0)
                    )
                ),
                name="ck_snapshot_pof_zona_integridad",
            ),
        ]

        indexes = [
            # Historial de snapshots por localización.
            models.Index(
                fields=["localizacion", "fecha_snapshot"],
                name="idx_snapshot_padron_loc_fecha",
            ),

            # Consulta rápida de la foto vigente.
            models.Index(
                fields=["localizacion", "vigente"],
                name="idx_snap_padron_loc_vig",
            ),

            # Filtro por estado del padrón.
            models.Index(
                fields=["estado_padron"],
                name="idx_snapshot_padron_estado",
            ),

            # Filtro por tipo de snapshot.
            models.Index(
                fields=["tipo_snapshot"],
                name="idx_snapshot_padron_tipo",
            ),
        ]

        ordering = ["-fecha_snapshot"]

    def clean(self):
        """
        Valida reglas internas del snapshot antes de guardar.
        Evita marcar una verificación simple como snapshot vigente y mantiene
        consistente la asignación histórica de Zona Educativa.
        """
        super().clean()

        if self.tipo_snapshot == self.TipoSnapshot.VERIFICACION and self.vigente:
            raise ValidationError({
                "vigente": "Una verificación no debería marcarse como snapshot vigente."
            })

        tiene_tipo_zona = bool(self.zona_educativa_tipo)
        tiene_zona = bool(self.zona_educativa)
        tiene_puntos_zona = self.puntos_zona_educativa is not None

        if any((tiene_tipo_zona, tiene_zona, tiene_puntos_zona)) and not all(
            (tiene_tipo_zona, tiene_zona, tiene_puntos_zona)
        ):
            raise ValidationError({
                "zona_educativa_tipo": (
                    "La Zona Educativa debe indicar tipo, zona y puntos en conjunto."
                ),
                "zona_educativa": (
                    "La Zona Educativa debe indicar tipo, zona y puntos en conjunto."
                ),
                "puntos_zona_educativa": (
                    "La Zona Educativa debe indicar tipo, zona y puntos en conjunto."
                ),
            })

        if tiene_puntos_zona and self.puntos_zona_educativa <= 0:
            raise ValidationError({
                "puntos_zona_educativa": (
                    "Los puntos de Zona Educativa deben ser mayores que cero."
                )
            })

    def save(self, *args, **kwargs):
        """
        Ejecuta validaciones antes de guardar.
        Esto mantiene trazabilidad y evita snapshots incoherentes.
        """
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        """
        Muestra una descripción legible del snapshot del padrón.
        """
        localizacion = self.localizacion.cueanexo or f"CUOF {self.localizacion.cuof}"
        return f"{localizacion} - {self.tipo_snapshot} - {self.fecha_snapshot:%d/%m/%Y %H:%M}"



#REPRESENTA EL MOMENTO EN EL QUE EL ADMINISTRATIVO TOCA GUARDAR -----------------------------------------------------------

class LoteCargaPof(models.Model):
    """
    Representa un lote de carga dentro de POF.
    Agrupa una o varias acciones guardadas juntas sobre una misma localización.
    """

    class TipoOperacion(models.TextChoices):
        """
        Tipos de operación que puede representar el lote de carga.
        """
        AFECTADO = "AFECTADO", "Afectado"
        MODIFICACION = "MODIFICACION", "Modificación"
        DESAFECTADO = "DESAFECTADO", "Desafectado"

    # Reunida a la que pertenece el lote de carga.
    reunida = models.ForeignKey(
        ReunidaPof,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="lotes_carga",
        verbose_name="Reunida POF",
    )

    # Proyectos Especiales POF a los que pertenece el lote de carga.
    proyecto_especial = models.ForeignKey(
        ProyectosEspecialesPof,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="lotes_carga",
        verbose_name="Proyectos Especiales POF",
    )

    # Localización sobre la que se realiza la operación.
    localizacion = models.ForeignKey(
        LocalizacionPof,
        on_delete=models.PROTECT,
        related_name="lotes_carga",
        verbose_name="Localización POF",
    )

    # Tipo de operación realizada en este lote.
    tipo_operacion = models.CharField(
        max_length=40,
        choices=TipoOperacion.choices,
        default=TipoOperacion.AFECTADO,
        verbose_name="Tipo de operación",
    )

    # Usuario que realizó la operación. Puede quedar vacío en cargas técnicas o migraciones.
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="lotes_carga_pof",
        verbose_name="Usuario",
    )

    # Fecha lógica de la operación. Es editable para permitir cargas históricas si hiciera falta.
    fecha = models.DateTimeField(
        default=timezone.now,
        verbose_name="Fecha de operación",
    )

    # Fecha real en la que el registro fue creado en el sistema.
    creado_en = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Creado en",
    )

    # Fecha real de la última modificación del registro.
    actualizado_en = models.DateTimeField(
        auto_now=True,
        verbose_name="Actualizado en",
    )

    class Meta:
        db_table = '"reunidas_pof"."lote_carga_pof"'
        verbose_name = "Lote de carga POF"
        verbose_name_plural = "Lotes de carga POF"

        constraints = [
            # Asegura que el lote pertenezca a una sola cabecera.
            models.CheckConstraint(
                condition=(
                    models.Q(reunida__isnull=False, proyecto_especial__isnull=True) |
                    models.Q(reunida__isnull=True, proyecto_especial__isnull=False)
                ),
                name="ck_lote_carga_pof_una_cabecera",
            ),
        ]

        indexes = [
            # Búsqueda de lotes por Reunida y localización.
            models.Index(
                fields=["reunida", "localizacion"],
                name="idx_lote_carga_pof_reunida_loc",
            ),

            # Búsqueda de lotes por Proyectos Especiales POF y localización.
            models.Index(
                fields=["proyecto_especial", "localizacion"],
                name="idx_lote_carga_pof_proy_loc",
            ),

            # Filtro por tipo de operación.
            models.Index(
                fields=["tipo_operacion"],
                name="idx_lote_carga_pof_tipo",
            ),

            # Ordenamiento o búsqueda por fecha de operación.
            models.Index(
                fields=["fecha"],
                name="idx_lote_carga_pof_fecha",
            ),

            # Búsqueda de lotes realizados por usuario.
            models.Index(
                fields=["usuario"],
                name="idx_lote_carga_pof_usuario",
            ),
        ]

    def clean(self):
        """
        Valida reglas internas del lote antes de guardar.
        Evita que el lote relacione una localización con una cabecera incorrecta.
        """
        super().clean()

        tiene_reunida = bool(self.reunida_id)
        tiene_proyecto = bool(self.proyecto_especial_id)

        if tiene_reunida == tiene_proyecto:
            raise ValidationError({
                "reunida": "El lote debe pertenecer a una única cabecera.",
                "proyecto_especial": "El lote debe pertenecer a una única cabecera.",
            })

        try:
            localizacion = self.localizacion
        except ObjectDoesNotExist:
            raise ValidationError({
                "localizacion": "El lote debe tener una localización."
            })

        if tiene_reunida:
            if localizacion.reunida_id != self.reunida_id or localizacion.proyecto_especial_id:
                raise ValidationError({
                    "localizacion": "La localización no pertenece a la Reunida indicada."
                })
            return

        if localizacion.proyecto_especial_id != self.proyecto_especial_id or localizacion.reunida_id:
            raise ValidationError({
                "localizacion": "La localización no pertenece a los Proyectos Especiales POF indicados."
        })

    def save(self, *args, **kwargs):
        """
        Ejecuta validaciones antes de guardar.
        Esto protege la consistencia aunque el dato venga desde vista, admin o script.
        """
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        """
        Muestra una descripción legible del lote de carga.
        """
        cabecera = self.reunida or self.proyecto_especial
        return f"{self.get_tipo_operacion_display()} - {cabecera} - {self.localizacion} - {self.fecha:%d/%m/%Y %H:%M}"
    
#REPRESENTA EL CARGO CARGADO POR POF -------------------------------------------------------------------------------------------


class CargoPof(models.Model):
    """
    Representa un cargo cargado en POF para una localización.
    Cada registro guarda CEIC, ofertas, cantidad, unidad, puntos, total y estado POF.
    """

    class EstadoPof(models.TextChoices):
        """
        Estado funcional del cargo dentro de POF.
        AFECTADO cuenta en los totales.
        DESAFECTADO queda guardado pero no cuenta.
        """
        AFECTADO = "AFECTADO", "Afectado"
        DESAFECTADO = "DESAFECTADO", "Desafectado"

    class UnidadCantidad(models.TextChoices):
        """
        Indica qué representa el valor cargado en cantidad.
        La cantidad puede ser cantidad de cargos u horas cátedra.
        """
        CARGO = "CARGO", "Cargo"
        HORA_CATEDRA = "HORA_CATEDRA", "Hora cátedra"

    # Localización POF a la que pertenece el cargo.
    localizacion = models.ForeignKey(
        LocalizacionPof,
        on_delete=models.PROTECT,
        related_name="cargos",
        verbose_name="Localización POF",
    )

    # Lote de carga en el que se registró este cargo.
    lote_carga = models.ForeignKey(
        LoteCargaPof,
        on_delete=models.PROTECT,
        related_name="cargos",
        verbose_name="Lote de carga POF",
    )

    # Código CEIC del cargo.
    ceic = models.PositiveIntegerField(
        db_index=True,
        verbose_name="CEIC",
        help_text="Código CEIC asociado al cargo.",
    )

    # Descripción del cargo según CEIC al momento de la carga.
    cargo = models.TextField(
        blank=True,
        verbose_name="Cargo",
    )

    # Ofertas educativas asociadas específicamente a este cargo, separadas por coma.
    oferta = models.TextField(
        blank=True,
        default="",
        verbose_name="Ofertas",
    )

    # Filas oficiales seleccionadas para reconstruir y validar el selector de ofertas.
    ofertas_seleccionadas = models.JSONField(
        default=list,
        blank=True,
        verbose_name="Ofertas seleccionadas",
    )

    observacion = models.TextField(
        blank=True,
        default="",
        verbose_name="Observación",
    )

    # Cantidad cargada. Puede representar cargos u horas cátedra según unidad_cantidad.
    cantidad = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0"),
        verbose_name="Cantidad",
    )

    # Indica qué significa la cantidad cargada.
    unidad_cantidad = models.CharField(
        max_length=20,
        choices=UnidadCantidad.choices,
        default=UnidadCantidad.CARGO,
        verbose_name="Unidad de cantidad",
    )

    # Puntos asignados al cargo según CEIC.
    puntos_asignados = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0"),
        verbose_name="Puntos asignados",
    )

    # Total calculado por el sistema: cantidad * puntos_asignados.
    total = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("0"),
        editable=False,
        verbose_name="Total",
    )

    # Estado del cargo dentro de POF.
    estado_pof = models.CharField(
        max_length=20,
        choices=EstadoPof.choices,
        default=EstadoPof.AFECTADO,
        verbose_name="Estado POF",
    )

    # Foto del CEIC al momento de guardar el cargo.
    snapshot_ceic = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="Snapshot CEIC",
    )

    # Fecha real en la que se creó el registro.
    creado_en = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Creado en",
    )

    # Fecha real de la última modificación del registro.
    actualizado_en = models.DateTimeField(
        auto_now=True,
        verbose_name="Actualizado en",
    )

    class Meta:
        db_table = '"reunidas_pof"."cargo_pof"'
        verbose_name = "Cargo POF"
        verbose_name_plural = "Cargos POF"

        constraints = [
            # Refuerza que el CEIC sea válido.
            models.CheckConstraint(
                condition=models.Q(ceic__gt=0),
                name="ck_cargo_pof_ceic_gt_0",
            ),

            # Evita cantidades negativas.
            models.CheckConstraint(
                condition=models.Q(cantidad__gte=0),
                name="ck_cargo_pof_cantidad_gte_0",
            ),

            # Un cargo afectado siempre debe tener cantidad positiva.
            models.CheckConstraint(
                condition=(
                    models.Q(estado_pof="DESAFECTADO")
                    | models.Q(cantidad__gt=0)
                ),
                name="ck_cargo_pof_afectado_cant_gt0",
            ),

            # Evita puntos negativos.
            models.CheckConstraint(
                condition=models.Q(puntos_asignados__gte=0),
                name="ck_cargo_pof_puntos_gte_0",
            ),

            # Evita totales negativos.
            models.CheckConstraint(
                condition=models.Q(total__gte=0),
                name="ck_cargo_pof_total_gte_0",
            ),
        ]

        indexes = [
            # Búsqueda de cargos por localización y estado.
            models.Index(
                fields=["localizacion", "estado_pof"],
                name="idx_cargo_pof_loc_estado",
            ),

            # Búsqueda directa por CEIC.
            models.Index(
                fields=["ceic"],
                name="idx_cargo_pof_ceic",
            ),

            # Filtro por estado POF.
            models.Index(
                fields=["estado_pof"],
                name="idx_cargo_pof_estado",
            ),

            # Búsqueda de cargos asociados a un lote.
            models.Index(
                fields=["lote_carga"],
                name="idx_cargo_pof_lote",
            ),

            # Útil para consultar cargos por localización y CEIC.
            models.Index(
                fields=["localizacion", "ceic"],
                name="idx_cargo_pof_loc_ceic",
            ),
        ]

    def clean(self):
        """
        Valida reglas internas antes de guardar el cargo.
        Controla valores numéricos y consistencia entre localización y lote.
        """
        super().clean()

        self.cantidad = self.cantidad or Decimal("0")
        self.puntos_asignados = self.puntos_asignados or Decimal("0")
        self.oferta = str(self.oferta or "").strip()
        self.observacion = str(self.observacion or "").strip()

        if not isinstance(self.ofertas_seleccionadas, list):
            raise ValidationError({
                "ofertas_seleccionadas": "Las ofertas seleccionadas deben ser una lista."
            })

        if not self.ceic or self.ceic <= 0:
            raise ValidationError({
                "ceic": "El CEIC debe ser mayor a 0."
            })

        if self.cantidad < 0:
            raise ValidationError({
                "cantidad": "La cantidad debe ser mayor o igual a 0."
            })

        if self.estado_pof == self.EstadoPof.AFECTADO and self.cantidad <= 0:
            raise ValidationError({
                "cantidad": "Para afectar el cargo, la cantidad debe ser superior a 0."
            })

        if self.puntos_asignados < 0:
            raise ValidationError({
                "puntos_asignados": "Los puntos asignados no pueden ser negativos."
            })

        try:
            localizacion = self.localizacion
            lote_carga = self.lote_carga
        except ObjectDoesNotExist:
            return

        if lote_carga.localizacion != localizacion:
            raise ValidationError({
                "lote_carga": "El lote de carga no pertenece a la localización indicada."
            })

    def save(self, *args, **kwargs):
        """
        Calcula el total y ejecuta validaciones antes de guardar.
        Evita depender del cálculo realizado en el frontend.
        """
        self.cantidad = _decimal_o_cero(self.cantidad)
        self.puntos_asignados = _decimal_dos_decimales(self.puntos_asignados)
        self.total = _decimal_dos_decimales(self.cantidad * self.puntos_asignados)

        self.full_clean()
        super().save(*args, **kwargs)

    @property
    def esta_afectado(self):
        """
        Indica si el cargo cuenta en los totales de la Reunida.
        """
        return self.estado_pof == self.EstadoPof.AFECTADO

    @property
    def esta_desafectado(self):
        """
        Indica si el cargo está guardado pero no cuenta en los totales.
        """
        return self.estado_pof == self.EstadoPof.DESAFECTADO

    @property
    def es_hora_catedra(self):
        """
        Indica si la cantidad cargada representa horas cátedra.
        """
        return self.unidad_cantidad == self.UnidadCantidad.HORA_CATEDRA

    def __str__(self):
        """
        Muestra una descripción legible del cargo POF.
        """
        localizacion = self.localizacion.cueanexo or f"CUOF {self.localizacion.cuof}"
        return f"{localizacion} - CEIC {self.ceic} - {self.get_estado_pof_display()}"

#GUARDA HISTORIAL DE MOVIMIENTOS DE CARGOS -------------------------------------------------------------------------------


class MovimientoCargoPof(models.Model):
    """
    Registra el historial de acciones realizadas sobre un cargo POF.
    Permite auditar cargos afectados, modificaciones y cargos desafectados.
    """

    class TipoMovimiento(models.TextChoices):
        """
        Tipos de movimiento posibles sobre un cargo POF.
        """
        AFECTADO = "AFECTADO", "Afectado"
        MODIFICACION = "MODIFICACION", "Modificación"
        DESAFECTADO = "DESAFECTADO", "Desafectado"

    # Cargo afectado por el movimiento.
    cargo = models.ForeignKey(
        CargoPof,
        on_delete=models.PROTECT,
        related_name="movimientos",
        verbose_name="Cargo POF",
    )

    # Lote de carga u operación administrativa que originó el movimiento.
    lote_carga = models.ForeignKey(
        LoteCargaPof,
        on_delete=models.PROTECT,
        related_name="movimientos",
        verbose_name="Lote de carga POF",
    )

    # Snapshot del padrón/localización usado al momento del movimiento.
    snapshot_padron = models.ForeignKey(
        SnapshotPadronLocalizacionPof,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="movimientos_cargos",
        verbose_name="Snapshot padrón",
        help_text="Snapshot de padrón/localización vigente al momento del movimiento.",
    )

    # Tipo de acción realizada sobre el cargo.
    tipo_movimiento = models.CharField(
        max_length=40,
        choices=TipoMovimiento.choices,
        verbose_name="Tipo de movimiento",
    )

    # Estado anterior del cargo, si corresponde.
    estado_anterior = models.CharField(
        max_length=30,
        blank=True,
        verbose_name="Estado anterior",
    )

    # Estado nuevo del cargo, si corresponde.alta
    estado_nuevo = models.CharField(
        max_length=30,
        blank=True,
        verbose_name="Estado nuevo",
    )

    # Valores antes del cambio, útil para auditoría.
    valores_anteriores = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="Valores anteriores",
    )

    # Valores después del cambio, útil para auditoría.
    valores_nuevos = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="Valores nuevos",
    )

    # Observación opcional para explicar el motivo del movimiento.
    observacion = models.TextField(
        blank=True,
        verbose_name="Observación",
    )

    # Usuario que realizó el movimiento.
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="movimientos_cargos_pof",
        verbose_name="Usuario",
    )

    # Fecha lógica del movimiento. Es editable para permitir cargas históricas si hiciera falta.
    fecha = models.DateTimeField(
        default=timezone.now,
        verbose_name="Fecha del movimiento",
    )

    # Fecha real en la que se creó el registro en el sistema.
    creado_en = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Creado en",
    )

    class Meta:
        db_table = '"reunidas_pof"."movimiento_cargo_pof"'
        verbose_name = "Movimiento de cargo POF"
        verbose_name_plural = "Movimientos de cargos POF"

        indexes = [
            # Historial de un cargo ordenado por fecha.
            models.Index(
                fields=["cargo", "fecha"],
                name="idx_mov_cargo_pof_cargo_fecha",
            ),

            # Movimientos originados por un lote de carga.
            models.Index(
                fields=["lote_carga", "fecha"],
                name="idx_mov_cargo_pof_lote_fecha",
            ),

            # Movimientos asociados a un snapshot de padrón/localización.
            models.Index(
                fields=["snapshot_padron", "fecha"],
                name="idx_mov_cargo_pof_snap_fecha",
            ),

            # Filtro por tipo de movimiento.
            models.Index(
                fields=["tipo_movimiento"],
                name="idx_mov_cargo_pof_tipo",
            ),

            # Filtro por usuario.
            models.Index(
                fields=["usuario", "fecha"],
                name="idx_mov_cargo_pof_usr",
            ),

            # Ordenamiento general por fecha.
            models.Index(
                fields=["fecha"],
                name="idx_mov_cargo_pof_fecha",
            ),
        ]

        ordering = ["-fecha"]

    def clean(self):
        """
        Valida reglas internas antes de guardar el movimiento.
        Evita que el movimiento relacione un cargo con un lote de otra localización.
        """
        super().clean()

        try:
            cargo = self.cargo
            lote_carga = self.lote_carga
        except ObjectDoesNotExist:
            return

        if lote_carga.localizacion != cargo.localizacion:
            raise ValidationError({
                "lote_carga": "El lote de carga no pertenece a la misma localización que el cargo."
            })

        if self.snapshot_padron_id:
            if self.snapshot_padron.localizacion_id != cargo.localizacion_id:
                raise ValidationError({
                    "snapshot_padron": "El snapshot no pertenece a la misma localización que el cargo."
                })

        if self.tipo_movimiento == self.TipoMovimiento.AFECTADO:
            if self.estado_nuevo and self.estado_nuevo != CargoPof.EstadoPof.AFECTADO:
                raise ValidationError({
                    "estado_nuevo": "Un movimiento Afectado debe dejar el cargo en estado AFECTADO."
                })

        if self.tipo_movimiento == self.TipoMovimiento.DESAFECTADO:
            if self.estado_nuevo and self.estado_nuevo != CargoPof.EstadoPof.DESAFECTADO:
                raise ValidationError({
                    "estado_nuevo": "Un movimiento Desafectado debe dejar el cargo en estado DESAFECTADO."
                })

    def save(self, *args, **kwargs):
        """
        Ejecuta validaciones antes de guardar el movimiento.
        Esto protege la trazabilidad aunque el registro venga desde vista, admin o script.
        """
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        """
        Muestra una descripción legible del movimiento.
        """
        return f"{self.tipo_movimiento} - CEIC {self.cargo.ceic} - {self.fecha:%d/%m/%Y %H:%M}"



class VCapaUnicaOfertasAnt(models.Model):
    id = models.IntegerField(primary_key=True)

    cueanexo = models.CharField(max_length=20, blank=True, null=True)
    padron_cueanexo = models.CharField(max_length=20, blank=True, null=True)

    nom_est = models.CharField(max_length=255, blank=True, null=True)
    nro_est = models.CharField(max_length=100, blank=True, null=True)

    acronimo = models.TextField(blank=True, null=True)
    oferta = models.TextField(blank=True, null=True)
    etiqueta = models.TextField(blank=True, null=True)

    ambito = models.CharField(max_length=100, blank=True, null=True)
    sector = models.CharField(max_length=100, blank=True, null=True)
    region_loc = models.CharField(max_length=100, blank=True, null=True)

    ref_loc = models.TextField(blank=True, null=True)
    calle = models.TextField(blank=True, null=True)
    numero = models.CharField(max_length=50, blank=True, null=True)

    localidad = models.CharField(max_length=255, blank=True, null=True)
    departamento = models.CharField(max_length=255, blank=True, null=True)

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
        db_table = '"public"."v_capa_unica_ofertas_ant"'
        verbose_name = "Vista capa única oferta"
        verbose_name_plural = "Vista capa única ofertas"

    @property
    def cue_base(self):
        valor = str(self.padron_cueanexo or self.cueanexo or "")
        return valor[:7] if len(valor) >= 7 else ""

    @property
    def anexo_localizacion(self):
        valor = str(self.padron_cueanexo or self.cueanexo or "")
        return valor[-2:] if len(valor) >= 9 else ""

    @property
    def ubicacion_completa(self):
        partes = [
            self.ref_loc or self.calle,
            self.localidad,
            self.departamento,
        ]
        return " - ".join(str(parte) for parte in partes if parte)

    def __str__(self):
        return f"{self.padron_cueanexo or self.cueanexo} - {self.nom_est}"
