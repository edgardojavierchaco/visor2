# tu_app/mixins.py

from typing import Any, Optional
from django.http import HttpRequest, JsonResponse, HttpResponse
from django.contrib import messages
from django.shortcuts import redirect
from django.views import View

from .models import GenerarInforme


class InformeBloqueoMixin(View):
    request: HttpRequest

    def get_cueanexo_activo(self):
        cueanexo = self.request.session.get("cueanexo")

        print("🔥 SESIÓN CUEANEXO:", cueanexo)

        return cueanexo

    def informe_bloqueado(self) -> bool:
        cueanexo = self.get_cueanexo_activo()

        if not cueanexo:
            return False

        ultimo = (
            GenerarInforme.objects
            .filter(cueanexo=cueanexo)
            .order_by('-id')
            .first()
        )

        return bool(ultimo and ultimo.estado == "ENVIADO")

    def handle_bloqueo(self):
        mensaje = "El último informe ya fue ENVIADO. No se puede modificar."

        # 🔥 mensaje para usuario
        messages.error(self.request, mensaje)

        # 🔥 redirigir SIEMPRE al list_url
        return redirect(self.success_url)

    def dispatch(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        print("🔥 MIXIN ACTIVO")

        self.request = request

        blocked = self.informe_bloqueado()
        print("🚫 BLOQUEADO:", blocked)

        if blocked:
            return self.handle_bloqueo()

        return super().dispatch(request, *args, **kwargs)