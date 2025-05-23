from django.views.generic import TemplateView


class DashboardView(TemplateView):
    template_name = 'superv/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['panel'] = 'Panel de administrador'
        return context


class DashboardSupervisorView(TemplateView):
    template_name = 'superv/dashboard_supervisor.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['panel'] = 'Panel de supervisor'
        return context