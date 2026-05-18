# middleware.py
from apps.bnhpersonas_old.utils import get_ofertas_usuario


class UserCueanexoMiddleware:
    """
    Adjunta cueanexos del usuario autenticado al request.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):

        request.cueanexos_validos = set()
        request.cueanexos_list = []

        if request.user.is_authenticated:

            qs = get_ofertas_usuario(request.user)

            cueanexos = {
                str(c).strip()
                for c in qs.values_list('cueanexo', flat=True)
                if c is not None
            }

            request.cueanexos_validos = cueanexos
            request.cueanexos_list = list(cueanexos)

        return self.get_response(request)