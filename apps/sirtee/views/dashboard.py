from django.http import JsonResponse
from django.views import View

from apps.sirtee.services.dashboard import SirteeDashboardService


class SirteeDashboardView(View):
    """
    Endpoint principal del dashboard SIRTEE.
    """

    def get(self, request):
        service = SirteeDashboardService()
        data = service.get_dashboard()

        return JsonResponse(data, safe=False)