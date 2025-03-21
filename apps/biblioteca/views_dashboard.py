from django.views.generic import TemplateView


class DashboardView(TemplateView):
    template_name = 'biblioteca/layout.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['panel'] = 'Panel de administrador'
        return context

class DashboardDirView(TemplateView):
    template_name= 'biblioteca/layout_dir.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['panel'] = 'Panel de administrador'
        return context