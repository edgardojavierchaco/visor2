from audit.services import log_change


class AuditRequestMiddleware:

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):

        response = self.get_response(request)

        # opcional: log de endpoints sensibles
        if request.path.startswith("/api/"):

            # podés extender esto para tracking general
            pass

        return response