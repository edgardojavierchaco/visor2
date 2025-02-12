from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.db import connection
from .forms import EscuelasRepresentadasForm
#from .mixins import ValidatePermissionRequiredMixin
from .models import EscuelasRepresentadas


class EscuelasRepresentadasListView(LoginRequiredMixin, ListView):
    model = EscuelasRepresentadas
    template_name = 'replegales/escuelas/list.html'
    #permission_required = 'apps.view_escuelas'

    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)    
          
        
    def get_queryset(self):
        
        return EscuelasRepresentadas.objects.all()


    def post(self, request, *args, **kwargs):
        data = {}
        try:
            action = request.POST['action']
            if action == 'searchdata':
                data = []
                for i in self.get_queryset():
                    data.append(i.toJSON())
            else:
                data['error'] = 'Ha ocurrido un error'
        except Exception as e:
            data['error'] = str(e)
        return JsonResponse(data, safe=False)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Listado de Unidades de Servicios'
        context['create_url'] = reverse_lazy('representantes:escuelas_create')
        context['list_url'] = reverse_lazy('representantes:super_list')
        context['entity'] = 'Escuelas'
        return context


class EscuelasRepresentadasCreateView(LoginRequiredMixin, CreateView):
    model = EscuelasRepresentadas
    form_class = EscuelasRepresentadasForm
    template_name = 'replegales/escuelas/create.html'
    success_url = reverse_lazy('representantes:super_list')
    #permission_required = 'apps.add_escuelas'
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
        context['title'] = 'Creación de una Unidad de Servicio'
        context['entity'] = 'Escuelas'
        context['list_url'] = self.success_url
        context['action'] = 'add'
        return context


class EscuelasRepresentadasUpdateView(LoginRequiredMixin, UpdateView):
    model = EscuelasRepresentadas
    form_class = EscuelasRepresentadasForm
    template_name = 'replegales/escuelas/create.html'
    success_url = reverse_lazy('representantes:super_list')
    #permission_required = 'apps.change_escuelas'
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
        context['title'] = 'Edición de una Unidad de Servicio'
        context['entity'] = 'Escuelas'
        context['list_url'] = self.success_url
        context['action'] = 'edit'
        return context


class EscuelasRepresentadasDeleteView(LoginRequiredMixin, DeleteView):
    model = EscuelasRepresentadas
    template_name = 'replegales/escuelas/delete.html'
    success_url = reverse_lazy('representantes:super_list')
    #permission_required = 'apps.delete_escuelas'
    url_redirect = success_url

    @method_decorator(login_required)
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
        context['title'] = 'Eliminación de una Unidad de Servicio'