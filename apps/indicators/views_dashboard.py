from django.views.generic import TemplateView


class DashboardIndicatorsView(TemplateView):
    template_name = "indicators/dashboard.html"