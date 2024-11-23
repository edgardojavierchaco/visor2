from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.urls import reverse_lazy
from django.http import HttpResponseRedirect
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from .forms import UnidadServicioForm
#from .mixins import ValidatePermissionRequiredMixin
from .models import UnidadServicio, DepartamentoLocalidad


def cargar_localidades(request):
    departamento_id = request.GET.get('departamento_id')
    localidades = DepartamentoLocalidad.objects.filter(departamento=departamento_id)
    localidades_json = [{"id": localidad.id, "nombre": localidad.denom_localidad} for localidad in localidades]
    return JsonResponse(localidades_json, safe=False)


class USListView(LoginRequiredMixin, ListView):
    model = UnidadServicio
    template_name = 'pof/unidserv/list.html'
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
                for i in UnidadServicio.objects.all():
                    data.append(i.toJSON())
            else:
                data['error'] = 'Ha ocurrido un error'
        except Exception as e:
            data['error'] = str(e)
        return JsonResponse(data, safe=False)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Listado de Unidades de Servicio'
        context['create_url'] = reverse_lazy('pof:us_create')
        context['list_url'] = reverse_lazy('pof:us_list')         
        context['entity'] = 'Unidad Servicio'
        return context


class USCreateView(LoginRequiredMixin, CreateView):
    model = UnidadServicio
    form_class = UnidadServicioForm
    template_name = 'pof/unidserv/create.html'
    success_url = reverse_lazy('pof:us_list')
    #permission_required = 'apps.add_client'
    url_redirect = success_url

    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        try:
            action = request.POST.get('action')
            if action == 'add':
                form = self.get_form()
                if form.is_valid():
                    form.save() 
                    return HttpResponseRedirect(self.success_url)
                else:
                    return self.form_invalid(form)
            else:
                return JsonResponse({'error': 'No ha ingresado a ninguna opción'})
        except Exception as e:
            return JsonResponse({'error': str(e)})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Creación de una Unidad Servicio'
        context['entity'] = 'Unidad Servicio'
        context['list_url'] = self.success_url
        context['action'] = 'add'
        return context


class USUpdateView(LoginRequiredMixin, UpdateView):
    model = UnidadServicio
    form_class = UnidadServicioForm
    template_name = 'pof/unidserv/create.html'
    success_url = reverse_lazy('pof:us_list')
    #permission_required = 'apps.change_client'
    url_redirect = success_url

    def dispatch(self, request, *args, **kwargs):
        self.object = self.get_object()
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        try:
            action = request.POST.get('action')
            if action == 'add':
                form = self.get_form()
                if form.is_valid():
                    form.save()
                    return HttpResponseRedirect(self.success_url)
                else:
                    return self.form_invalid(form)
            else:
                return JsonResponse({'error': 'No ha ingresado a ninguna opción'})
        except Exception as e:
            return JsonResponse({'error': str(e)})


    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Edición de Unidad Servicio'
        context['entity'] = 'Unidad Servicio'
        context['list_url'] = self.success_url
        context['action'] = 'edit'
        return context


class USDeleteView(LoginRequiredMixin, DeleteView):
    model = UnidadServicio
    template_name = 'pof/unidserv/delete.html'
    success_url = reverse_lazy('pof:us_list')
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
        context['title'] = 'Eliminación de Unidad de Servicio'
        context['entity'] = 'Unidad Servicio'
        context['list_url'] = self.success_url
        return context


