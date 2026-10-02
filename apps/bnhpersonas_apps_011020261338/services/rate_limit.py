"""Rate limit liviano para endpoints de consulta de identidad.

Usa el cache configurado por Django. En producción con Redis el contador es
compartido entre workers; con LocMemCache sólo protege cada proceso.
"""
from __future__ import annotations

import time
from functools import wraps

from django.core.cache import cache
from django.http import JsonResponse


def user_rate_limit(prefix: str, *, limit: int = 60, window_seconds: int = 60):
    def decorator(view):
        @wraps(view)
        def wrapped(request, *args, **kwargs):
            user_id = getattr(getattr(request, "user", None), "pk", None) or "anon"
            bucket = int(time.time() // window_seconds)
            key = f"bnh:ratelimit:{prefix}:{user_id}:{bucket}"
            if cache.add(key, 1, timeout=window_seconds + 5):
                count = 1
            else:
                try:
                    count = cache.incr(key)
                except ValueError:
                    cache.set(key, 1, timeout=window_seconds + 5)
                    count = 1
            if count > limit:
                return JsonResponse(
                    {
                        "ok": False,
                        "mensaje": "Se realizaron demasiadas consultas. Espere un momento y vuelva a intentar.",
                    },
                    status=429,
                )
            return view(request, *args, **kwargs)

        return wrapped

    return decorator
