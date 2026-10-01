from django.contrib.auth import logout
from django.shortcuts import redirect
from django.urls import reverse

from .models import DispositivoUsuario
from .utils_dispositivo import generar_fingerprint


class DispositivoConfirmadoMiddleware:
    """
    Impide que una sesión autenticada navegue por el sistema desde un
    dispositivo que todavía no fue confirmado por correo.

    Es una segunda barrera de seguridad: además de no crear la sesión en
    LoginFormView hasta confirmar el dispositivo, invalida sesiones antiguas
    que pudieran haber sido creadas por versiones anteriores del login.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            login_url = reverse('logueo:login')
            logout_url = reverse('logueo:logout')

            # Estas rutas deben poder ejecutarse sin que el middleware genere
            # un bucle de redirecciones.
            rutas_exentas = {
                login_url,
                logout_url,
            }

            # La confirmación por token debe ser accesible desde el correo.
            confirmar_prefix = login_url.rstrip('/') + '/confirmar-dispositivo/'

            if (
                request.path not in rutas_exentas
                and not request.path.startswith(confirmar_prefix)
            ):
                fingerprint = generar_fingerprint(request)

                confirmado = DispositivoUsuario.objects.filter(
                    usuario=request.user,
                    fingerprint=fingerprint,
                    confirmado=True,
                    bloqueado=False,
                ).exists()

                if not confirmado:
                    logout(request)
                    return redirect(login_url)

        return self.get_response(request)
