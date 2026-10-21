# middleware.py
from apps.core.security.padron_access import user_cueanexos


class UserCueanexoMiddleware:
    """Anexa CUEANEXO cuyo responsable coincide con el CUIL del usuario."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.cueanexos_validos = set()
        request.cueanexos_list = []

        if request.user.is_authenticated:
            cues = {
                str(cue).strip()
                for cue in user_cueanexos(request.user)
                if cue is not None and str(cue).strip()
            }
            request.cueanexos_validos = cues
            request.cueanexos_list = sorted(cues)

        return self.get_response(request)
