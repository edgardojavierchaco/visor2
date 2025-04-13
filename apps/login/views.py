from django.urls import reverse, reverse_lazy
from django.contrib.auth.views import LoginView, LogoutView
from django.contrib.auth.models import Group
from django.template.loader import render_to_string
from django.http import JsonResponse
from django.contrib.auth import authenticate, login
from django.conf import settings


class LoginFormView(LoginView):
    """
    Vista personalizada para gestionar el inicio de sesión.

    Atributos:
        template_name (str): El nombre del template utilizado para el formulario de inicio de sesión.

    Métodos:
        get_context_data: Agrega el título 'Iniciar Sesión' al contexto.
        get_success_url: Redirige al usuario autenticado según sus permisos y grupos, o a una URL predeterminada si no está en ningún grupo.
        form_valid: Valida el formulario de inicio de sesión y autentica al usuario. Retorna una respuesta JSON dependiendo del resultado.
        form_invalid: Retorna una respuesta JSON con un mensaje de error si las credenciales son incorrectas.
        post: Maneja la solicitud POST, incluyendo solicitudes AJAX, para validar el formulario y retornarlas respuestas correspondientes.

    """
    template_name = 'login/login.html'
    
    def get_context_data(self, **kwargs):
        """
        Agrega el título 'Iniciar Sesión' al contexto del template.

        Args:
            kwargs: Diccionario de argumentos adicionales.

        Returns:
            dict: Contexto actualizado con el título de la página.
        """
        context = super().get_context_data(**kwargs)
        context['title'] = 'Iniciar Sesión'
        return context

    def get_success_url(self):
        """
        Redirige al usuario autenticado basado en su grupo.

        Returns:
            str: URL a la que será redirigido el usuario según su grupo.
        """
        user = self.request.user
        
        if user.is_authenticated and user.is_staff:
            evaluacion_group = Group.objects.get(name='Evaluacion')
            if evaluacion_group in user.groups.all():
                return reverse('oplectura:portada_eval')        
            
            gestor_group = Group.objects.get(name='Gestor')
            if gestor_group in user.groups.all():
                return reverse('archivos:portada_gestor')
            
            director_group = Group.objects.get(name='Director')
            if director_group in user.groups.all():
                return reverse('directores:institucional')
            
            aplicador_group = Group.objects.get(name='Aplicador')
            if aplicador_group in user.groups.all():
                return reverse('oplectura:evaluacion') + '?cueanexo=0&grado=TERCERO&seccion=A'
         
            regionales_group = Group.objects.get(name='Regional')
            if regionales_group in user.groups.all():
                return reverse('oplectura:portada_regional')
            
            privada_group=Group.objects.get(name='Director_Privada')
            if privada_group in user.groups.all():
                return reverse('directores:institucional_uegp')
            
            privada_group=Group.objects.get(name='DirGral_Privada')
            if privada_group in user.groups.all():
                return reverse('privada:dashboard')
            
            funcionarios_group=Group.objects.get(name='Funcionarios')
            if funcionarios_group in user.groups.all():
                return reverse('funcionario:portada_func')
            
            funcionarios_group=Group.objects.get(name='Supervisor')
            if funcionarios_group in user.groups.all():
                return reverse('operativo:portada_supervisor')
                
            if not user.groups.exists():
                return settings.LOGIN_REDIRECT_URL            
            
            return super().get_success_url()

        return reverse('login')  

    def form_valid(self, form):
        """
        Maneja el caso en que el formulario es válido, autenticando al usuario y redirigiéndolo según sus permisos.

        Args:
            form: Formulario de inicio de sesión.

        Returns:
            JsonResponse: Respuesta JSON con el estado de la autenticación.
        """
        user = authenticate(username=form.cleaned_data['username'], password=form.cleaned_data['password'])
        if user is not None:
            login(self.request, user)
            if user.is_staff:
                redirect_url = self.get_success_url()
                return JsonResponse({'success': True, 'redirect_url': redirect_url})
            else:
                return JsonResponse({'success': False, 'message': 'Aún no estás autorizado.'})
        return JsonResponse({'success': False, 'message': 'Credenciales incorrectas.'})

    def form_invalid(self, form):
        """
        Maneja el caso en que el formulario no es válido, retornando un mensaje de error.

        Args:
            form: Formulario de inicio de sesión inválido.

        Returns:
            JsonResponse: Respuesta JSON con el mensaje de error y el template asociado.
        """
        html = 'login/login.html'
        return JsonResponse({'success': False, 'message': 'Credenciales incorrectas.', 'template': html})

    def post(self, request, *args, **kwargs):
        """
        Procesa la solicitud POST, manejando solicitudes AJAX y no AJAX.

        Args:
            request: Objeto de solicitud HTTP.
            *args: Argumentos adicionales.
            **kwargs: Argumentos adicionales.

        Returns:
            JsonResponse o HttpResponse: Respuesta dependiendo de si la solicitud es AJAX o no.
        """
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            # Manejar la solicitud AJAX
            form = self.get_form()
            if form.is_valid():
                return self.form_valid(form)
            else:
                return self.form_invalid(form)
        else:
            return super().post(request, *args, **kwargs)


class CustomLogoutView(LogoutView):
    """
    Vista personalizada para gestionar el cierre de sesión.

    Atributos:
        next_page (str): URL a la que se redirige al usuario tras cerrar sesión.
    """
    next_page = reverse_lazy('dash:portada')