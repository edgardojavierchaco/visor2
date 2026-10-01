import unicodedata
from django.conf import settings

DEFAULT_SUPERVISOR_ROLES = {"supervisor"}
DEFAULT_REGIONAL_ROLES = {"regional"}
DEFAULT_GLOBAL_ROLES = {
    "administrador",
    "gestor",
    "director general",
    "director/a general",
    "directora general",
    "subsecretario",
    "subsecretaria",
    "subsecretario/a",
    "ministro",
    "ministra",
    "ministro/a",
}


def _text(value):
    if value is None:
        return ""
    for attr in ("nombre", "descripcion", "nivel", "rol", "codigo"):
        if hasattr(value, attr):
            candidate = getattr(value, attr, None)
            if candidate:
                return str(candidate)
    return str(value)


def normalize_role(value):
    value = _text(value).strip().casefold()
    value = unicodedata.normalize("NFKD", value)
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    value = " ".join(value.replace("_", " ").replace("-", " ").split())
    return value


def user_role(user):
    if not user or not getattr(user, "is_authenticated", False):
        return ""
    if getattr(user, "is_superuser", False):
        return "administrador"
    return normalize_role(getattr(user, "nivelacceso", ""))


def _configured(name, default):
    values = getattr(settings, name, default)
    return {normalize_role(value) for value in values}


def supervisor_roles():
    return _configured("BNH_MONITOR_SUPERVISOR_ROLES", DEFAULT_SUPERVISOR_ROLES)


def regional_roles():
    return _configured("BNH_MONITOR_REGIONAL_ROLES", DEFAULT_REGIONAL_ROLES)


def global_roles():
    return _configured("BNH_MONITOR_GLOBAL_ROLES", DEFAULT_GLOBAL_ROLES)


def role_kind(user):
    role = user_role(user)
    if not role:
        return "none"
    if getattr(user, "is_superuser", False) or role in global_roles():
        return "global"
    if role in supervisor_roles():
        return "supervisor"
    if role in regional_roles():
        return "regional"
    return "none"
