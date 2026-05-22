import re

from django.conf import settings
from django.db import models
from django.db.models import CharField, F, Func, Value
from django.db.models.functions import Trim, Upper


ACRONIMO_CEF = "CEF"
OFERTA_SERVICIOS_COMPLEMENTARIOS = "Común - Servicios complementarios"
LONGITUD_CUEANEXO = 9
PADRON_DB_ALIAS = "default"


class CefPadronOferta(models.Model):
    """
    Modelo de integración CEF contra la vista de Padrón.

    No representa una tabla propia del módulo CEF.
    No debe generar migraciones.
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
        verbose_name = "Oferta CEF desde Padrón"
        verbose_name_plural = "Ofertas CEF desde Padrón"

    def __str__(self):
        cueanexo = self.cueanexo or ""
        nombre = self.nom_est or ""
        return f"{cueanexo} - {nombre}".strip(" -")


class CefRolUsuario(models.Model):
    """
    Rol global del usuario.

    Lee la tabla existente usuarios_rol.
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
    Perfil global del usuario para resolver rol dentro del módulo CEF.

    Lee la tabla existente usuarios_perfilusuario.
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


def normalizar_cueanexo(valor):
    cueanexo = re.sub(r"\D", "", str(valor or ""))
    if len(cueanexo) != LONGITUD_CUEANEXO:
        return ""
    return cueanexo


def normalizar_cuil(valor):
    return re.sub(r"\D", "", str(valor or ""))


def _cuil_limpio_db_expression():
    return Func(
        F("resploc_cuitcuil"),
        Value(r"[^0-9]"),
        Value(""),
        Value("g"),
        function="REGEXP_REPLACE",
        output_field=CharField(),
    )


def get_cefs_base_queryset():
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
    return get_cefs_base_queryset().order_by("cueanexo")


def get_cef_por_cueanexo(cueanexo):
    cueanexo_normalizado = normalizar_cueanexo(cueanexo)
    if not cueanexo_normalizado:
        return None
    return get_cefs_base_queryset().filter(cueanexo=cueanexo_normalizado).first()


def get_cefs_por_cuil_responsable(user):
    if not user or not getattr(user, "is_authenticated", False):
        return get_cefs_base_queryset().none()

    cuil_usuario = normalizar_cuil(getattr(user, "username", ""))
    if not cuil_usuario:
        return get_cefs_base_queryset().none()

    return (
        get_cefs_base_queryset()
        .annotate(responsable_cuil_limpio=_cuil_limpio_db_expression())
        .filter(responsable_cuil_limpio=cuil_usuario)
        .order_by("cueanexo")
    )


def get_cueanexos_por_cuil_responsable(user):
    return list(
        get_cefs_por_cuil_responsable(user)
        .values_list("cueanexo", flat=True)
        .distinct()
    )


def get_datos_establecimiento_cef(cueanexo):
    cef = get_cef_por_cueanexo(cueanexo)
    if cef is None:
        return None

    return {
        "id": cef.id,
        "cueanexo": cef.cueanexo or "",
        "nom_est": cef.nom_est or "",
        "padron_cueanexo": cef.padron_cueanexo or "",
        "acronimo": cef.acronimo or "",
        "oferta": cef.oferta or "",
        "etiqueta": cef.etiqueta or "",
        "nro_est": cef.nro_est or "",
        "ambito": cef.ambito or "",
        "sector": cef.sector or "",
        "region_loc": cef.region_loc or "",
        "ref_loc": cef.ref_loc or "",
        "calle": cef.calle or "",
        "numero": cef.numero or "",
        "localidad": cef.localidad or "",
        "departamento": cef.departamento or "",
        "estado_loc": cef.estado_loc or "",
        "est_oferta": cef.est_oferta or "",
        "estado_est": cef.estado_est or "",
        "resploc_cuitcuil": cef.resploc_cuitcuil or "",
        "resploc_doc": cef.resploc_doc or "",
        "apellido_resp": cef.apellido_resp or "",
        "nombre_resp": cef.nombre_resp or "",
        "resploc_email": cef.resploc_email or "",
        "resploc_telefono": cef.resploc_telefono or "",
        "sup_tecnico": cef.sup_tecnico or "",
        "email_suptecnico": cef.email_suptecnico or "",
        "tel_suptecnico": cef.tel_suptecnico or "",
        "categoria": cef.categoria or "",
        "cui_loc": cef.cui_loc or "",
        "cua_loc": cef.cua_loc or "",
        "cuof_loc": cef.cuof_loc or "",
        "jornada": cef.jornada or "",
    }
