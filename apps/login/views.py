from django.contrib.auth.views import LoginView, LogoutView
from django.urls import reverse_lazy
from django.contrib.auth.models import Group

class LoginFormView(LoginView):
    template_name='login/login.html'
    
    def get_context_data(self, **kwargs):
        context=super().get_context_data(**kwargs)
        context['title']='Iniciar Sesión'
        return context

    def get_success_url(self):
        user = self.request.user
        
        # Verificar si el usuario pertenece al grupo 'Evaluacion'
        evaluacion_group = Group.objects.get(name='Evaluacion')
        if evaluacion_group in user.groups.all():
            return reverse_lazy('oplectura:portada_eval')        
        
        # Verificar si el usuario pertenece al grupo 'Director'
        director_group = Group.objects.get(name='Director')
        if director_group in user.groups.all():
            return reverse_lazy('directores:institucional')
       
        # Verificar si el usuario pertenece al grupo 'Aplicador'
        aplicador_group = Group.objects.get(name='Aplicador')
        if aplicador_group in user.groups.all():
            return reverse_lazy('oplectura:evaluacion') + '?cueanexo=0&grado=TERCERO&seccion=A'
         
        # Si el usuario no pertenece a ninguno de los grupos anteriores            
        return super().get_success_url()