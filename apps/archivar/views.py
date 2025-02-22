from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy
from django.http import JsonResponse
from django.views.generic import CreateView, ListView, TemplateView, UpdateView, DeleteView
from .forms import ArchRegisterForm
from .models import ArchRegister
from .mixins import GroupRequiredMixin, ReadOnlyAccessMixin
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt

class ArchivoCreateView(GroupRequiredMixin,CreateView):
    
    model = ArchRegister
    form_class = ArchRegisterForm
    template_name = 'archivos/create.html'
    success_url = reverse_lazy('archivos:listar')
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
        context['title'] = 'Cargar Archivo'
        context['entity'] = 'Archivos'
        context['list_url'] = self.success_url
        context['action'] = 'add'
        return context
    

class ArchivosListView(ReadOnlyAccessMixin,ListView):
    
    model=ArchRegister
    template_name='archivos/list.html'
    #context_object_name='archivos' 
    
    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

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
        context['title'] = 'Listado de Archivos'
        context['create_url'] = reverse_lazy('archivos:crear')
        context['list_url'] = reverse_lazy('archivos:listar')
        context['update_url'] = reverse_lazy('archivos:editar', args=[0]) 
        context['entity'] = 'Archivos'
        return context           
   

class editar_archivos(GroupRequiredMixin,UpdateView):
    
    model = ArchRegister
    form_class = ArchRegisterForm
    template_name = 'archivos/create.html'
    success_url = reverse_lazy('archivos:listar')
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
        context['title'] = 'Edición de Archivos'
        context['entity'] = 'Archivos'
        context['list_url'] = self.success_url
        context['action'] = 'edit'
        return context
    
    """ def get_object(self):
        user_id = self.request.GET.get('id')
        return get_object_or_404(ArchRegister, id=user_id)
 """
    

class EliminarArchivosView(GroupRequiredMixin,DeleteView):
    
    model = ArchRegister
    template_name = 'archivos/delete.html'
    success_url = reverse_lazy('archivos:listar')
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
        context['title'] = 'Eliminación de Archivos'
        context['entity'] = 'Archivos'
        context['list_url'] = self.success_url
        return context
    
    """ def get(self, request):
        user_id = request.GET.get('id')
        user = get_object_or_404(ArchRegister, id=user_id)
        user.delete()
        return redirect('archivos:listar')  """
        


@method_decorator(csrf_exempt, name='dispatch')
class BuscarPDFView(TemplateView):
    def post(self, request, *args, **kwargs):
        action = request.POST.get('action')
        if action == 'searchdata':
            data = [registro.toJSON() for registro in ArchRegister.objects.all()]
            return JsonResponse(data, safe=False)
        elif action == 'buscar_pdf':
            cueanexo = request.POST.get('cueanexo')
            asunto = request.POST.get('asunto')
            print(cueanexo, asunto)  # Verifica en la consola que llegan los valores
            archivo = ArchRegister.objects.filter(cueanexo=cueanexo, asunto__asunto=asunto).first()
            if archivo and archivo.archivo:
                return JsonResponse({'ruta_pdf': archivo.archivo.url})
            return JsonResponse({'error': 'No se encontró ningún PDF.'})
        else:
            return JsonResponse({'error': 'Acción no definida.'})