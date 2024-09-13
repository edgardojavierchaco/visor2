from django.urls import reverse
from django.contrib.auth.views import LoginView, LogoutView
from django.contrib.auth.models import Group
from django.template.loader import render_to_string
from django.http import JsonResponse
from django.contrib.auth import authenticate, login

class LoginFormView(LoginView):
    template_name = 'login/login.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Iniciar Sesión'
        return context

    def get_success_url(self):
        user = self.request.user
        
        if user.is_authenticated and user.is_staff:
            evaluacion_group = Group.objects.get(name='Evaluacion')
            if evaluacion_group in user.groups.all():
                return reverse('oplectura:portada_eval')        
            
            director_group = Group.objects.get(name='Director')
            if director_group in user.groups.all():
                return reverse('directores:institucional')
            
            aplicador_group = Group.objects.get(name='Aplicador')
            if aplicador_group in user.groups.all():
                return reverse('oplectura:evaluacion') + '?cueanexo=0&grado=TERCERO&seccion=A'
         
            return super().get_success_url()

        return reverse('login')  # Redirigir a la página de login si el usuario no es staff

    def form_valid(self, form):
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
        html = 'login/login.html'
        return JsonResponse({'success': False, 'message': 'Credenciales incorrectas.', 'template': html})

    def post(self, request, *args, **kwargs):
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            # Manejar la solicitud AJAX
            form = self.get_form()
            if form.is_valid():
                return self.form_valid(form)
            else:
                return self.form_invalid(form)
        else:
            return super().post(request, *args, **kwargs)