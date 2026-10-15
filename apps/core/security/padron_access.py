import re

from django.core.cache import cache
from django.db import connections

CACHE_TTL = 60 * 5
CACHE_VERSION = "v1"

def normalize_cuil(value):
    return re.sub(r"\D", "", str(value or ""))

def _cache_key(cuil):
    return f"padron:{CACHE_VERSION}:cues:{cuil}"

def get_cueanexos_by_cuil(cuil):
    """Obtiene los CUEANEXO activos del responsable directamente desde Padron."""
    cuil = normalize_cuil(cuil)
    if len(cuil) != 11:
        return tuple()
    cache_key = _cache_key(cuil)
    cached = cache.get(cache_key)
    if cached is not None:
        return tuple(cached)
    sql = """
        SELECT DISTINCT
            (e.cue::text || l.anexo::text) AS cueanexo
        FROM responsable r
        JOIN localizacion l ON l.id_responsable = r.id_responsable
        JOIN establecimiento e ON e.id_establecimiento = l.id_establecimiento
        JOIN oferta_local ol ON ol.id_localizacion = l.id_localizacion
        JOIN estado_tipo et ON et.c_estado = ol.c_estado
        WHERE regexp_replace(r.cuil_cuit::text, '\\D', '', 'g') = %s
          AND et.descripcion ILIKE '%%Activo%%'
        ORDER BY 1
    """
    with connections["Padron"].cursor() as cursor:
        cursor.execute(sql, [cuil])
        cueanexos = tuple(str(row[0]).strip() for row in cursor.fetchall() if row[0])
    cache.set(cache_key, cueanexos, CACHE_TTL)
    return cueanexos

def user_cueanexos(user):
    if not user or not user.is_authenticated or not user.is_active:
        return tuple()
    return get_cueanexos_by_cuil(user.get_username())

def user_has_cueanexo(user, cueanexo):
    cueanexo = str(cueanexo or "").strip()
    if not cueanexo:
        return False
    return cueanexo in user_cueanexos(user)

def invalidate_cuil_cache(cuil):
    cuil = normalize_cuil(cuil)
    if len(cuil) != 11:
        return False
    cache.delete(_cache_key(cuil))
    return True
