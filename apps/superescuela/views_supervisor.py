from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import ListView, CreateView, UpdateView, DeleteView

from .forms import SupervisorForm
#from .mixins import ValidatePermissionRequiredMixin
from .models import Supervisor


class SupervisoresListView(LoginRequiredMixin, ListView):
    model = Supervisor
    template_name = 'superv/supervisor/list.html'
    #permission_required = 'apps.view_supervisor'

    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        data = {}
        try:
            action = request.POST['action']
            if action == 'searchdata':
                data = []
                for i in Supervisor.objects.all():
                    data.append(i.toJSON())
            else:
                data['error'] = 'Ha ocurrido un error'
        except Exception as e:
            data['error'] = str(e)
        return JsonResponse(data, safe=False)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Listado de Supervisores'
        context['create_url'] = reverse_lazy('superescuela:super_create')
        context['list_url'] = reverse_lazy('superescuela:super_list')
        context['update_url'] = reverse_lazy('supervi:super_update', args=[0]) 
        context['entity'] = 'Supervisor'
        return context


class SupervisorCreateView(LoginRequiredMixin, CreateView):
    model = Supervisor
    form_class = SupervisorForm
    template_name = 'superv/supervisor/create.html'
    success_url = reverse_lazy('superescuela:super_list')
    #permission_required = 'apps.add_client'
    url_redirect = success_url

    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        data = {}
        try:
            action = request.POST['action']
            if action == 'add':
                form = self.get_form()
                data = form.save()
            else:
                data['error'] = 'No ha ingresado a ninguna opción'
        except Exception as e:
            data['error'] = str(e)
        return JsonResponse(data)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Creación un Supervisor'
        context['entity'] = 'Supervisor'
        context['list_url'] = self.success_url
        context['action'] = 'add'
        return context


class SupervisorUpdateView(LoginRequiredMixin, UpdateView):
    model = Supervisor
    form_class = SupervisorForm
    template_name = 'superv/supervisor/create.html'
    success_url = reverse_lazy('superescuela:super_list')
    #permission_required = 'apps.change_client'
    url_redirect = success_url

    def dispatch(self, request, *args, **kwargs):
        self.object = self.get_object()
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        data = {}
        try:
            action = request.POST['action']
            if action == 'edit':
                form = self.get_form()
                data = form.save()
            else:
                data['error'] = 'No ha ingresado a ninguna opción'
        except Exception as e:
            data['error'] = str(e)
        return JsonResponse(data)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Edición un Supervisor'
        context['entity'] = 'Supervisor'
        context['list_url'] = self.success_url
        context['action'] = 'edit'
        return context


class SupervisorDeleteView(LoginRequiredMixin, DeleteView):
    model = Supervisor
    template_name = 'superv/supervisor/delete.html'
    success_url = reverse_lazy('superescuela:super_list')
    #permission_required = 'apps.delete_client'
    url_redirect = success_url

    def dispatch(self, request, *args, **kwargs):
        self.object = self.get_object()
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        data = {}
        try:
            self.object.delete()
        except Exception as e:
            data['error'] = str(e)
        return JsonResponse(data)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Eliminación de un Supervisor'
        context['entity'] = 'Supervisor'
        context['list_url'] = self.success_url
        return context