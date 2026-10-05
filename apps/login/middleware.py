from django.contrib.auth import logout
from django.shortcuts import redirect
from django.urls import reverse

from .models import DispositivoUsuario
from .utils_dispositivo import generar_fingerprint


class DispositivoConfirmadoMiddleware:
    """
    Impide que una sesión autenticada navegue por el sistema desde un
    dispositivo que todavía no fue confirmado por correo.

    Excepciones:
    - Login
    - Logout
    - Confirmación de dispositivo
    - Verificación pública de constancias BNH mediante QR
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):

        # ============================================================
        # RUTAS PÚBLICAS / EXENTAS
        # ============================================================

        login_url = reverse("logueo:login")
        logout_url = reverse("logueo:logout")

        rutas_exentas = {
            login_url,
            logout_url,
        }

        # Confirmación por correo del dispositivo.
        confirmar_prefix = (
            login_url.rstrip("/")
            + "/confirmar-dispositivo/"
        )

        # ============================================================
        # BNH - VERIFICACIÓN PÚBLICA DE CONSTANCIAS
        # ============================================================
        #
        # La URL real queda montada bajo /bnh/ porque las URLs de
        # bnhpersonas se incluyen allí desde config.urls.
        #
        # No requiere autenticación ni dispositivo confirmado.
        #
        verificar_constancia_prefix = (
            "/bnh/constancias/verificar/"
        )

        ruta_publica = (
            request.path in rutas_exentas
            or request.path.startswith(confirmar_prefix)
            or request.path.startswith(
                verificar_constancia_prefix
            )
        )

        if ruta_publica:
            return self.get_response(request)

        # ============================================================
        # CONTROL DE DISPOSITIVO
        # ============================================================

        if request.user.is_authenticated:

            fingerprint = generar_fingerprint(request)

            confirmado = (
                DispositivoUsuario.objects
                .filter(
                    usuario=request.user,
                    fingerprint=fingerprint,
                    confirmado=True,
                    bloqueado=False,
                )
                .exists()
            )

            if not confirmado:
                logout(request)
                return redirect(login_url)

        return self.get_response(request)