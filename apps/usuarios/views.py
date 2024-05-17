from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse_lazy
from django.http import HttpResponseRedirect
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from apps.usuarios.forms import UsuariosForm
from apps.usuarios.models import UsuariosVisualizador
import hashlib

class listado_usuarios(ListView):
    model=UsuariosVisualizador        
    template_name='usuarios/listado.html' 
    context_object_name='usuarios'   
    print(context_object_name)
    
    def get_context_data(self, **kwargs):
        context=super().get_context_data(**kwargs)
        context['title']='Listado de Usuarios'
        return context

class crear_usuarios(CreateView):
    model=UsuariosVisualizador
    form_class=UsuariosForm
    template_name='usuarios/crear.html'
    success_url=reverse_lazy('usuarios:listado')

    def get_context_data(self,**kwargs):
        context=super().get_context_data(**kwargs)
        context['title']='Crear Usuario'
        return context
    
    def form_valid(self, form):
        # Obtener el formulario de usuario
        usuario_form = form.save(commit=False)
        
        # Encriptar la contraseña usando SHA256
        password = form.cleaned_data.get('password')
        hashed_password = hashlib.sha256(password.encode()).hexdigest()
        
        # Guardar la contraseña encriptada en el objeto de usuario
        usuario_form.password = hashed_password
        
        # Guardar el usuario en la base de datos
        usuario_form.save()

        return super().form_valid(form)


class editar_usuarios(UpdateView):
    model = UsuariosVisualizador
    form_class = UsuariosForm
    template_name = 'usuarios/editar.html'
    success_url = reverse_lazy('usuarios:listado')

    def get_object(self):
        user_id = self.request.GET.get('id')
        return get_object_or_404(UsuariosVisualizador, id=user_id)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Editar Usuario'
        return context

class EliminarUsuarioView(DeleteView):
    def get(self, request):
        user_id = request.GET.get('id')
        user = get_object_or_404(UsuariosVisualizador, id=user_id)
        user.delete()
        return redirect('usuarios:listado') 