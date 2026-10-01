# ============================================================
# IMPORTS BASE Y DEPENDENCIAS DE BASE DE DATOS
# ============================================================
# Este archivo define modelos propios del módulo BNH Alumnos sin
# duplicar datos maestros. Los catálogos ya existentes se referencian
# desde bnhpersonas mediante ForeignKey.
#
# Datos propios de este módulo: alumno, tutor, vínculo parental, obra
# social, discapacidad y planes sociales cargados para el alumno.
# Datos externos reutilizados: tipos de documento, países, provincias,
# localidades, sexo, parentescos, nacionalidades y demás catálogos.
#
"""Modelos y reglas de negocio persistentes del modulo BNH Alumnos.

Este archivo define las tablas propias del esquema ``bnh_alumno`` y las
referencias a catalogos externos de ``bnhpersonas``. Tambien concentra
validaciones que deben cumplirse aunque el guardado no venga desde los
ModelForm de ``forms.py``.
"""

# ============================================================
import re
import unicodedata
from django.conf import settings
from django.db import models
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator

# Catálogos compartidos de bnhpersonas: se reutilizan para mantener una
# única fuente de verdad y evitar tablas duplicadas en BNH Alumnos.
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
    TipoComunidadOriginaria,
    TipoLenguaOriginaria,
    validar_cuil,
    TipoDiscapacidad,
    EstadosCiviles,
    CodAreasTelefonos,
)


DOCUMENTO_DNI = 1
DOCUMENTO_NO_POSEE = 11
DOCUMENTO_EN_TRAMITE = 12
DOCUMENTO_EXTRANJERO = 13


def _texto_tipo_documento(tipo_documento):
    """Normaliza el texto visible del catálogo para tolerar PK no canónicos."""

    try:
        texto = str(tipo_documento or "").strip().upper()
        return "".join(
            caracter
            for caracter in unicodedata.normalize("NFKD", texto)
            if not unicodedata.combining(caracter)
        )
    except Exception:
        return ""


def clasificar_tipo_documento(tipo_documento):
    """Clasifica tipos BNH por código y, como respaldo, por su etiqueta visible."""

    tipo_id = getattr(tipo_documento, "pk", tipo_documento)
    try:
        tipo_id = int(tipo_id)
    except (TypeError, ValueError):
        tipo_id = None

    texto = _texto_tipo_documento(tipo_documento)
    # Los estados especiales tienen prioridad sobre coincidencias parciales
    # como "DNI" dentro de la descripción del catálogo.
    if tipo_id == DOCUMENTO_NO_POSEE or "NO POSEE" in texto:
        return "no_posee"
    if tipo_id == DOCUMENTO_EN_TRAMITE or "TRAMITE" in texto:
        return "en_tramite"
    if tipo_id == DOCUMENTO_EXTRANJERO or "EXTRANJ" in texto:
        return "extranjero"
    if tipo_id == DOCUMENTO_DNI or texto == "DNI" or "DNI" in texto:
        return "dni"
    if (
        re.search(r"\b(?:CI|LC|LE)\b", texto)
        or "CEDULA DE IDENTIDAD" in texto
        or "CEDULA MERCOSUR" in texto
    ):
        return "numerico"
    return "otro"


def normalizar_documento_bnh(tipo_documento, valor, nombre="Número de documento"):
    """Aplica las reglas documentales BNH sin asumir que todo documento es DNI."""

    clase = clasificar_tipo_documento(tipo_documento)
    texto = str(valor or "").strip().upper()

    if clase == "no_posee":
        if texto:
            raise ValidationError(
                f"{nombre}: no debe informarse cuando el tipo de documento es 'No posee'."
            )
        return None

    if clase == "en_tramite":
        # El requerimiento permite ausencia de número y no fija un formato
        # adicional cuando se informa; no se inventan restricciones.
        return texto or None

    if not texto:
        raise ValidationError(f"{nombre} es obligatorio para el tipo de documento seleccionado.")

    if clase in {"dni", "numerico"}:
        normalizado = re.sub(r"[.\-\s]", "", texto)
        if not normalizado.isdigit():
            raise ValidationError(f"{nombre}: el tipo seleccionado admite únicamente números.")
        if clase == "dni":
            if len(normalizado) == 7:
                normalizado = normalizado.zfill(8)
            if len(normalizado) != 8:
                raise ValidationError(
                    "DNI inválido: debe contener 8 dígitos; para DNI menores a 10 millones use cero inicial."
                )
        return normalizado

    if clase == "extranjero":
        if not re.fullmatch(r"[A-Z0-9]+", texto):
            raise ValidationError(
                f"{nombre}: el documento extranjero admite únicamente letras mayúsculas y números."
            )
        return texto

    # Para códigos no documentados en el requerimiento adjunto no se inventan
    # restricciones adicionales: se conserva el valor, normalizado a mayúsculas.
    return texto


def normalizar_cuil_opcional(valor, nombre="CUIL"):
    """Valida CUIL sólo cuando fue informado y conserva ausencia real como None."""

    texto = str(valor or "").strip()
    if not texto:
        return None
    if not re.fullmatch(r"[0-9.\-\s]+", texto):
        raise ValidationError(f"{nombre} inválido: use únicamente números y separadores habituales.")
    cuil = re.sub(r"\D", "", texto)
    if len(cuil) != 11:
        raise ValidationError(f"{nombre} debe tener 11 dígitos.")
    validar_cuil(cuil)
    return cuil


def normalizar_componente_id_jurisdiccional(valor):
    """Normaliza una parte del identificador jurisdiccional de respaldo.

    BNH indica concatenar los seis datos de identidad cuando la jurisdicción no
    dispone de un identificador nominal. Para que el resultado sea estable y no
    contenga signos de puntuación, se usan mayúsculas ASCII y sólo letras/números.
    """

    texto = str(valor or "").strip().upper()
    texto = "".join(
        caracter
        for caracter in unicodedata.normalize("NFKD", texto)
        if not unicodedata.combining(caracter)
    )
    return re.sub(r"[^A-Z0-9]", "", texto)


def generar_id_persona_jurisdiccional_bnh(
    *,
    apellidos,
    nombres,
    tipo_documento,
    nro_documento,
    fecha_nacimiento,
    sexo,
):
    """Construye la identidad jurisdiccional con la regla canónica BNH."""

    tipo_id = getattr(tipo_documento, "pk", tipo_documento)
    sexo_id = getattr(sexo, "pk", sexo)
    documento = normalizar_documento_bnh(
        tipo_documento or tipo_id,
        nro_documento,
    )
    fecha = (
        fecha_nacimiento.strftime("%d%m%Y")
        if fecha_nacimiento
        else ""
    )
    componentes = (
        apellidos,
        nombres,
        tipo_id,
        documento,
        fecha,
        sexo_id,
    )
    identificador = "".join(
        normalizar_componente_id_jurisdiccional(componente)
        for componente in componentes
    )
    if not identificador:
        raise ValidationError(
            {"id_persona_jurisdiccional": "No se pudo generar el identificador jurisdiccional."}
        )
    return identificador


def validar_cuil_con_documento(cuil, tipo_documento, nro_documento, nombre="CUIL"):
    """CUIL sólo corresponde a DNI argentino y, si hay DNI, debe coincidir."""

    if not cuil:
        return

    clase_documento = clasificar_tipo_documento(tipo_documento)
    if clase_documento != "dni":
        raise ValidationError(
            f"{nombre} sólo puede informarse cuando el tipo de documento es DNI."
        )

    if not nro_documento:
        return

    dni = str(nro_documento).zfill(8)
    if cuil[2:10] != dni:
        raise ValidationError(
            f"{nombre} no corresponde al DNI informado."
        )


def _provincia_id_de_localidad(localidad):
    """Obtiene el id de provincia grabado en una localidad de catalogo."""

    return getattr(localidad, "c_provincia_id", None)


def _localidad_corresponde_a_provincia(localidad, provincia):
    """Valida la correspondencia provincia-localidad sin exigir ambos datos."""

    if not localidad or not provincia:
        return True
    return str(_provincia_id_de_localidad(localidad) or "") == str(getattr(provincia, "pk", provincia) or "")


def _validar_contacto_telefono(errors, codigo_area, telefono, requerido=False):
    """Valida codigo de area y numero local, acumulando errores por campo.

    El numero se guarda separado del codigo de area para conservar la clave del
    catalogo; luego cada modelo arma ``telefono_normalizado`` cuando corresponde.
    """

    numero = str(telefono or "").strip()
    tiene_codigo = bool(codigo_area)
    if not numero:
        if requerido:
            errors["telefono"] = "Debe ingresar el numero de telefono."
        if tiene_codigo:
            errors["telefono"] = "Debe ingresar el numero de telefono si selecciona codigo de area."
        if requerido and not tiene_codigo:
            errors["codigo_area"] = "Debe seleccionar el codigo de area."
        return None

    if not numero.isdigit() or not re.fullmatch(r"\d{6,8}", numero):
        errors["telefono"] = "El numero local debe tener entre 6 y 8 digitos."
    if not tiene_codigo:
        errors["codigo_area"] = "Debe seleccionar el codigo de area si ingresa telefono."
    return numero

# ============================================================
# PERMISOS DE ACCESO AL MODULO BNH ALUMNOS
# ============================================================
class BnhRolUsuario(models.Model):
    """Rol externo usado para autorizar acceso al modulo BNH Alumnos.

    ``managed=False`` indica que Django no administra esta tabla: pertenece al
    esquema de usuarios existente y solo se consulta desde este modulo.
    """

    nombre = models.CharField(max_length=100)

    class Meta:
        managed = False
        db_table = "usuarios_rol"
        verbose_name = "Rol de usuario"
        verbose_name_plural = "Roles de usuario"

    def __str__(self):
        return self.nombre or ""


class BnhUsuarioPerfil(models.Model):
    """Perfil externo que une usuario Django con un rol funcional BNH.

    Tambien es ``managed=False`` porque la tabla fisica ya existe fuera de las
    migraciones de BNH Alumnos.
    """

    usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.DO_NOTHING,
        db_column="usuario_id",
        related_name="perfil_bnhalumnos",
    )
    rol = models.ForeignKey(
        BnhRolUsuario,
        on_delete=models.DO_NOTHING,
        db_column="rol_id",
        related_name="perfiles_bnhalumnos",
    )

    class Meta:
        managed = False
        db_table = "usuarios_perfilusuario"
        verbose_name = "Perfil de usuario para BNH Alumnos"
        verbose_name_plural = "Perfiles de usuario para BNH Alumnos"

    def __str__(self):
        usuario_txt = getattr(self.usuario, "username", self.usuario_id)
        rol_txt = getattr(self.rol, "nombre", "")
        return f"{usuario_txt} - {rol_txt}"


ROLES_BNH_ALUMNOS = {
    "Administrador",
    "Gestor",
    "Director de Servicios Complementarios",
    "Director de Modalidad Especial",
}


def obtener_rol_usuario_bnh(user):
    """
    Devuelve el nombre del rol del usuario logueado.
    Usa usuarios_perfilusuario -> usuarios_rol.
    """
    if not user or not user.is_authenticated:
        return None

    try:
        perfil = (
            BnhUsuarioPerfil.objects
            .select_related("rol")
            .get(usuario=user)
        )
        return (perfil.rol.nombre or "").strip()
    except BnhUsuarioPerfil.DoesNotExist:
        return None


def usuario_puede_ver_bnh_alumnos(user):
    """
    Permite acceso a BNH Alumnos solo a roles autorizados.
    """
    rol = obtener_rol_usuario_bnh(user)

    if not rol:
        return False

    return rol in ROLES_BNH_ALUMNOS


def usuario_es_admin_bnh(user):
    """Indica si el usuario tiene permisos administrativos dentro de BNH."""

    return obtener_rol_usuario_bnh(user) == "Administrador"


# ============================================================
# MODELO PRINCIPAL DE ALUMNOS
# ============================================================
# Este bloque define la tabla propia "alumnos". Los datos operativos
# del alumno se guardan aquí; bnhpersonas se usa solo como fuente de
# catálogos y longitudes compatibles.
#
# La función bnh_max_length() solo toma el tamaño máximo de campos
# ya existentes en Personas, por ejemplo apellido y nombre, para
# mantener consistencia de longitudes. No crea ni modifica registros
# en Personas.
#
# Los ForeignKey hacia DocumentoTipo, Sexo, Provincias, Pais,
# Localidades y otros catálogos no copian datos de esas tablas. Solo
# guardan en "alumnos" el identificador del registro relacionado.
#
# ============================================================
def bnh_max_length(modelo, campo):
    """Devuelve la longitud máxima de un campo de otro modelo del proyecto."""

    return modelo._meta.get_field(campo).max_length


class CatalogoSinoTipo(models.Model):
    """Catalogo propio para respuestas SI/NO/Sin informacion.

    Se usa en campos condicionales del alumno, por ejemplo discapacidad, PPI y
    pertenencia a pueblo indigena.
    """

    SIN_INFORMACION = -2
    SI = 1
    NO = 2

    codigo = models.SmallIntegerField(primary_key=True)
    descripcion = models.CharField(max_length=50)

    class Meta:
        db_table = '"bnh_alumno"."catalogo_sino_tipo"'
        verbose_name = "Catálogo Sí/No/Sin información"
        verbose_name_plural = "Catálogo Sí/No/Sin información"
        ordering = ["codigo"]

    def __str__(self):
        return self.descripcion


class Alumno(models.Model):
    """Alumno cargado por BNH Alumnos y eje de sus relaciones asociadas.

    Los campos de identidad, contacto, salud y observaciones son propios
    del módulo. Los ForeignKey apuntan a catálogos externos reutilizados
    desde bnhpersonas y se protegen con PROTECT para preservar integridad
    histórica si alguien intenta eliminar un catálogo usado.
    """
      
    # Identificación del alumno: documento y CUIL quedan indexados para
    # búsquedas frecuentes desde la pantalla de carga.
    id = models.BigAutoField(primary_key=True)
    apellidos = models.CharField(max_length=bnh_max_length(Personas, "apellido"))
    nombres = models.CharField(max_length=bnh_max_length(Personas, "nombre"))
    tipo_doc = models.ForeignKey(
        DocumentoTipo, 
        on_delete=models.PROTECT
        )
    nro_doc = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        db_index=True,
    )
    cuil = models.CharField(
        max_length=11,
        null=True,
        blank=True,
        db_index=True,
    )
    # Referencia técnica a SGE cuando la persona fue localizada allí. Se guarda
    # separada del PK local y del identificador jurisdiccional porque cumplen
    # funciones distintas. PostgreSQL admite múltiples NULL con unique=True.
    id_persona_sge = models.PositiveBigIntegerField(
        null=True,
        blank=True,
        unique=True,
        db_index=True,
    )
    id_persona_jurisdiccional = models.CharField(
        max_length=512,
        unique=True,
        db_index=True,
        null=True,
        blank=True,
    )
    fecha_nacimiento = models.DateField()
    lugar_nacimiento = models.CharField(
        max_length=100,
        blank=True,
        default="",
    )

    # Catálogos de nacimiento y residencia. PROTECT evita que una baja de
    # catálogo deje alumnos apuntando a referencias inexistentes.
    sexo = models.ForeignKey(Sexo, on_delete=models.PROTECT)
    nacionalidad = models.ForeignKey(
        Nacionalidad,
        on_delete=models.PROTECT,
        db_column="c_nacionalidad",
        default=-2,
    )
    pais_nacimiento = models.ForeignKey(
        Pais,
        on_delete=models.PROTECT,
        db_column="pais_nacimiento",
        related_name="alumnos_pais_nacimiento",
    )
    prov_nacimiento = models.ForeignKey(
        Provincias,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        db_column="prov_nacimiento",
        related_name="alumnos_provincia_nacimiento",
    )
    loc_nacimiento = models.ForeignKey(
        Localidades,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        db_column="loc_nacimiento",
        related_name="alumnos_localidad_nacimiento",
        verbose_name="Localidad de nacimiento",
    )
    pais_residencia = models.ForeignKey(
        Pais,
        on_delete=models.PROTECT,
        db_column="pais_residencia",
        related_name="alumnos_pais_residencia",
    )
    prov_residencia = models.ForeignKey(
        Provincias,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        db_column="prov_residencia",
        related_name="alumnos_provincia_residencia",
    )

    loc_residencia = models.ForeignKey(
        Localidades,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        db_column="loc_residencia",
        related_name="alumnos_localidad_residencia",
    )

    # Catálogos socioeducativos, culturales y de salud asociados al alumno.
    est_civil = models.ForeignKey(
        EstadosCiviles,
        on_delete=models.PROTECT,
        db_column="est_civil",
        related_name="alumnos",
    )

    pertenece_pueblo_indigena = models.ForeignKey(
        CatalogoSinoTipo,
        on_delete=models.PROTECT,
        db_column="cd_pueblo_indigena",
        related_name="alumnos_pueblo_indigena",
        default=CatalogoSinoTipo.SIN_INFORMACION,
    )

    comunidad_originaria = models.ForeignKey(
        TipoComunidadOriginaria,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        db_column="id_comunidad_originaria",
        related_name="alumnos_comunidad_originaria",
    )

    lengua_originaria = models.ForeignKey(
    TipoLenguaOriginaria,
    on_delete=models.PROTECT,
    null=True,
    blank=True,
    )

    tiene_discapacidad = models.ForeignKey(
        CatalogoSinoTipo,
        on_delete=models.PROTECT,
        db_column="cd_discapacidad",
        related_name="alumnos_discapacidad_sino",
        default=CatalogoSinoTipo.SIN_INFORMACION,
    )
    tiene_ppi = models.ForeignKey(
        CatalogoSinoTipo,
        on_delete=models.PROTECT,
        db_column="c_ppi",
        related_name="alumnos_ppi",
        default=CatalogoSinoTipo.SIN_INFORMACION,
        verbose_name="Proyecto Pedagógico Individual",
    )
    # Datos de contacto y medidas propios de BNH Alumnos.
    codigo_area = models.ForeignKey(
        CodAreasTelefonos,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        db_column="codigo_area",
        related_name="alumnos_codigo_area",
    )
    telefono = models.CharField(
        max_length=8,
        null=True,
        blank=True,
        validators=[
            RegexValidator(
                r"^\d{6,8}$",
                message="Ingrese solo el número local (6 a 8 dígitos, sin código de área)",
            )
        ],
    )
    telefono_normalizado = models.CharField(
        max_length=15,
        null=True,
        blank=True,
        db_index=True,
    )
    es_celular = models.BooleanField(default=False)
    whatsapp = models.BooleanField(default=False)
    email = models.CharField(max_length=150, blank=True)
    talla = models.DecimalField(max_digits=5, decimal_places=2)
    peso = models.DecimalField(max_digits=5, decimal_places=2)
    
    fecha_registro = models.DateTimeField(auto_now_add=True)
    fecha_modificacion = models.DateTimeField(auto_now=True)

    usuario_modificacion = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="alumnos_modificados",
    )

    cuil_usuario_modificacion = models.CharField(
        max_length=11,
        blank=True,
        default="",
        db_index=True,
    )

    observaciones = models.TextField(blank=True)

    def pais_nacimiento_es_argentina(self):
        """Determina si aplican las reglas de nacimiento argentino."""

        pais_id = self.pais_nacimiento_id
        try:
            pais_txt = str(self.pais_nacimiento or "").upper() if pais_id else ""
        except Pais.DoesNotExist:
            pais_txt = ""
        return pais_id == 14 or "ARGENT" in pais_txt

    def pais_residencia_es_argentina(self):
        """Determina si provincia/localidad de residencia deben completarse."""

        pais_id = self.pais_residencia_id
        try:
            pais_txt = str(self.pais_residencia or "").upper() if pais_id else ""
        except Pais.DoesNotExist:
            pais_txt = ""
        return pais_id == 14 or "ARGENT" in pais_txt

    def clean(self):
        """Normaliza documento/CUIL y aplica validaciones antes de guardar."""

        super().clean()
        errors = {}

        # Nacimiento argentino exige provincia/localidad del catalogo. Para
        # nacimiento extranjero se limpian esas referencias y se usa texto libre.
        self.lugar_nacimiento = str(self.lugar_nacimiento or "").strip().upper()
        if self.pais_nacimiento_es_argentina():
            self.lugar_nacimiento = ""
            if not self.prov_nacimiento_id:
                errors["prov_nacimiento"] = "La provincia de nacimiento es obligatoria para Argentina."
            if not self.loc_nacimiento_id:
                errors["loc_nacimiento"] = "La localidad de nacimiento es obligatoria para Argentina."
            if (
                self.prov_nacimiento_id
                and self.loc_nacimiento_id
                and not _localidad_corresponde_a_provincia(self.loc_nacimiento, self.prov_nacimiento_id)
            ):
                errors["loc_nacimiento"] = "La localidad de nacimiento no corresponde a la provincia seleccionada."
        else:
            self.prov_nacimiento = None
            self.loc_nacimiento = None
            if self.pais_nacimiento_id and not self.lugar_nacimiento:
                errors["lugar_nacimiento"] = (
                    "El lugar de nacimiento es obligatorio cuando el pais de nacimiento no es Argentina."
                )

        # BNH pide provincia/localidad de residencia únicamente para Argentina.
        if not self.pais_residencia_id:
            errors["pais_residencia"] = "Debe seleccionar el pais de residencia."
        elif self.pais_residencia_es_argentina():
            if not self.prov_residencia_id:
                errors["prov_residencia"] = "La provincia de residencia es obligatoria para Argentina."
            if not self.loc_residencia_id:
                errors["loc_residencia"] = "La localidad de residencia es obligatoria para Argentina."
            if (
                self.prov_residencia_id
                and self.loc_residencia_id
                and not _localidad_corresponde_a_provincia(self.loc_residencia, self.prov_residencia_id)
            ):
                errors["loc_residencia"] = "La localidad de residencia no corresponde a la provincia seleccionada."
        else:
            self.prov_residencia = None
            self.loc_residencia = None

        # WhatsApp solo queda habilitado si hay telefono celular completo.
        telefono = _validar_contacto_telefono(errors, self.codigo_area_id, self.telefono)
        if telefono:
            self.telefono = telefono
        else:
            self.telefono = None
            self.whatsapp = False
            self.es_celular = False
        if not self.es_celular:
            self.whatsapp = False

        # Documento y CUIL son atributos de identidad, pero CUIL no es
        # requisito de existencia de la persona. La regla documental depende
        # del tipo seleccionado y contempla No posee / En trámite / extranjero.
        tipo_documento = None
        if self.tipo_doc_id:
            try:
                tipo_documento = self.tipo_doc
            except DocumentoTipo.DoesNotExist:
                tipo_documento = self.tipo_doc_id

        try:
            self.nro_doc = normalizar_documento_bnh(
                tipo_documento or self.tipo_doc_id,
                self.nro_doc,
            )
        except ValidationError as exc:
            errors["nro_doc"] = exc.messages

        try:
            self.cuil = normalizar_cuil_opcional(self.cuil, "CUIL del alumno")
        except ValidationError as exc:
            errors["cuil"] = exc.messages

        if self.cuil and "nro_doc" not in errors:
            try:
                validar_cuil_con_documento(
                    self.cuil,
                    tipo_documento or self.tipo_doc_id,
                    self.nro_doc,
                    "CUIL del alumno",
                )
            except ValidationError as exc:
                errors["cuil"] = exc.messages

        # Ninguna coincidencia se fusiona silenciosamente. CUIL y
        # tipo+documento identifican candidatos fuertes y deben ser únicos
        # dentro de BNH Alumnos cuando están informados.
        if self.cuil and "cuil" not in errors:
            duplicado_cuil = type(self).objects.filter(cuil=self.cuil)
            if self.pk:
                duplicado_cuil = duplicado_cuil.exclude(pk=self.pk)
            if duplicado_cuil.exists():
                errors["cuil"] = "Ya existe otro alumno cargado con este CUIL."

        if self.nro_doc and self.tipo_doc_id and "nro_doc" not in errors:
            duplicado_documento = type(self).objects.filter(
                tipo_doc_id=self.tipo_doc_id,
                nro_doc__iexact=self.nro_doc,
            )
            if self.pk:
                duplicado_documento = duplicado_documento.exclude(pk=self.pk)
            if duplicado_documento.exists():
                errors["nro_doc"] = (
                    "Ya existe otro alumno con el mismo tipo y número de documento."
                )

        # Nombre + fecha de nacimiento + sexo son datos de apoyo para
        # detectar candidatos, no una clave única: pueden existir homónimos reales.
        # Las coincidencias débiles se resuelven en la interfaz con confirmación
        # explícita y nunca se fusionan automáticamente desde el modelo.

        # Comunidad originaria depende de la respuesta del catalogo SI/NO.
        if self.pertenece_pueblo_indigena_id == CatalogoSinoTipo.SI:
            if not self.comunidad_originaria_id:
                errors["comunidad_originaria"] = (
                    "Debe indicar la comunidad originaria cuando pertenece a pueblo indígena."
                )
        elif self.comunidad_originaria_id:
            errors["comunidad_originaria"] = (
                "Solo debe indicar comunidad originaria si pertenece a pueblo indígena."
            )

        if errors:
            raise ValidationError(errors)


    def normalizar_telefono(self):
        """Arma telefono internacional a partir de codigo de area y numero local."""

        if not self.telefono or not self.codigo_area:
            return None

        numero = re.sub(r"\D", "", self.telefono)
        codigo = str(self.codigo_area.codigo)
        return f"+54{codigo}{numero}"

    def generar_id_persona_jurisdiccional(self):
        """Genera el identificador jurisdiccional inicial de la persona.

        El identificador jurisdiccional es independiente de SGE y siempre se
        construye con los seis datos de identidad BNH: apellidos, nombres, tipo
        y número de documento, fecha de nacimiento y sexo. id_persona_sge se
        conserva aparte únicamente como referencia técnica a SGE.

        El valor jurisdiccional se genera una sola vez; cambios posteriores de
        los datos personales o del vínculo con SGE no lo recalculan.
        """

        tipo_documento = None
        if self.tipo_doc_id:
            try:
                tipo_documento = self.tipo_doc
            except DocumentoTipo.DoesNotExist:
                tipo_documento = self.tipo_doc_id

        return generar_id_persona_jurisdiccional_bnh(
            apellidos=self.apellidos,
            nombres=self.nombres,
            tipo_documento=tipo_documento or self.tipo_doc_id,
            nro_documento=self.nro_doc,
            fecha_nacimiento=self.fecha_nacimiento,
            sexo=self.sexo_id,
        )


    def save(self, *args, **kwargs):
        """Fuerza validación integral y preserva la identidad jurisdiccional estable."""

        self.telefono_normalizado = self.normalizar_telefono()
        self.cuil = normalizar_cuil_opcional(self.cuil, "CUIL del alumno")

        identificador_original = None
        if self.pk:
            original = type(self).objects.filter(pk=self.pk).only(
                "id_persona_jurisdiccional",
            ).first()
            if original:
                identificador_original = original.id_persona_jurisdiccional

        if identificador_original:
            # El identificador permanente nunca se recalcula por cambios de
            # CUIL, documento, nombre, aparición posterior en SGE u otros datos.
            self.id_persona_jurisdiccional = identificador_original
        else:
            # En una persona nueva (o un registro antiguo todavía sin ID), el
            # valor siempre lo determina la regla canónica del modelo.
            self.id_persona_jurisdiccional = self.generar_id_persona_jurisdiccional()

        self.full_clean()
        super().save(*args, **kwargs)
        
    def __str__(self):
        """Representacion breve del alumno para admin, logs y relaciones."""

        documento = self.nro_doc or "SIN DOCUMENTO"
        return f"{self.apellidos}, {self.nombres} - {documento}"

    class Meta:
        # db_table conserva el esquema físico existente. Los índices aceleran
        # búsquedas por documento/email sin cambiar la lógica del modelo.
        db_table = '"bnh_alumno"."alumnos"'
        verbose_name = "Alumno"
        verbose_name_plural = "Alumnos"

        indexes = [
            models.Index(fields=["nro_doc"], name="idx_alumnos_nro_doc"),
            models.Index(fields=["email"], name="idx_alumnos_email"),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["cuil"],
                condition=models.Q(cuil__isnull=False) & ~models.Q(cuil=""),
                name="uq_bnh_alumno_cuil_informado",
            ),
            models.UniqueConstraint(
                fields=["tipo_doc", "nro_doc"],
                condition=models.Q(nro_doc__isnull=False) & ~models.Q(nro_doc=""),
                name="uq_bnh_alumno_tipo_documento",
            ),
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
   
class TipoObraSocial(models.Model):
    c_os = models.IntegerField(primary_key=True)
    descrip_os = models.CharField(max_length=50)

    class Meta:
        db_table = '"bnh_alumno"."tipo_obra_social"'
        verbose_name = "Tipo de obra social"
        verbose_name_plural = "Tipos de obra social"
        ordering = ["c_os"]

    def __str__(self):
        return self.descrip_os


class CatalogoObraSocial(models.Model):
    """Catalogo propio de obras sociales seleccionables en el modal."""

    c_os = models.IntegerField(primary_key=True)
    descrip_os = models.CharField(max_length=200)
    sigla = models.CharField(max_length=50, blank=True)

    class Meta:
        db_table = '"bnh_alumno"."catalogo_obra_social"'
        verbose_name = "Catálogo obra social"
        verbose_name_plural = "Catálogo obras sociales"
        ordering = ["descrip_os"]

    def __str__(self):
        """Muestra sigla y descripcion cuando ambas estan disponibles."""

        if self.sigla:
            return f"{self.sigla} - {self.descrip_os}"
        return self.descrip_os


class ObraSocial(models.Model):
    """Obra social asociada a un alumno, usando el catálogo propio del módulo."""
    
    id = models.BigAutoField(primary_key=True)

    # Relación obligatoria con Alumno. PROTECT impide borrar un alumno si
    # todavía tiene obra social asociada en esta tabla histórica.
    id_alumno = models.ForeignKey(
        Alumno,
        on_delete=models.PROTECT,
        db_column="id_alumno",
        related_name="obras_sociales",
    )

    # El tipo usa el catálogo propio; acá se guarda solo la referencia y los
    # datos propios de la obra social cargada para el alumno.
    tipo_obra = models.ForeignKey(
        TipoObraSocial,
        on_delete=models.PROTECT,
        db_column="tipo_obra",
        related_name="obras_sociales",
    )

    nombre_obra = models.ForeignKey(
        CatalogoObraSocial,
        on_delete=models.PROTECT,
        db_column="nombre_obra",
        related_name="obras_sociales",
    )

    # Vigencia y descripción de la cobertura registrada en BNH Alumnos.
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField(null=True, blank=True)
    descripcion = models.TextField(blank=True)
    estado = models.CharField(max_length=20)
    created_at = models.DateTimeField(auto_now_add=True)

    def clean(self):
        """Valida que la vigencia de la obra social sea cronologica."""

        super().clean()

        if self.fecha_inicio and self.fecha_fin and self.fecha_fin < self.fecha_inicio:
            raise ValidationError({
                "fecha_fin": "La fecha de fin no puede ser anterior a la fecha de inicio."
            })

    def save(self, *args, **kwargs):
        """Ejecuta validaciones del modelo antes de persistir la obra social."""

        self.full_clean()
        super().save(*args, **kwargs)

    class Meta:
        # Tabla propia del esquema bnh_alumno; el índice por alumno favorece
        # la reconstrucción de relaciones al editar una carga existente.
        db_table = '"bnh_alumno"."obra_social"'
        verbose_name = "Obra social"
        verbose_name_plural = "Obras sociales"
        indexes = [
            models.Index(fields=["id_alumno"], name="idx_obra_social_alumno"),
        ]

    def __str__(self):
        """Representacion de la cobertura vinculada al alumno."""

        return f"{self.nombre_obra} - {self.id_alumno}"
# ============================================================
# VÍNCULO PARENTAL ENTRE ALUMNO Y TUTOR
# ============================================================
# Este modelo define la tabla "parental". No representa al alumno ni al
# tutor en sí, sino la relación funcional entre ambos.
#
# La relación con Alumno se guarda mediante la columna id_alumno.
# Un alumno puede tener uno o varios parentales asociados, por ejemplo
# madre, padre, tutor legal o responsable.
#
# RelacionParentesco viene de bnhpersonas y se protege con PROTECT por
# ser catálogo compartido. La restricción única evita duplicar el mismo
# par alumno-tutor dentro de esta tabla.
# ============================================================

class Parental(models.Model):
    """Relación entre un alumno y un tutor con parentesco y observaciones."""
    
    id = models.BigAutoField(primary_key=True)

    # Extremos del vínculo: un Parental siempre une un alumno con un tutor.
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
    
    # Parentesco es catálogo compartido; las observaciones describen detalles
    # propios de esta relación.
    parentesco = models.ForeignKey(
        RelacionParentesco,
        on_delete=models.PROTECT,
        db_column="id_parentesco",
        related_name="parentales",
    )

    observaciones = models.TextField(blank=True)
    
    class Meta:
        # Los índices cubren las consultas naturales desde alumno o desde tutor.
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
        """Muestra tutor y parentesco de la relacion parental."""

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
# La relación con TipoDiscapacidad usa PROTECT porque ese modelo funciona
# como catálogo externo. Borrar una discapacidad del catálogo no debería
# borrar registros históricos de alumnos.
# ============================================================
class Discapacidad(models.Model):
    """Detalle histórico de discapacidades asociadas a un alumno."""
    
    id = models.BigAutoField(primary_key=True)

    # Relación con el alumno y tipo de discapacidad del catálogo externo.
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

    # Datos propios del registro: vigencia, porcentaje, observación y CUD.
    fecha_inicio = models.DateField(null=True, blank=True)
    fecha_fin = models.DateField(null=True, blank=True)
    porcentaje = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    observaciones = models.TextField(blank=True)
    certificado_cud = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def clean(self):
        """Valida reglas condicionales y rangos del detalle de discapacidad."""

        super().clean()
        errors = {}

        if self.id_alumno_id:
            tiene_discapacidad = getattr(self.id_alumno, "tiene_discapacidad_id", None)
            if tiene_discapacidad != CatalogoSinoTipo.SI:
                errors["id_alumno"] = (
                    "Solo se pueden cargar detalles de discapacidad si el alumno tiene discapacidad indicada como SI."
                )

        if self.fecha_inicio and self.fecha_fin and self.fecha_fin < self.fecha_inicio:
            errors["fecha_fin"] = "La fecha de fin no puede ser anterior a la fecha de inicio."

        if self.porcentaje is not None and (self.porcentaje < 0 or self.porcentaje > 100):
            errors["porcentaje"] = "El porcentaje de discapacidad debe estar entre 0 y 100."

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        """Ejecuta clean() antes de guardar para proteger altas directas."""

        self.full_clean()
        super().save(*args, **kwargs)

    class Meta:
        # Tabla propia para detalles por alumno; el índice compuesto permite
        # filtrar por alumno y tipo de discapacidad.
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
        """Representacion del detalle de discapacidad por alumno."""

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
# La relación con TipoPlanesSociales usa PROTECT porque ese modelo
# funciona como catálogo externo. Borrar un beneficio del catálogo no
# debería borrar registros históricos de alumnos.
#
# ============================================================

class PlanesSociales(models.Model):
    """Plan social o beneficio asociado históricamente a un alumno."""
    
    id = models.BigAutoField(primary_key=True)

    # El alumno es dueño del registro; el beneficio se toma del catálogo
    # TipoPlanesSociales para evitar duplicar nombres de planes.
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

    # Datos variables del beneficio para este alumno: vigencia, monto y estado.
    descripcion = models.CharField(max_length=150)
    fecha_desde = models.DateField()
    fecha_hasta = models.DateField(null=True, blank=True)
    monto = models.DecimalField(max_digits=12, decimal_places=2)
    estado = models.CharField(max_length=20)
    observaciones = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def clean(self):
        """Valida la vigencia cronologica del beneficio social."""

        super().clean()

        if self.fecha_desde and self.fecha_hasta and self.fecha_hasta < self.fecha_desde:
            raise ValidationError({
                "fecha_hasta": "La fecha hasta no puede ser anterior a la fecha desde."
            })

    def save(self, *args, **kwargs):
        """Valida el plan social antes de persistirlo."""

        self.full_clean()
        super().save(*args, **kwargs)

    class Meta:
        # La tabla guarda datos propios del beneficio del alumno y solo
        # referencia el catálogo de tipos mediante id_beneficio.
        db_table = '"bnh_alumno"."planes_sociales"'
        verbose_name = "Plan social"
        verbose_name_plural = "Planes sociales"
        indexes = [
            models.Index(fields=["id_alumno"], name="idx_planes_alumno"),
        ]

    def __str__(self):
        """Representacion del plan social asociado al alumno."""

        return f"{self.id_alumno} - {self.id_beneficio}"


      
# ============================================================
# TUTOR / RESPONSABLE DEL ALUMNO
# ============================================================
# Tutor es una entidad propia de BNH Alumnos. No se escribe en Personas:
# solo se reutilizan longitudes y catálogos compartidos para mantener
# consistencia con el resto del sistema.
# ============================================================
      
class Tutor(models.Model):
    """Tutor con datos propios, reutilizable en vínculos parentales."""
      
    # CUIL es opcional: un responsable extranjero puede no tenerlo.
    # Tipo + documento identifican candidatos cuando existe documentación.
    id = models.BigAutoField(primary_key=True)
    cuil_tutor = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        db_index=True,
    )
    apellidos = models.CharField(max_length=bnh_max_length(Personas, "apellido"))
    nombres = models.CharField(max_length=bnh_max_length(Personas, "nombre"))
    tipo_doc = models.ForeignKey(DocumentoTipo, on_delete=models.PROTECT)
    nro_doc = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        db_index=True,
    )
    fecha_nac = models.DateField()
    nacionalidad = models.ForeignKey(Nacionalidad, on_delete=models.PROTECT)
    pais_nac = models.ForeignKey(
        Pais,
        on_delete=models.PROTECT,
        db_column="pais_nac",
        related_name="tutores_pais_nacimiento",
    )
    nivel_formacion = models.ForeignKey(
        NivelFormacion,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        db_column="c_nivel_formacion",
        related_name="tutores",
    )

    # Datos laborales y de actualización propios del tutor.
    ocupacion = models.CharField(max_length=100, blank=True, default="")
    fecha_actualiza = models.DateField(auto_now=True)

    # Residencia del tutor: provincia y localidad son catálogos externos
    # protegidos para no borrar tutores ante cambios en datos maestros.
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

    # Domicilio y vías de contacto del tutor, separados de los datos del alumno.
    cod_postal = models.CharField(max_length=20)
    calle = models.CharField(max_length=150)
    nro = models.CharField(max_length=20)
    piso = models.CharField(max_length=10, blank=True)
    dpto = models.CharField(max_length=10, blank=True)
    mail = models.EmailField(max_length=150, blank=True)
    codigo_area = models.ForeignKey(
        CodAreasTelefonos,
        on_delete=models.PROTECT,
        db_column="codigo_area",
        related_name="tutores_codigo_area",
    )
    telefono = models.CharField(
        max_length=8,
        validators=[
            RegexValidator(
                r"^\d{6,8}$",
                message="Ingrese solo el número local (6 a 8 dígitos, sin código de área)",
            )
        ],
    )
    telefono_normalizado = models.CharField(
        max_length=15,
        null=True,
        blank=True,
        db_index=True,
    )
    es_celular = models.BooleanField(default=False)
    whatsapp = models.BooleanField(default=False)

    class Meta:
        # Tabla propia del módulo e índices para búsquedas de alta frecuencia.
        db_table = '"bnh_alumno"."tutores"'
        verbose_name = "Tutor"
        verbose_name_plural = "Tutores"
        indexes = [
            models.Index(fields=["cuil_tutor"], name="idx_tutores_cuil"),
            models.Index(fields=["nro_doc"], name="idx_tutores_nro_doc"),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["cuil_tutor"],
                condition=models.Q(cuil_tutor__isnull=False) & ~models.Q(cuil_tutor=""),
                name="uq_bnh_tutor_cuil_informado",
            ),
            models.UniqueConstraint(
                fields=["tipo_doc", "nro_doc"],
                condition=models.Q(nro_doc__isnull=False) & ~models.Q(nro_doc=""),
                name="uq_bnh_tutor_tipo_documento",
            ),
        ]

    def clean(self):
        """Normaliza documento/CUIL y aplica validaciones antes de guardar."""

        super().clean()
        errors = {}

        # Tutor tiene contacto obligatorio porque funciona como responsable o
        # referente del alumno dentro de la relacion parental. Su identidad,
        # en cambio, no depende de disponer de CUIL.
        tipo_documento = None
        if self.tipo_doc_id:
            try:
                tipo_documento = self.tipo_doc
            except DocumentoTipo.DoesNotExist:
                tipo_documento = self.tipo_doc_id

        try:
            self.nro_doc = normalizar_documento_bnh(
                tipo_documento or self.tipo_doc_id,
                self.nro_doc,
                "Número de documento del tutor",
            )
        except ValidationError as exc:
            errors["nro_doc"] = exc.messages

        try:
            self.cuil_tutor = normalizar_cuil_opcional(
                self.cuil_tutor,
                "CUIL del tutor",
            )
        except ValidationError as exc:
            errors["cuil_tutor"] = exc.messages

        if self.cuil_tutor and "nro_doc" not in errors:
            try:
                validar_cuil_con_documento(
                    self.cuil_tutor,
                    tipo_documento or self.tipo_doc_id,
                    self.nro_doc,
                    "CUIL del tutor",
                )
            except ValidationError as exc:
                errors["cuil_tutor"] = exc.messages

        if self.cuil_tutor and "cuil_tutor" not in errors:
            duplicado_cuil = type(self).objects.filter(cuil_tutor=self.cuil_tutor)
            if self.pk:
                duplicado_cuil = duplicado_cuil.exclude(pk=self.pk)
            if duplicado_cuil.exists():
                errors["cuil_tutor"] = "Ya existe otro tutor cargado con este CUIL."

        if self.nro_doc and self.tipo_doc_id and "nro_doc" not in errors:
            duplicado_documento = type(self).objects.filter(
                tipo_doc_id=self.tipo_doc_id,
                nro_doc__iexact=self.nro_doc,
            )
            if self.pk:
                duplicado_documento = duplicado_documento.exclude(pk=self.pk)
            if duplicado_documento.exists():
                errors["nro_doc"] = (
                    "Ya existe otro tutor con el mismo tipo y número de documento."
                )

        if not self.prov_resid_id:
            errors["prov_resid"] = "Debe seleccionar la provincia de residencia del tutor."
        if not self.loc_resid_id:
            errors["loc_resid"] = "Debe seleccionar la localidad de residencia del tutor."
        if (
            self.prov_resid_id
            and self.loc_resid_id
            and not _localidad_corresponde_a_provincia(self.loc_resid, self.prov_resid_id)
        ):
            errors["loc_resid"] = "La localidad de residencia del tutor no corresponde a la provincia seleccionada."

        telefono = _validar_contacto_telefono(errors, self.codigo_area_id, self.telefono, requerido=True)
        if telefono:
            self.telefono = telefono
        else:
            self.whatsapp = False
            self.es_celular = False
        if not self.es_celular:
            self.whatsapp = False

        if errors:
            raise ValidationError(errors)

    def normalizar_telefono(self):
        """Arma telefono internacional del tutor para busqueda o consulta."""

        if not self.telefono or not self.codigo_area:
            return None

        numero = re.sub(r"\D", "", self.telefono)
        codigo = str(self.codigo_area.codigo)
        return f"+54{codigo}{numero}"

    def save(self, *args, **kwargs):
        """Actualiza telefono normalizado y valida antes de guardar tutor."""

        self.telefono_normalizado = self.normalizar_telefono()
        self.cuil_tutor = normalizar_cuil_opcional(self.cuil_tutor, "CUIL del tutor")
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        """Representacion breve del tutor para tablas y relaciones."""

        documento = self.nro_doc or "SIN DOCUMENTO"
        return f"{self.apellidos}, {self.nombres} - {documento}"
      
      
############################
# FUNCIONES DE VALIDACION
############################
def validar_dni(dni):
    """Normaliza y valida DNI argentino cuando el tipo de documento corresponde."""

    dni = str(dni or "").strip().upper()

    # Normaliza formatos comunes: 12.345.678, 12-345-678, 12 345 678
    dni = re.sub(r"[.\-\s]", "", dni)

    if not dni:
        raise ValidationError(
            "DNI inválido: es obligatorio cuando el tipo de documento es DNI."
        )

    if not re.fullmatch(r"\d{7,8}", dni):
        raise ValidationError(
            "DNI inválido: debe contener solo números y tener 8 dígitos."
        )

    return dni.zfill(8)
