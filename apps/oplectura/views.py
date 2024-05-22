from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy
from django.http import JsonResponse
from django.views.generic import CreateView, ListView, TemplateView, UpdateView, DeleteView
from .models import DocenteGradoSeccion
from .forms import CargarDocenteGradoSeccion

class DocenteCreateView(CreateView):
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
    
