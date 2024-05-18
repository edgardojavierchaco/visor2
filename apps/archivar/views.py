from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy
from django.http import JsonResponse
from django.views.generic import CreateView, ListView, TemplateView, UpdateView, DeleteView
from .forms import ArchRegisterForm
from .models import ArchRegister
from .mixins import GroupRequiredMixin, ReadOnlyAccessMixin

class ArchivoCreateView(GroupRequiredMixin,CreateView):
    model = ArchRegister
    form_class = ArchRegisterForm
    template_name = 'archivos/cargar_archivo.html'
    success_url = reverse_lazy('archivos:listar')

    def get_context_data(self, **kwargs):
        context=super().get_context_data(**kwargs)
        context['title']='Cargar Archivo'
        return context

class ArchivosListView(ReadOnlyAccessMixin,ListView):
    model=ArchRegister
    template_name='archivos/archivos_lista.html'
    context_object_name='archivos' 
    
    def get_context_data(self, **kwargs):
        context=super().get_context_data(**kwargs)
        context['title']='Listado de Archivos'
        return context
    

class BuscarPDFView(TemplateView):   

    def post(self, request, *args, **kwargs):
        cueanexo = request.POST.get('cueanexo')
        asunto = request.POST.get('asunto')
        archivo = ArchRegister.objects.filter(cueanexo=cueanexo, asunto__asunto=asunto).first()
        if archivo and archivo.archivo:
            return JsonResponse({'ruta_pdf': archivo.archivo.url})
        else:
            return JsonResponse({'error': 'No se encontró ningún PDF con el cueanexo y asunto especificados.'})

class editar_archivos(GroupRequiredMixin,UpdateView):
    model = ArchRegister
    form_class = ArchRegisterForm
    template_name = 'archivos/editar.html'
    success_url = reverse_lazy('archivos:listar')

    def get_object(self):
        user_id = self.request.GET.get('id')
        return get_object_or_404(ArchRegister, id=user_id)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Editar Archivo'
        return context

class EliminarArchivosView(GroupRequiredMixin,DeleteView):
    def get(self, request):
        user_id = request.GET.get('id')
        user = get_object_or_404(ArchRegister, id=user_id)
        user.delete()
        return redirect('archivos:listar') 