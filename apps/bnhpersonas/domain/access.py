"""Política única de alcance de BNH Personas."""
import re
from functools import wraps
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.core.exceptions import PermissionDenied
from django.db.models import CharField
from django.db.models.functions import Cast
from apps.consultasge.models_padron import CapaUnicaOfertas
from apps.core.security.padron_access import get_cueanexos_by_cuil, user_has_cueanexo

CACHE_TTL = 60 * 5
CACHE_VERSION = "v1"

def normalize_cuil(value):
    return re.sub(r"[^0-9]", "", str(value or ""))

def authenticated(user):
    return bool(user and user.is_authenticated and user.is_active)

def get_user_cuil(user):
    return normalize_cuil(user.get_username()) if authenticated(user) else ""

def role(user):
    return str(getattr(user, "nivelacceso", ""))

def is_admin(user):
    return authenticated(user) and (user.is_superuser or role(user) in getattr(settings, "BNH_ADMIN_ROLES", ("Administrador",)))

def is_regional(user):
    return authenticated(user) and role(user) in getattr(settings, "BNH_REGIONAL_ROLES", ("Regional",))

def is_refestadistica(user):
    """Referente habilitado mediante rol y registro propio (sin caché)."""
    if not authenticated(user):
        return False
    perfil = getattr(user, "perfil", None)
    if not perfil or not perfil.rol or perfil.rol.categoria_acceso != "refestadistica":
        return False
    from apps.usuarios.models import Referentes
    return Referentes.objects.filter(cuil=get_user_cuil(user), estado=True).exists()


def regiones_refestadistica(user):
    if not is_refestadistica(user):
        return ()
    from apps.usuarios.models import Referentes
    region_text = Referentes.objects.filter(
        cuil=get_user_cuil(user), estado=True
    ).values_list("region", flat=True).first() or ""
    return tuple(dict.fromkeys(r.strip() for r in region_text.split(",") if r.strip()))


def is_director(user):
    return authenticated(user) and role(user) in getattr(settings, "BNH_DIRECTOR_ROLES", ("Director/a", "Director"))

def scoped_offers(user):
    qs = CapaUnicaOfertas.objects.annotate(cueanexo_str=Cast("cueanexo", CharField()))
    if not authenticated(user):
        return qs.none()
    if is_admin(user):
        return qs
    if is_regional(user):
        from ..models import AccesoRegional
        regiones = AccesoRegional.objects.filter(usuario=user, activo=True).values("region")
        return qs.filter(region_loc__in=regiones)
    if is_refestadistica(user):
        regiones = regiones_refestadistica(user)
        return qs.filter(region_loc__in=regiones) if regiones else qs.none()
    if is_director(user):
        cueanexos = get_user_cueanexos(user)
        return qs.filter(cueanexo_str__in=cueanexos) if cueanexos else qs.none()
    return qs.none()

def _regional_cache_key(user):
    return f"bnh:{CACHE_VERSION}:regional-cues:{user.pk}"

def get_user_cueanexos(user):
    if not authenticated(user):
        return tuple()
    if is_director(user):
        cuil = get_user_cuil(user)
        return get_cueanexos_by_cuil(cuil) if len(cuil) == 11 else tuple()
    if is_refestadistica(user):
        # Sin caché para que los cambios de regiones o estado sean inmediatos.
        return tuple(str(c).strip() for c in scoped_offers(user).order_by().values_list(
            "cueanexo_str", flat=True
        ).distinct() if c)
    if is_regional(user):
        key = _regional_cache_key(user)
        cached = cache.get(key)
        if cached is not None:
            return tuple(cached)
        result = tuple(str(c).strip() for c in scoped_offers(user).order_by().values_list("cueanexo_str", flat=True).distinct() if c)
        cache.set(key, result, CACHE_TTL)
        return result
    if is_admin(user):
        return tuple(str(c).strip() for c in scoped_offers(user).order_by().values_list("cueanexo_str", flat=True).distinct() if c)
    return tuple()

def invalidate_regional_cue_cache(user):
    if user and getattr(user, "pk", None):
        cache.delete(_regional_cache_key(user))

def user_has_cueanexo_access(user, cueanexo):
    if not authenticated(user):
        return False
    cueanexo = str(cueanexo or "").strip()
    if not cueanexo:
        return False
    if is_admin(user):
        return True
    if is_director(user):
        return user_has_cueanexo(user, cueanexo)
    if is_regional(user) or is_refestadistica(user):
        return cueanexo in get_user_cueanexos(user)
    return False

def activity_scope(user, include_deleted=False):
    from ..models import RegistroActividades
    if not authenticated(user):
        return RegistroActividades.objects.none()
    if is_admin(user):
        qs = RegistroActividades.objects.all()
    else:
        cueanexos = get_user_cueanexos(user)
        if not cueanexos:
            return RegistroActividades.objects.none()
        qs = RegistroActividades.objects.filter(cueanexo__in=cueanexos)
    if include_deleted:
        return qs
    return qs.filter(eliminado=False, persona__archivada=False)

def person_scope(user):
    from ..models import Personas
    qs = Personas.objects.filter(archivada=False)
    if not authenticated(user):
        return qs.none()
    if is_admin(user):
        return qs
    cueanexos = get_user_cueanexos(user)
    if not cueanexos:
        return qs.none()
    return qs.filter(actividades__cueanexo__in=cueanexos).distinct()

def operator_required(view):
    @login_required
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        if not authenticated(request.user):
            raise PermissionDenied("No tiene instituciones habilitadas para BNH Personal.")
        if not (is_admin(request.user) or bool(get_user_cueanexos(request.user))):
            raise PermissionDenied("No tiene instituciones habilitadas para BNH Personal.")
        if is_refestadistica(request.user) and request.method not in ("GET", "HEAD", "OPTIONS"):
            raise PermissionDenied("Los referentes de Estadística disponen de acceso de consulta únicamente.")
        response = view(request, *args, **kwargs)
        response["Cache-Control"] = "private, no-store"
        return response
    return wrapped
