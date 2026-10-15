"""Catálogo institucional cacheado para BNH Personas."""
from django.core.cache import cache
from .access import is_admin, scoped_offers

CACHE_TTL = 60 * 5
CACHE_VERSION = "v1"

def _cache_key(user):
    return f"bnh:{CACHE_VERSION}:institutions:global" if is_admin(user) else f"bnh:{CACHE_VERSION}:institutions:user:{user.pk}"

def institution_catalog(user):
    if not user or not user.is_authenticated or not user.is_active:
        return tuple()
    key = _cache_key(user)
    cached = cache.get(key)
    if cached is not None:
        return tuple(cached)
    rows = scoped_offers(user).exclude(nom_est__isnull=True).exclude(nom_est="").order_by("cueanexo_str", "nom_est").values_list("cueanexo_str", "nom_est")
    institutions = {}
    for cue, name in rows:
        cue = str(cue or "").strip()
        if cue:
            institutions.setdefault(cue, str(name or "").strip())
    result = tuple(institutions.items())
    cache.set(key, result, CACHE_TTL)
    return result

def institution_map(user):
    return dict(institution_catalog(user))

def institution_name(user, cueanexo, default=""):
    cueanexo = str(cueanexo or "").strip()
    return institution_map(user).get(cueanexo, default) if cueanexo else default

def institution_rows(user):
    return tuple({"cueanexo_str": cue, "nom_est": name} for cue, name in institution_catalog(user))

def invalidate_institution_catalog(user):
    if user and getattr(user, "pk", None):
        cache.delete(_cache_key(user))
