from django.views.generic import TemplateView


class DashboardView(TemplateView):
    template_name = 'operativoschaco/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['panel'] = 'Panel de administrador'
        return context

class DashboardFluidezView(TemplateView):
    template_name = 'operativoschaco/dashboard_fluidez.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['panel'] = 'Panel de administrador'
        return context

class DashboardMatemQuintoView(TemplateView):
    template_name = 'operativoschaco/dashboard_matematica_quinto.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['panel'] = 'Panel de administrador'
        return context