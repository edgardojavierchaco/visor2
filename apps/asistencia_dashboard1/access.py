import re
import unicodedata
from dataclasses import dataclass, field

from django.db.models import F, Func, Value

from apps.consultasge.models_padron import CapaUnicaOfertas


FULL_ACCESS_ROLES = {
    "administrador",
    "gestor",
    "ministro",
    "secretario",
    "subsecretario",
    "director general",
}


@dataclass
class AccessScope:
    role_name: str = ""
    full_access: bool = False
    regiones: list[str] = field(default_factory=list)
    cueanexos: list[str] = field(default_factory=list)

    @property
    def denied(self):
        return not self.full_access and not self.cueanexos


def _normalize(value):
    value = value or ""
    value = unicodedata.normalize("NFKD", str(value))
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    return " ".join(value.casefold().strip().split())


def _digits(value):
    return re.sub(r"\D", "", str(value or ""))




def _normalize_cues(values):
    """
    Normaliza CUEANEXO a texto sin comparar contra cadena vacía en SQL.
    Esto soporta vistas donde PostgreSQL expone cueanexo como bigint.
    """
    resultado = []
    for value in values:
        if value is None:
            continue
        cue = str(value).strip()
        if cue:
            resultado.append(cue)
    return list(dict.fromkeys(resultado))

def get_role_name(user):
    try:
        return getattr(user.perfil.rol, "nombre", "") or ""
    except Exception:
        return ""


def _model_has_field(model, field_name):
    try:
        model._meta.get_field(field_name)
        return True
    except Exception:
        return False


def _cues_por_regiones(regiones):
    if not regiones:
        return []
    return _normalize_cues(
        CapaUnicaOfertas.objects.using("default")
        .filter(region_loc__in=regiones)
        .exclude(cueanexo__isnull=True)
        .values_list("cueanexo", flat=True)
        .distinct()
    )


def _scope_regional(user, role_name):
    try:
        from apps.supervisor_registro.models import ResponsableRegional
    except Exception:
        return AccessScope(role_name=role_name)

    qs = ResponsableRegional.objects.all()
    if _model_has_field(ResponsableRegional, "activo"):
        qs = qs.filter(activo=True)

    responsable = None
    try:
        responsable = qs.filter(usuario=user).first()
    except Exception:
        pass

    if responsable is None:
        try:
            responsable = qs.filter(usuario__username=user.username).first()
        except Exception:
            pass

    if responsable is None:
        return AccessScope(role_name=role_name)

    regiones_qs = responsable.regiones.all()
    region_model = regiones_qs.model
    if _model_has_field(region_model, "activo"):
        regiones_qs = regiones_qs.filter(activo=True)

    campo_nombre = "nombre" if _model_has_field(region_model, "nombre") else "descripcion"
    regiones = list(regiones_qs.values_list(campo_nombre, flat=True))
    return AccessScope(
        role_name=role_name,
        regiones=regiones,
        cueanexos=_cues_por_regiones(regiones),
    )


def _scope_supervisor(user, role_name):
    try:
        from apps.supervisor_registro.models import ABMSupervisores, SupervisorRegionalOferta
    except Exception:
        return AccessScope(role_name=role_name)

    qs = ABMSupervisores.objects.all()
    if _model_has_field(ABMSupervisores, "activo"):
        qs = qs.filter(activo=True)

    supervisor = None
    try:
        supervisor = qs.filter(usuario=user).first()
    except Exception:
        pass

    if supervisor is None:
        try:
            supervisor = qs.filter(usuario__username=user.username).first()
        except Exception:
            pass

    if supervisor is None:
        return AccessScope(role_name=role_name)

    ofertas = SupervisorRegionalOferta.objects.filter(
        supervisor_regional__supervisor=supervisor,
    )
    if _model_has_field(SupervisorRegionalOferta, "activo"):
        ofertas = ofertas.filter(activo=True)

    sr_model = SupervisorRegionalOferta._meta.get_field("supervisor_regional").related_model
    if _model_has_field(sr_model, "activo"):
        ofertas = ofertas.filter(supervisor_regional__activo=True)

    cues = _normalize_cues(
        ofertas.exclude(cueanexo__isnull=True)
        .values_list("cueanexo", flat=True)
        .distinct()
    )
    return AccessScope(role_name=role_name, cueanexos=cues)


def _scope_director(user, role_name):
    username = _digits(getattr(user, "username", ""))
    if not username:
        return AccessScope(role_name=role_name)

    cues = _normalize_cues(
        CapaUnicaOfertas.objects.using("default")
        .annotate(
            responsable_limpio=Func(
                F("resploc_cuitcuil"),
                Value(r"\D"),
                Value(""),
                Value("g"),
                function="REGEXP_REPLACE",
            )
        )
        .filter(responsable_limpio=username)
        .exclude(cueanexo__isnull=True)
        .values_list("cueanexo", flat=True)
        .distinct()
    )
    return AccessScope(role_name=role_name, cueanexos=cues)


def get_access_scope(user):
    role_name = get_role_name(user)
    role = _normalize(role_name)

    if getattr(user, "is_superuser", False) or role in FULL_ACCESS_ROLES:
        return AccessScope(role_name=role_name, full_access=True)

    if role == "regional":
        return _scope_regional(user, role_name)

    if role == "supervisor":
        return _scope_supervisor(user, role_name)

    if role == "director":
        return _scope_director(user, role_name)

    # Seguridad por defecto: cualquier perfil no contemplado no recibe datos.
    return AccessScope(role_name=role_name)
