"""Compatibilidad para instalaciones existentes; los servicios reciben el usuario explícito."""
from contextvars import ContextVar
_user = ContextVar("bnh_current_user", default=None)

def get_current_user():
    return _user.get()

class CurrentUserMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        token = _user.set(request.user)
        try:
            return self.get_response(request)
        finally:
            _user.reset(token)
