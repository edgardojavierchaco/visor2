from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse_lazy
from django.http import HttpResponseRedirect
from django.contrib.auth import login
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from apps.usuarios.forms import UsuariosForm, UsuariosForm_login
from apps.usuarios.models import UsuariosVisualizador, NivelAcceso
from .mixins import AdminRequiredMixin
from django.contrib.auth.models import Group
import hashlib

#listado de usuarios para el Admin
class listado_usuarios(AdminRequiredMixin,ListView):
    model=UsuariosVisualizador        
    template_name='usuarios/listado.html' 
    context_object_name='usuarios'   
    print(context_object_name)
    
    def get_context_data(self, **kwargs):
        context=super().get_context_data(**kwargs)
        context['title']='Listado de Usuarios'
        return context

#listado de usuarios para Evaluación
class listado_usuarios_op(ListView):
    model=UsuariosVisualizador        
    template_name='usuarios/listado_op.html' 
    context_object_name='usuarios'   
    print(context_object_name)
    
    def get_queryset(self):
        # Filtrar los usuarios cuyo nivel de acceso es "Director/a"
        return UsuariosVisualizador.objects.filter(nivelacceso='Director/a')
    
    def get_context_data(self, **kwargs):
        context=super().get_context_data(**kwargs)
        context['title']='Listado de Usuarios'
        return context


class crear_usuarios(AdminRequiredMixin,CreateView):
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

#edición para Administrador
class editar_usuarios(AdminRequiredMixin, UpdateView):
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

    def form_valid(self, form):
        # Simplemente llamamos al form_valid de la superclase
        return super().form_valid(form)


#edición para Evaluación
class editar_usuarios_op(UpdateView):
    model = UsuariosVisualizador
    form_class = UsuariosForm
    template_name = 'usuarios/editar_op.html'
    success_url = reverse_lazy('usuarios:listado_op')

    def get_object(self):
        user_id = self.request.GET.get('id')
        return get_object_or_404(UsuariosVisualizador, id=user_id)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Editar Usuario'
        return context

    def form_valid(self, form):
        # Simplemente llamamos al form_valid de la superclase
        return super().form_valid(form)

class EliminarUsuarioView(AdminRequiredMixin,DeleteView):
    def get(self, request):
        user_id = request.GET.get('id')
        user = get_object_or_404(UsuariosVisualizador, id=user_id)
        user.delete()
        return redirect('usuarios:listado') 

class registrar_usuarios(CreateView):
    model=UsuariosVisualizador
    form_class=UsuariosForm_login
    template_name='login/login.html'
    success_url=reverse_lazy('usuarios:registrar')

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
        
        # Asignar al usuario al grupo "Director"
        grupo_director = Group.objects.get(name='Director')
        usuario_form.groups.add(grupo_director)

        return super().form_valid(form)