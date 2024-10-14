from django.conf import settings
from urllib import request
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse_lazy
from django.http import HttpResponseRedirect, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.contrib.auth import login
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, FormView, TemplateView
from apps.usuarios.forms import UsuariosForm, UsuariosForm_login, ResetpassWordForm
from apps.usuarios.models import UsuariosVisualizador, NivelAcceso
from config import settings
from .mixins import AdminRequiredMixin
from django.contrib.auth.models import Group
from django.core.mail import send_mail
from django.contrib import messages
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.contrib import messages
import hashlib
import json

#listado de usuarios para el Admin
class listado_usuarios(AdminRequiredMixin,ListView):
    """
    Vista que muestra el listado de usuarios para el administrador.

    Atributos:
        model: El modelo a utilizar (UsuariosVisualizador).
        template_name: La plantilla a renderizar.
        context_object_name: Nombre del contexto a pasar a la plantilla.

    Métodos:
        get_context_data: Agrega información adicional al contexto.
    """
    
    model=UsuariosVisualizador        
    template_name='usuarios/listado.html' 
    context_object_name='usuarios'   
    print(context_object_name)
    
    def get_context_data(self, **kwargs):
        """
        Agrega el título al contexto.

        Args:
            **kwargs: Argumentos adicionales.

        Returns:
            dict: El contexto actualizado.
        """
        
        context=super().get_context_data(**kwargs)
        context['title']='Listado de Usuarios'
        return context

#listado de directores para Evaluación
class listado_usuarios_op(ListView):
    """
    Vista que muestra el listado de usuarios con nivel de acceso "Director/a".

    Atributos:
        model: El modelo a utilizar (UsuariosVisualizador).
        template_name: La plantilla a renderizar.
        context_object_name: Nombre del contexto a pasar a la plantilla.

    Métodos:
        get_queryset: Filtra los usuarios por nivel de acceso.
        get_context_data: Agrega información adicional al contexto.
    """

    model=UsuariosVisualizador        
    template_name='usuarios/listado_op.html' 
    context_object_name='usuarios'   
    print(context_object_name)
    
    def get_queryset(self):
        """
        Filtra los usuarios cuyo nivel de acceso es "Director/a".

        Returns:
            QuerySet: Los usuarios filtrados.
        """
        
        # Filtrar los usuarios cuyo nivel de acceso es "Director/a"
        return UsuariosVisualizador.objects.filter(nivelacceso='Director/a')
    
    def get_context_data(self, **kwargs):
        """
        Agrega el título al contexto.

        Args:
            **kwargs: Argumentos adicionales.

        Returns:
            dict: El contexto actualizado.
        """
        
        context=super().get_context_data(**kwargs)
        context['title']='Listado de Directores'
        return context


class crear_usuarios(AdminRequiredMixin,CreateView):
    """
    Vista para crear un nuevo usuario.

    Atributos:
        model: El modelo a utilizar (UsuariosVisualizador).
        form_class: El formulario para crear usuarios.
        template_name: La plantilla a renderizar.
        success_url: URL a la que redirigir después de una creación exitosa.

    Métodos:
        get_context_data: Agrega información adicional al contexto.
        form_valid: Guarda el usuario en la base de datos.
    """
    
    model=UsuariosVisualizador
    form_class=UsuariosForm
    template_name='usuarios/crear.html'
    success_url=reverse_lazy('usuarios:listado')

    def get_context_data(self,**kwargs):
        """
        Agrega el título al contexto.

        Args:
            **kwargs: Argumentos adicionales.

        Returns:
            dict: El contexto actualizado.
        """
        
        context=super().get_context_data(**kwargs)
        context['title']='Crear Usuario'
        return context
    
    def form_valid(self, form):
        """
        Procesa el formulario válido y guarda el usuario.

        Args:
            form: El formulario enviado.

        Returns:
            HttpResponse: Respuesta de redirección después de guardar el usuario.
        """
        
        # Obtener el formulario de usuario
        usuario_form = form.save(commit=False)
        
        # Encriptar la contraseña usando SHA256
        password = form.cleaned_data.get('password')
        hashed_password = hashlib.sha256(password.encode()).hexdigest() # type: ignore
        
        # Guardar la contraseña encriptada en el objeto de usuario
        usuario_form.password = hashed_password
        
        # Guardar el usuario en la base de datos
        usuario_form.save()

        return super().form_valid(form)

#edición para Administrador
class editar_usuarios(AdminRequiredMixin, UpdateView):
    """
    Vista para editar un usuario existente.

    Atributos:
        model: El modelo a utilizar (UsuariosVisualizador).
        form_class: El formulario para editar usuarios.
        template_name: La plantilla a renderizar.
        success_url: URL a la que redirigir después de una edición exitosa.

    Métodos:
        get_object: Obtiene el objeto de usuario a editar.
        get_context_data: Agrega información adicional al contexto.
        form_valid: Procesa el formulario válido.
    """
    
    model = UsuariosVisualizador
    form_class = UsuariosForm
    template_name = 'usuarios/editar.html'
    success_url = reverse_lazy('usuarios:listado')

    def get_object(self):
        """
        Obtiene el objeto de usuario a editar basado en el ID proporcionado.

        Returns:
            UsuariosVisualizador: El usuario a editar.
        """
        
        user_id = self.request.GET.get('id')
        return get_object_or_404(UsuariosVisualizador, id=user_id)

    def get_context_data(self, **kwargs):
        """
        Agrega el título al contexto.

        Args:
            **kwargs: Argumentos adicionales.

        Returns:
            dict: El contexto actualizado.
        """
        
        context = super().get_context_data(**kwargs)
        context['title'] = 'Editar Usuario'
        return context

    def form_valid(self, form):
        """
        Procesa el formulario válido y actualiza el usuario.

        Args:
            form: El formulario enviado.

        Returns:
            HttpResponse: Respuesta de redirección después de actualizar el usuario.
        """
        
        # Simplemente llamamos al form_valid de la superclase
        return super().form_valid(form)


#edición para Evaluación
class editar_usuarios_op(UpdateView):
    """
    Vista para editar un usuario existente para evaluación.

    Atributos:
        model: El modelo a utilizar (UsuariosVisualizador).
        form_class: El formulario para editar usuarios.
        template_name: La plantilla a renderizar.
        success_url: URL a la que redirigir después de una edición exitosa.

    Métodos:
        get_object: Obtiene el objeto de usuario a editar.
        get_context_data: Agrega información adicional al contexto.
        form_valid: Procesa el formulario válido.
    """
    
    model = UsuariosVisualizador
    form_class = UsuariosForm
    template_name = 'usuarios/editar_op.html'
    success_url = reverse_lazy('usuarios:listado_op')

    def get_object(self):
        """
        Obtiene el objeto de usuario a editar basado en el ID proporcionado.

        Returns:
            UsuariosVisualizador: El usuario a editar.
        """
        
        user_id = self.request.GET.get('id')
        return get_object_or_404(UsuariosVisualizador, id=user_id)

    def get_context_data(self, **kwargs):
        """
        Agrega el título al contexto.

        Args:
            **kwargs: Argumentos adicionales.

        Returns:
            dict: El contexto actualizado.
        """
        
        context = super().get_context_data(**kwargs)
        context['title'] = 'Editar Usuario'
        return context

    def form_valid(self, form):
        """
        Procesa el formulario válido y actualiza el usuario.

        Args:
            form: El formulario enviado.

        Returns:
            HttpResponse: Respuesta de redirección después de actualizar el usuario.
        """
        
        # Simplemente llamamos al form_valid de la superclase
        return super().form_valid(form)

#Eliminar usuarios para Administrador
class EliminarUsuarioView(AdminRequiredMixin,DeleteView):
    """
    Vista para eliminar un usuario.

    Métodos:
        get: Elimina el usuario basado en el ID proporcionado.
    """
    
    def get(self, request):
        """
        Elimina el usuario y redirige a la lista de usuarios.

        Args:
            request: La solicitud HTTP.

        Returns:
            HttpResponseRedirect: Redirección a la lista de usuarios.
        """
        
        user_id = request.GET.get('id')
        user = get_object_or_404(UsuariosVisualizador, id=user_id)
        user.delete()
        return redirect('usuarios:listado') 

#Eliminar usuarios para Evaluación
class EliminarUsuarioView_op(DeleteView):
    """
    Vista para eliminar un usuario en evaluación.

    Métodos:
        get: Elimina el usuario basado en el ID proporcionado.
    """
    
    def get(self, request):
        """
        Elimina el usuario y redirige a la lista de directores.

        Args:
            request: La solicitud HTTP.

        Returns:
            HttpResponseRedirect: Redirección a la lista de directores.
        """
        
        user_id = request.GET.get('id')
        user = get_object_or_404(UsuariosVisualizador, id=user_id)
        user.delete()
        return redirect('usuarios:listado_op')

class registrar_usuarios(CreateView):
    model = UsuariosVisualizador
    form_class = UsuariosForm_login
    template_name = 'login/login.html'
    success_url = reverse_lazy('usuarios:registro')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Crear Usuario'
        return context
    
    def form_valid(self, form):
        # Verificar si el username ya está registrado
        username = form.cleaned_data.get('username')
        if UsuariosVisualizador.objects.filter(username=username).exists():
            messages.error(self.request, 'El usuario ya está registrado.')
            return redirect('usuarios:registro')
        
        # Obtener el formulario de usuario
        usuario_form = form.save(commit=False)
        
        # Encriptar la contraseña usando SHA256
        password = form.cleaned_data.get('password')
        hashed_password = hashlib.sha256(password.encode()).hexdigest() # type: ignore
        
        # Guardar la contraseña encriptada en el objeto de usuario
        usuario_form.password = hashed_password
        
        # Asignar los campos activo a True e is_staff a False
        usuario_form.activo = False
        usuario_form.is_staff = False
        
        # Guardar el usuario en la base de datos
        usuario_form.save()
        
        # Asignar al usuario al grupo correspondiente según el nivel de acceso
        nivel_acceso = form.cleaned_data.get('nivelacceso')
        print(f"Nivel de acceso seleccionado: {nivel_acceso.tacceso}") 
        if nivel_acceso.tacceso == 'Director/a':
            grupo = Group.objects.get(name='Director')
        elif nivel_acceso.tacceso == 'Aplicador':
            grupo = Group.objects.get(name='Aplicador')
        elif nivel_acceso.tacceso == 'Docente':
            grupo = Group.objects.get(name='Docente')
        else:
            grupo = None

        if grupo:
            usuario_form.groups.add(grupo)
            print(f"Usuario {usuario_form.username} asignado al grupo {grupo.name}")
        else:
            print("No se encontró el grupo correspondiente")
        return super().form_valid(form)
    

@csrf_exempt
def check_user_status(request):
    if request.method == "POST":
        data = json.loads(request.body)
        username = data.get('username')
        try:
            user = UsuariosVisualizador.objects.get(username=username)
            return JsonResponse({'is_staff': user.is_staff})
        except UsuariosVisualizador.DoesNotExist:
            return JsonResponse({'is_staff': False})
    return JsonResponse({'is_staff': False})


