import hashlib
from django.http.response import HttpResponse as HttpResponse
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.shortcuts import render

from apps.usuarios.forms import UsuariosForm
from apps.usuarios.models import UsuariosVisualizador
from django.contrib.auth.mixins import LoginRequiredMixin
from apps.login.mixins import IsSuperuserMixin

# Create your views here.

def usuarios_list(request):
    data={
       'title':'Listado de Usuarios',
       'usuarios': UsuariosVisualizador.objects.all()
    }
    return render(request,'usuarios/listadousers.html',data)

class UsuariosListView(LoginRequiredMixin, IsSuperuserMixin,ListView):
    model= UsuariosVisualizador
    template_name='usuarios/listadousers.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Listado de Usuarios'
        return context

class UsuariosCreateView(LoginRequiredMixin,IsSuperuserMixin,CreateView):
    model=UsuariosVisualizador
    form_class=UsuariosForm
    template_name='usuarios/create.html'
    success_url=reverse_lazy('usuarios:Listado_usuarios')
    
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Creación de Usuarios'
        return context
    
    def form_valid(self, form):
        # Encriptar la contraseña antes de guardar
        form.instance.password = hashlib.sha256(form.cleaned_data['password'].encode()).hexdigest()
        return super().form_valid(form)
    
    
class UsuariosUpdateView(LoginRequiredMixin,IsSuperuserMixin,UpdateView):
    model = UsuariosVisualizador
    form_class = UsuariosForm
    template_name = 'usuarios/editar.html'
    success_url = reverse_lazy('usuarios:Listado_usuarios')   
              
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Edición de Usuario' 
        return context


class UsuariosDeleteView(LoginRequiredMixin,IsSuperuserMixin,DeleteView):
    model = UsuariosVisualizador
    template_name = 'usuarios/eliminar.html'
    success_url = reverse_lazy('usuarios:Listado_usuarios')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Eliminación de Usuario'                        
        context['list_url'] = reverse_lazy('usuarios:Listado_usuarios')
        return context