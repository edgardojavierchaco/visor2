from functools import wraps
from .services import log_change
from .utils import snapshot


def audit(action):

    def decorator(func):

        @wraps(func)
        def wrapper(request, *args, **kwargs):

            instance_before = None
            instance_after = None

            result = func(request, *args, **kwargs)

            # intentar detectar instance en response (opcional)
            return result

        return wrapper

    return decorator