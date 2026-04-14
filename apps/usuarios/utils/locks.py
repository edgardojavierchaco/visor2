from django.core.cache import cache

LOCK_KEY = "sync:usuarios:lock"


def acquire_lock():
    """
    Intenta adquirir lock atómico en Redis.
    Devuelve True si lo obtuvo, False si ya existe.
    """
    return cache.set(LOCK_KEY, "1", nx=True, timeout=600)


def release_lock():
    """
    Libera el lock manualmente.
    """
    cache.delete(LOCK_KEY)


def is_locked():
    """
    (Opcional) verificar estado del lock
    """
    return cache.get(LOCK_KEY) is not None