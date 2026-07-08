from apps.sirtee.signals import set_current_user, set_request_meta


class AuditMiddleware:
    """
    Middleware global de auditoría.

    Objetivo:
    - Capturar usuario autenticado
    - Capturar IP del request
    - Capturar User-Agent
    - Inyectar todo en contexto thread-local
    para uso en signals sin acoplar Django request.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        self.process_request(request)
        response = self.get_response(request)
        self.process_response(request, response)
        return response

    # -----------------------------
    # REQUEST
    # -----------------------------

    def process_request(self, request):
        user = getattr(request, "user", None)

        if user and user.is_authenticated:
            set_current_user(user)
        else:
            set_current_user(None)

        ip = self.get_client_ip(request)
        user_agent = request.META.get("HTTP_USER_AGENT", "")

        set_request_meta(ip=ip, user_agent=user_agent)

    # -----------------------------
    # RESPONSE (limpieza opcional)
    # -----------------------------

    def process_response(self, request, response):
        # Opcional: podrías limpiar thread-local aquí si querés
        return response

    # -----------------------------
    # IP REAL (proxy-safe básico)
    # -----------------------------

    def get_client_ip(self, request):
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")

        if x_forwarded_for:
            # toma el primer IP real del proxy chain
            ip = x_forwarded_for.split(",")[0].strip()
        else:
            ip = request.META.get("REMOTE_ADDR")

        return ip