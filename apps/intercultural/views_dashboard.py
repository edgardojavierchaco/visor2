from django.views.generic import TemplateView


class DashboardView(TemplateView):
    template_name = 'intercultural/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['panel'] = 'Panel de administrador'
        return context

class DashboardComunView(TemplateView):
    template_name = 'intercultural/dashboard_comun.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['panel'] = 'Panel de administrador'
        return context

class DashboardFuncView(TemplateView):
    template_name = 'intercultural/dashboard_func.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['panel'] = 'Panel de administrador'
        return context


class DashboardRegView(TemplateView):
    template_name = 'intercultural/dashboard_reg.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['panel'] = 'Panel de administrador'
        return context