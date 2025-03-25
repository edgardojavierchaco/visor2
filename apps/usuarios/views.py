import hashlib
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView
from apps.usuarios.forms import UsuariosForm
from apps.usuarios.models import UsuariosVisualizador
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt

class listado_usuarios(ListView):
    model=UsuariosVisualizador        
    template_name='usuarios/listado.html' 
    context_object_name='usuarios'   
    print(context_object_name)  
    
    @method_decorator(csrf_exempt)
    def dispatch(self,request,*args,**kwargs):
        return super().dispatch(request,*args,**kwargs)
         
    def get_context_data(self, **kwargs):
        context=super().get_context_data(**kwargs)
        context['title']='Listado de Usuarios'
        context['create_url']=reverse_lazy('usua:crear')
        context['entity']='Usuarios'
        context['list_url']=reverse_lazy('usua:listado')
        return context

class UsuariosCreateView(CreateView):
    model=UsuariosVisualizador
    form_class= UsuariosForm
    template_name='usuarios/crearusuario.html'
    success_url=reverse_lazy('usua:listado')
    
    def form_valid(self, form):
        # Obtenemos la contraseña ingresada por el usuario
        password = form.cleaned_data['password']
        
        # Calculamos el hash SHA-256 de la contraseña
        hashed_password = hashlib.sha256(password.encode()).hexdigest()
        
        # Reemplazamos la contraseña original por su hash en el formulario
        form.instance.password = hashed_password
        
        # Llamamos al método form_valid del padre para continuar el proceso de guardado
        return super().form_valid(form)
    
    
        
    def get_context_data(self, **kwargs):
        context=super().get_context_data(**kwargs)
        context['title']='Agregar un nuevo Usuario'
        context['entity']='Usuarios'
        context['list_url']=reverse_lazy('usua:listado')
        context['action']='add'
        return context
    

class UsuariosEditarView(UpdateView):
    model=UsuariosVisualizador
    fields=['id','apellido','nombres','correo','telefono','nivelacceso']
    template_name= 'usuarios/editarusuario.html'
    success_url=reverse_lazy('usua:listado')
    
     
    def get_context_data(self, **kwargs):
        context=super().get_context_data(**kwargs)
        context['title']='Editar un usuario'
        context['list_url']=reverse_lazy('usua:listado')
        return context