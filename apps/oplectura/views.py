from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy
from django.http import JsonResponse
from django.views.generic import CreateView, ListView, TemplateView, UpdateView, DeleteView
from .models import DocenteGradoSeccion
from .forms import CargarDocenteGradoSeccion

class DocenteCreateView(LoginRequiredMixin,CreateView):
    model=DocenteGradoSeccion
    form_class=CargarDocenteGradoSeccion
    template_name='oplectura/cargar_docente.html'
    success_url = reverse_lazy('oplectura:listado')
    
    def get_context_data(self, **kwargs):
        context=super().get_context_data(**kwargs)
        context['title']='Cargar Docente'
        return context

class DocentesListView(LoginRequiredMixin,ListView):
    model=DocenteGradoSeccion      
    template_name='oplectura/listado.html' 
    context_object_name='docentes'   
    print(context_object_name)
    
    def get_queryset(self):
        # Obtener el usuario logueado
        user = self.request.user
        # Filtrar los docentes por el usuario logueado
        queryset = super().get_queryset().filter(cueanexo=user.username)
        return queryset
    
    def get_context_data(self, **kwargs):
        context=super().get_context_data(**kwargs)
        context['title']='Listado de Docentes'
        return context
    
class DocentesUpdateView(LoginRequiredMixin,UpdateView):
    model = DocenteGradoSeccion
    form_class = CargarDocenteGradoSeccion
    template_name = 'oplectura/editar.html'
    success_url = reverse_lazy('oplectura:listado')

    def get_object(self):
        user_id = self.request.GET.get('id')
        return get_object_or_404(DocenteGradoSeccion, id=user_id)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Editar Archivo'
        return context

class DocentesDeleteView(LoginRequiredMixin,DeleteView):
    def get(self, request):
        user_id = request.GET.get('id')
        user = get_object_or_404(DocenteGradoSeccion, id=user_id)
        user.delete()
        return redirect('oplectura:listado') 