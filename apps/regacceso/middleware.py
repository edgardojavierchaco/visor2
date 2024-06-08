from django.utils.deprecation import MiddlewareMixin
from .models import RegistroAcceso

class RegistroAccesoMiddleware(MiddlewareMixin):
    def process_request(self, request):
        if request.user.is_authenticated:
            RegistroAcceso.objects.create(
                usuario=request.user,
                url_acceso=request.path,
                metodo_http=request.method,
                ip_usuario=request.META.get('REMOTE_ADDR'),
                agente_usuario=request.META.get('HTTP_USER_AGENT')
            )