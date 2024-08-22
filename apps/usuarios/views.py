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
import hashlib
import json

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

#listado de directores para Evaluación
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
        context['title']='Listado de Directores'
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
        hashed_password = hashlib.sha256(password.encode()).hexdigest() # type: ignore
        
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

#Eliminar usuarios para Administrador
class EliminarUsuarioView(AdminRequiredMixin,DeleteView):
    def get(self, request):
        user_id = request.GET.get('id')
        user = get_object_or_404(UsuariosVisualizador, id=user_id)
        user.delete()
        return redirect('usuarios:listado') 

#Eliminar usuarios para Evaluación
class EliminarUsuarioView_op(DeleteView):
    def get(self, request):
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
        # Obtener el formulario de usuario
        usuario_form = form.save(commit=False)
        
        # Encriptar la contraseña usando SHA256
        password = form.cleaned_data.get('password')
        hashed_password = hashlib.sha256(password.encode()).hexdigest() # type: ignore
        
        # Guardar la contraseña encriptada en el objeto de usuario
        usuario_form.password = hashed_password
        
        # Asignar los campos activo e is_staff a True
        usuario_form.activo = True
        usuario_form.is_staff = True
        
        # Guardar el usuario en la base de datos
        usuario_form.save()
        
        # Asignar al usuario al grupo correspondiente según el nivel de acceso
        nivel_acceso = form.cleaned_data.get('nivelacceso')
        print(f"Nivel de acceso seleccionado: {nivel_acceso.tacceso}") 
        if nivel_acceso.tacceso == 'Director/a':
            grupo = Group.objects.get(name='Director')
        elif nivel_acceso.tacceso == 'Aplicador':
            grupo = Group.objects.get(name='Aplicador')
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


class ResetPassWordView(FormView):
    form_class = ResetpassWordForm
    template_name = 'login/resetpwd.html'
    success_url = reverse_lazy('usuarios:login')  

    def form_valid(self, form):
        username = form.cleaned_data.get('username')
        try:
            user = UsuariosVisualizador.objects.get(username=username)
            token = default_token_generator.make_token(user)
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            reset_url = self.request.build_absolute_uri(reverse_lazy('usuarios:password_reset_confirm', args=[uid, token]))
            send_mail(
                'Resetear su contraseña',
                f'use el siguiente enlace para resetear su contraseña:\n{reset_url}',
                'estadisticaseducativaschaco@gmail.com',
                [user.correo],
                fail_silently=False,
            )
            messages.success(self.request, 'Se ha enviado un correo electrónico para restablecer tu contraseña.')
        except UsuariosVisualizador.DoesNotExist:
            messages.error(self.request, 'El nombre de usuario no existe.')

        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Reseteo de Contraseña'
        return context

class PasswordResetConfirmView(TemplateView):
    template_name = 'login/password_reset_confirm.html'

    def post(self, request, *args, **kwargs):
        uidb64 = kwargs.get('uidb64')
        token = kwargs.get('token')
        try:
            uid = force_str(urlsafe_base64_decode(uidb64))
            user = UsuariosVisualizador.objects.get(pk=uid)
            if default_token_generator.check_token(user, token):
                new_password1 = request.POST.get('new_password1')
                new_password2 = request.POST.get('new_password2')
                if new_password1 and new_password1 == new_password2:
                    user.set_password(new_password1)
                    user.save()
                    messages.success(request, 'Tu contraseña ha sido restablecida con éxito.')
                    return HttpResponseRedirect(reverse_lazy('usuarios:login'))
                else:
                    messages.error(request, 'Las contraseñas no coinciden.')
            else:
                messages.error(request, 'El enlace de restablecimiento de contraseña no es válido.')
        except (TypeError, ValueError, OverflowError, UsuariosVisualizador.DoesNotExist):
            messages.error(request, 'El enlace de restablecimiento de contraseña no es válido.')
        
        return self.render_to_response(self.get_context_data())