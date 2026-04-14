# middleware.py

from .models import UsuarioAccesoLog
from django.utils.deprecation import MiddlewareMixin


class AuditoriaMiddleware(MiddlewareMixin):

    EXCLUDE_PREFIXES = (
        "/static/",
        "/media/",
        "/favicon.ico",
        "/robots.txt",
        "/usua/trazabilidad/data/",
        "/usua/dashboard_trace/data/",
        "/admin/jsi18n/",
    )

    EXCLUDE_EXTENSIONS = (
        ".js", ".css", ".png", ".jpg", ".jpeg",
        ".gif", ".svg", ".ico", ".woff", ".woff2",
        ".ttf", ".map"
    )

    def process_response(self, request, response):
        try:

            path = request.path.lower()

            # =========================
            # 🚫 EXCLUSIONES
            # =========================
            if path.startswith(self.EXCLUDE_PREFIXES):
                return response

            if path.endswith(self.EXCLUDE_EXTENSIONS):
                return response

            # =========================
            # 🚫 SOLO RESPUESTAS OK
            # =========================
            if response.status_code >= 400:
                return response

            # =========================
            # 🚫 SOLO USUARIOS LOGUEADOS
            # =========================
            if not request.user.is_authenticated:
                return response

            # =========================
            # 🧠 DATOS USUARIO
            # =========================
            username = request.user.username

            # =========================
            # 🌍 IP
            # =========================
            ip = self.get_ip(request)

            # =========================
            # ⚡ ACCIÓN
            # =========================
            accion = self.detectar_accion(request)

            # =========================
            # 💾 LOG
            # =========================
            UsuarioAccesoLog.objects.create(
                username=username,
                ip=ip,
                user_agent=request.META.get("HTTP_USER_AGENT", "")[:255],
                accion=accion,
                path=path[:255]
            )

        except Exception as e:
            print("⚠️ Error AuditoriaMiddleware:", str(e))

        return response

    # =========================
    # 🌍 IP REAL
    # =========================
    def get_ip(self, request):
        x_forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded:
            return x_forwarded.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR", "")

    # =========================
    # 🧠 DETECCIÓN DE ACCIÓN
    # =========================
    def detectar_accion(self, request):

        path = request.path.lower()
        method = request.method

        if "login" in path:
            return "login"

        if "logout" in path:
            return "logout"

        if method == "POST":
            if any(x in path for x in ["create", "nuevo", "alta"]):
                return "create"
            if any(x in path for x in ["delete", "eliminar", "baja"]):
                return "delete"
            return "update"

        if method == "PUT":
            return "update"

        if method == "DELETE":
            return "delete"

        return "view"